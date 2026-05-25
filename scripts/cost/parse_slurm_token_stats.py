"""Parse per-note token usage and wall-clock from slurm-*.out logs.

The logs emitted by an older revision of ``main.py`` (visible in
``slurm-194652.out``, ``slurm-200028.out``, ``slurm-200036.out`` and
``slurm-200045.out``) contain explicit ``Token Usage Statistics for the note``
blocks for each completed note plus a ``Time taken for ...`` line.  This
parser is intentionally strict: any malformed block raises immediately (no
silent fallback per the project's fail-fast convention).

IMPORTANT: in those older single-threaded ``main.py`` runs the LLMManager was
SHARED across all notes in the loop and ``llm_model.note_token_stats[-1]``
was logged after each note.  Because ``finish_note()`` summed the **shared**
``self.chunk_token_stats`` rather than a per-note slice, the printed
"Number of chunks", "Total prompt tokens", "Total completion tokens",
"Total original chunk tokens" and "Total tokens" are *cumulative across all
notes processed so far in that job*, not per-note.  This script therefore
de-cumulates by computing diffs between consecutive notes within each
source_file.  The "avg_*" and "Average LLM calls per chunk" fields in the log
are likewise cumulative averages, so we recompute them from the per-note
diffs.

Output:
    A pandas DataFrame (also saved as CSV) with one row per note containing
    note_key, total_prompt_tokens, total_completion_tokens, total_tokens,
    num_chunks, avg_tokens_per_chunk, total_original_chunk_tokens,
    avg_calls_per_chunk, duration_sec, source_file, model_inferred,
    dataset_inferred.

Usage:
    python scripts/cost/parse_slurm_token_stats.py \
        slurm-194652.out slurm-200045.out ... \
        --output runs/EXP-D/slurm_token_stats.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


# ----------------------------------------------------------------------------
# Regex patterns — anchored on the exact log lines emitted by main.py.
# ----------------------------------------------------------------------------
#
# NOTE on line anchors: tqdm progress bars sometimes glue themselves to the
# start of a logging line (e.g. ``Processing notes:  25%|... 2025-05-26 ...
# Processing note 2/4: Test_note7 ...``).  We therefore use a non-anchored
# ``re.search`` semantics for the patterns that detect log events.
#
RE_PROCESSING_NOTE = re.compile(
    r"(?P<ts>[0-9-]{10} [0-9:,]+) - __main__ - INFO - "
    r"========= Processing note \d+/\d+: (?P<note_key>\S+) =========="
)
RE_TOKEN_BLOCK_HEADER = re.compile(
    # The header is emitted by ``logger.info('\nToken Usage Statistics for the note:')``
    # so the literal text lands on its own line, *without* the timestamp /
    # logger-name prefix.  We therefore match the text directly.
    r"Token Usage Statistics for the note:"
)
RE_TIME_TAKEN = re.compile(
    r"(?P<ts>[0-9-]{10} [0-9:,]+) - __main__ - INFO - "
    r"Time taken for (?P<note_key>\S+): (?P<sec>[0-9.]+) seconds"
)
RE_TOKEN_KV = re.compile(r"^\s*(?P<key>[A-Za-z][A-Za-z _()/]+):\s+(?P<val>[0-9.,]+)\s*$")
RE_MODEL_DEPLOY = re.compile(r"/deployments/(?P<model>[A-Za-z0-9\-]+)/chat/completions")
RE_INFO_LINE_KV = re.compile(
    r"[0-9-]{10} [0-9:,]+ - __main__ - INFO -\s+(?P<key>[A-Za-z][A-Za-z _()/]+):\s+(?P<val>[0-9.,]+)\s*$"
)


# Mapping from log field names to canonical schema keys.
TOKEN_FIELDS = {
    "Total prompt tokens": "total_prompt_tokens",
    "Total completion tokens": "total_completion_tokens",
    "Total tokens": "total_tokens",
    "Number of chunks": "num_chunks",
    "Average tokens per chunk": "avg_tokens_per_chunk",
    "Total original chunk tokens": "total_original_chunk_tokens",
    "Average original chunk tokens": "avg_original_chunk_tokens",
    "Average prompt tokens per chunk": "avg_prompt_tokens_per_chunk",
    "Average completion tokens per chunk": "avg_completion_tokens_per_chunk",
    "Average LLM calls per chunk": "avg_calls_per_chunk",
}


@dataclass
class NoteCost:
    source_file: str
    note_key: str
    model_inferred: str
    dataset_inferred: str
    duration_sec: float | None
    total_prompt_tokens: int | None = None
    total_completion_tokens: int | None = None
    total_tokens: int | None = None
    num_chunks: int | None = None
    avg_tokens_per_chunk: float | None = None
    total_original_chunk_tokens: int | None = None
    avg_original_chunk_tokens: float | None = None
    avg_prompt_tokens_per_chunk: float | None = None
    avg_completion_tokens_per_chunk: float | None = None
    avg_calls_per_chunk: float | None = None


def infer_dataset_from_note_key(note_key: str) -> str:
    """Map note_key to dataset label.

    4CE notes look like ``4CE_BCH_1`` / ``4CE_KUMC_3``.  CORAL look like
    ``coral_annotated_breastca_38`` / ``coral_annotated_pdac_14``.  Anything
    else is reported verbatim so we can audit.
    """
    if note_key.startswith("4CE_"):
        return "4CE"
    if note_key.startswith("coral_annotated_breastca"):
        return "CORAL-Breast"
    if note_key.startswith("coral_annotated_pdac"):
        return "CORAL-Pancreas"
    if note_key.lower().startswith("mimic"):
        return "MIMIC"
    return f"OTHER:{note_key.split('_')[0]}"


def infer_model_from_log(log_lines: list[str]) -> str:
    """Walk the *first* 5000 lines of the log to identify the deployment.

    For Azure OpenAI calls there is a ``/deployments/<model>/chat/completions``
    URL in the debug request body.  We prefer the explicit deployment ID over
    any inferred CLI args.
    """
    for line in log_lines[:5000]:
        m = RE_MODEL_DEPLOY.search(line)
        if m:
            return m.group("model")
    return "UNKNOWN"


def parse_one_log(path: Path) -> list[NoteCost]:
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    model_inferred = infer_model_from_log(text)

    # Build an index of (line_no -> processing-note event)
    # and (line_no -> time-taken event) to associate token blocks with note keys.
    note_starts: list[tuple[int, str]] = []
    time_takens: dict[str, float] = {}
    for i, line in enumerate(text):
        m = RE_PROCESSING_NOTE.search(line)
        if m:
            note_starts.append((i, m.group("note_key")))
            continue
        m = RE_TIME_TAKEN.search(line)
        if m:
            time_takens[m.group("note_key")] = float(m.group("sec"))

    records: list[NoteCost] = []
    n_notes = len(note_starts)
    for idx, (line_no, note_key) in enumerate(note_starts):
        next_line_no = (
            note_starts[idx + 1][0] if idx + 1 < n_notes else len(text)
        )
        block_slice = text[line_no:next_line_no]
        token_kv: dict[str, float] = {}
        in_block = False
        for line in block_slice:
            if not in_block:
                if RE_TOKEN_BLOCK_HEADER.search(line):
                    in_block = True
                continue
            # We collect lines until "Overall Token Usage Averages" appears,
            # then stop — the per-note block ends right before it.
            if "Overall Token Usage Averages" in line:
                break
            m = RE_INFO_LINE_KV.search(line)
            if m:
                key = m.group("key").strip()
                if key in TOKEN_FIELDS:
                    try:
                        val = float(m.group("val").replace(",", ""))
                    except ValueError as e:
                        raise RuntimeError(
                            f"Failed to parse number from line: {line!r} in {path}"
                        ) from e
                    token_kv[TOKEN_FIELDS[key]] = val

        record = NoteCost(
            source_file=str(path),
            note_key=note_key,
            model_inferred=model_inferred,
            dataset_inferred=infer_dataset_from_note_key(note_key),
            duration_sec=time_takens.get(note_key),
            total_prompt_tokens=int(token_kv["total_prompt_tokens"])
            if "total_prompt_tokens" in token_kv
            else None,
            total_completion_tokens=int(token_kv["total_completion_tokens"])
            if "total_completion_tokens" in token_kv
            else None,
            total_tokens=int(token_kv["total_tokens"])
            if "total_tokens" in token_kv
            else None,
            num_chunks=int(token_kv["num_chunks"])
            if "num_chunks" in token_kv
            else None,
            avg_tokens_per_chunk=token_kv.get("avg_tokens_per_chunk"),
            total_original_chunk_tokens=int(token_kv["total_original_chunk_tokens"])
            if "total_original_chunk_tokens" in token_kv
            else None,
            avg_original_chunk_tokens=token_kv.get("avg_original_chunk_tokens"),
            avg_prompt_tokens_per_chunk=token_kv.get("avg_prompt_tokens_per_chunk"),
            avg_completion_tokens_per_chunk=token_kv.get("avg_completion_tokens_per_chunk"),
            avg_calls_per_chunk=token_kv.get("avg_calls_per_chunk"),
        )
        records.append(record)

    return records


def decumulate_within_log(records: list[NoteCost]) -> list[NoteCost]:
    """Convert cumulative log entries into per-note diffs.

    Groups records by ``source_file`` (preserving in-file order) and treats
    consecutive entries as cumulative — i.e. fields like ``total_prompt_tokens``,
    ``num_chunks``, ``total_original_chunk_tokens`` are running totals.  The
    first record in each file is taken as-is; subsequent records become
    ``current - previous``.  Records with no token data are passed through
    unmodified (they only carry duration).
    """
    from collections import OrderedDict

    by_file: dict[str, list[NoteCost]] = OrderedDict()
    for r in records:
        by_file.setdefault(r.source_file, []).append(r)

    decumed: list[NoteCost] = []
    for source_file, file_records in by_file.items():
        previous_with_tok: NoteCost | None = None
        for r in file_records:
            if r.total_tokens is None:
                # No token block in this record — pass through.
                decumed.append(r)
                continue
            # A negative diff would mean the cumulative counter was reset
            # between consecutive notes — happens when the job script
            # re-launched main.py in a fresh process (resume).  Treat such a
            # row as a fresh-start record (no previous_with_tok).  Detect by
            # checking whether the running totals went *down*.
            is_reset = previous_with_tok is not None and (
                (
                    r.total_prompt_tokens is not None
                    and previous_with_tok.total_prompt_tokens is not None
                    and r.total_prompt_tokens < previous_with_tok.total_prompt_tokens
                )
                or (
                    r.num_chunks is not None
                    and previous_with_tok.num_chunks is not None
                    and r.num_chunks < previous_with_tok.num_chunks
                )
            )
            if previous_with_tok is None or is_reset:
                # First per-note token block (or after a reset): take as-is.
                # The log's "avg_calls_per_chunk" is also cumulative for
                # later notes, so we can't trust it for non-first notes; for
                # the first / post-reset note it IS correct.
                decumed.append(r)
            else:
                # Compute the diff for cumulative integer fields.
                diff = NoteCost(
                    source_file=r.source_file,
                    note_key=r.note_key,
                    model_inferred=r.model_inferred,
                    dataset_inferred=r.dataset_inferred,
                    duration_sec=r.duration_sec,  # already per-note
                    total_prompt_tokens=(
                        r.total_prompt_tokens - previous_with_tok.total_prompt_tokens
                        if (
                            r.total_prompt_tokens is not None
                            and previous_with_tok.total_prompt_tokens is not None
                        )
                        else r.total_prompt_tokens
                    ),
                    total_completion_tokens=(
                        r.total_completion_tokens
                        - previous_with_tok.total_completion_tokens
                        if (
                            r.total_completion_tokens is not None
                            and previous_with_tok.total_completion_tokens is not None
                        )
                        else r.total_completion_tokens
                    ),
                    total_tokens=(
                        r.total_tokens - previous_with_tok.total_tokens
                        if (
                            r.total_tokens is not None
                            and previous_with_tok.total_tokens is not None
                        )
                        else r.total_tokens
                    ),
                    num_chunks=(
                        r.num_chunks - previous_with_tok.num_chunks
                        if (
                            r.num_chunks is not None
                            and previous_with_tok.num_chunks is not None
                        )
                        else r.num_chunks
                    ),
                    total_original_chunk_tokens=(
                        r.total_original_chunk_tokens
                        - previous_with_tok.total_original_chunk_tokens
                        if (
                            r.total_original_chunk_tokens is not None
                            and previous_with_tok.total_original_chunk_tokens is not None
                        )
                        else r.total_original_chunk_tokens
                    ),
                    # Recompute per-note averages from the diffs so they are
                    # internally consistent and not cumulative-averaged.
                    avg_tokens_per_chunk=None,
                    avg_original_chunk_tokens=None,
                    avg_prompt_tokens_per_chunk=None,
                    avg_completion_tokens_per_chunk=None,
                    avg_calls_per_chunk=None,
                )
                if diff.num_chunks and diff.num_chunks > 0:
                    if diff.total_tokens is not None:
                        diff.avg_tokens_per_chunk = diff.total_tokens / diff.num_chunks
                    if diff.total_prompt_tokens is not None:
                        diff.avg_prompt_tokens_per_chunk = (
                            diff.total_prompt_tokens / diff.num_chunks
                        )
                    if diff.total_completion_tokens is not None:
                        diff.avg_completion_tokens_per_chunk = (
                            diff.total_completion_tokens / diff.num_chunks
                        )
                    if diff.total_original_chunk_tokens is not None:
                        diff.avg_original_chunk_tokens = (
                            diff.total_original_chunk_tokens / diff.num_chunks
                        )
                # avg_calls_per_chunk is left None — the original log field is
                # a cumulative average over all chunks ever processed in this
                # job and cannot be inverted from diffs without the raw
                # num_calls totals.  Static per-stage call counts are derived
                # separately in compute_cost_table.py from the pipeline source.
                decumed.append(diff)

            previous_with_tok = r
    return decumed


def write_csv(records: Iterable[NoteCost], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(r) for r in records]
    if not rows:
        # fail-fast: empty parse is an error condition.
        raise RuntimeError("No note token-stat records parsed from any input log.")
    fieldnames = list(rows[0].keys())
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", help="slurm-*.out paths to parse")
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="CSV path to write the per-note token+timing rows.",
    )
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help=(
            "Collapse duplicate (model, dataset, note_key) rows that arise from "
            "resume-from-checkpoint sweeps within a single SLURM job.  Prefers "
            "rows with non-null token-stat data; otherwise keeps the row with "
            "the largest wall-clock duration."
        ),
    )
    parser.add_argument(
        "--decumulate",
        action="store_true",
        help=(
            "Per-note token / chunk fields in the older single-threaded "
            "main.py are CUMULATIVE within a SLURM job (LLMManager was "
            "shared across notes).  Setting --decumulate converts them to "
            "per-note diffs by subtracting the previous note's totals.  "
            "Should be applied BEFORE --dedupe."
        ),
    )
    args = parser.parse_args(argv)

    all_records: list[NoteCost] = []
    for log_path_str in args.logs:
        log_path = Path(log_path_str)
        if not log_path.is_file():
            raise FileNotFoundError(f"slurm log not found: {log_path}")
        records = parse_one_log(log_path)
        print(f"  {log_path.name}: {len(records)} note records", file=sys.stderr)
        all_records.extend(records)

    if args.decumulate:
        all_records = decumulate_within_log(all_records)
        print(
            f"  Decumulated: {len(all_records)} rows "
            f"({sum(1 for r in all_records if r.total_tokens is not None)} with token data)",
            file=sys.stderr,
        )

    if args.dedupe:
        # Each note may appear multiple times because of resume-from-checkpoint
        # sweeps within one job.  Collapse on (model, dataset, note_key) by
        # preferring rows that recorded a non-empty token-stat block; among the
        # remainder, prefer the one with the largest non-null wall-clock
        # duration (corresponds to the actual processing run rather than the
        # resume-cache hit).
        from collections import defaultdict as _dd

        grouped: dict[tuple[str, str, str], list[NoteCost]] = _dd(list)
        for r in all_records:
            grouped[(r.model_inferred, r.dataset_inferred, r.note_key)].append(r)
        deduped: list[NoteCost] = []
        for group in grouped.values():
            with_tok = [r for r in group if r.total_tokens is not None]
            if with_tok:
                deduped.append(with_tok[-1])
            else:
                with_dur = [r for r in group if r.duration_sec is not None]
                if with_dur:
                    with_dur.sort(key=lambda x: x.duration_sec or 0.0, reverse=True)
                    deduped.append(with_dur[0])
                else:
                    deduped.append(group[-1])
        print(
            f"  Dedupe: {len(all_records)} → {len(deduped)} rows "
            f"({sum(1 for r in deduped if r.total_tokens is not None)} with token data)",
            file=sys.stderr,
        )
        all_records = deduped

    write_csv(all_records, args.output)
    print(f"Wrote {len(all_records)} records to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
