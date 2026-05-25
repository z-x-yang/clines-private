#!/usr/bin/env python3
"""Single-call baselines for EXP-F (R5 A1 hard requirement).

Runs one of two baselines per dataset/note:

1) o3-mini single-prompt: chunked, but each chunk asks o3-mini to extract
   ALL fields (mention, code, assertion, value, unit, dates) in ONE prompt
   — no 4-step decomposition.

2) gpt-4o CoT single-call: same single-prompt structure on gpt-4o-1120
   with a brief chain-of-thought instruction prepended.

Design choices (per RESPONSE_PLAN §1.5):
- KEEP chunking. Full notes are 4-25KB → would blow context single-shot.
  Chunking pipeline matches CLINES (`pipeline_coordinator.py`): semchunk
  with cl100k_base @ 768 tokens, followed by the same short-chunk merging
  (`if len(prev) < 200 or len(item) < 300: prev += item`) so boundaries
  and chunk counts are comparable.
- DO NOT over-engineer prompts. Reasonable defaults only.
- fail-fast (CLAUDE.md §2): no OPENAIKEY → abort; bounded retries with
  explicit logging; chunk that cannot be parsed after max retries RAISES
  to fail the note. SLURM HOLD_ON_FAIL is the intended recovery path.
- Output schema matches outputs/with_positions/ (including `Unnamed: 0`
  index column on read-back) so scripts/eval_predictions.py reads without
  modification.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import demjson3
import pandas as pd
import semchunk
import tiktoken
from openai import AzureOpenAI


logger = logging.getLogger("exp_f_baseline")


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

# Matches llm_interface/providers/openai_provider.py registry as of commit
# 21c7e08; replicated here so this script is self-contained (the whole point
# of a single-call baseline is to NOT depend on CLINES's 4-step pipeline).
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "o3-mini-0131": {
        "api_version": "2024-12-01-preview",
        "is_reasoning": True,
    },
    "gpt-4o-1120": {
        "api_version": "2025-04-01-preview",
        "is_reasoning": False,
    },
}


# ---------------------------------------------------------------------------
# Output schema — must match outputs/with_positions/*.csv exactly
# ---------------------------------------------------------------------------

OUTPUT_COLUMNS: List[str] = [
    "term_index",
    "key",
    "admission_date",
    "discharge_date",
    "gender",
    "death_date",
    "birth_date",
    "race",
    "ethnicity",
    "zip_code",
    "mention",
    "context",
    "code",
    "type",
    "assertion_status",
    "body_location",
    "body_location_code",
    "value",
    "unit",
    "infer",
    "freq",
    "route",
    "note",
    "related",
    "begin_date",
    "end_date",
    "agent_type",
    "start_pos",
    "end_pos",
]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

# Reasonable single-prompt baseline. Mirrors CLINES's four-step output schema
# in ONE call: entity span + UMLS CUI + assertion + value/unit + dates.
# Kept intentionally non-elaborate. No task decomposition, no per-field rules
# document. This is the "30-minute practitioner prompt", not an optimized one.
SINGLE_PROMPT_TEMPLATE = """\
Extract structured clinical information from the medical note chunk below.

Return a JSON array. Each element is an object with these keys (use null for
inapplicable fields; do not omit keys):
- "mention": exact substring from the note (case + punctuation preserved)
- "code": single UMLS Concept Unique Identifier (CUI) plus preferred name,
  formatted as "CUI||preferred_name" (e.g. "C0004096||asthma"). Best guess
  if uncertain.
- "assertion_status": one of "Present", "Absent", "Possible", "Conditional",
  "Hypothetical", "Notassociated", "Historical"
- "value": numeric or qualitative value if the mention is a measurement
  (e.g. "127", "elevated", "Stage III"); null otherwise
- "unit": unit string (e.g. "mg/dL", "cm") if applicable; null otherwise
- "begin_date": calendar date (YYYY-MM-DD, YYYY-MM, or YYYY) when the event
  began, if explicitly stated in the chunk; null otherwise
- "end_date": calendar date when the event ended, if applicable; null
  otherwise

Extract:
- diseases, signs/symptoms, procedures, medications, lab tests, allergies,
  anatomical findings, devices
- For panel tests (Chem-7, CMP, CBC) extract each numeric component as a
  separate entity
- Negated findings ("no fever" -> extract "fever", assertion=Absent)

Do NOT extract:
- Person names, generic locations
- Values/units as standalone entities (attach them to their parent entity)

Output ONLY the JSON array. No prose, no markdown fences, no surrounding
text. The first character MUST be '[' and the last MUST be ']'.

NOTE CHUNK:
\"\"\"
{chunk}
\"\"\"
"""


# CoT variant: prepend a short instruction asking the model to reason
# before producing JSON. Minimal — no task-specific reasoning scaffold (that
# would be task decomposition, defeating the baseline). No few-shot beyond
# the format description. The model emits a single JSON array inside
# <answer> tags.
COT_PROMPT_TEMPLATE = """\
You are extracting structured clinical information from a medical note chunk.

First, think step by step inside <reasoning>...</reasoning> tags about which
clinical entities are present, their codes, and their assertion status.
Then output the final JSON array inside <answer>...</answer> tags. The
content inside <answer> MUST start with '[' and end with ']'. Do not put
anything outside those two tag pairs.

Inside <answer>, return a JSON array. Each element is an object with:
- "mention": exact substring from the note
- "code": "CUI||preferred_name" (UMLS Concept Unique Identifier)
- "assertion_status": "Present" | "Absent" | "Possible" | "Conditional" |
  "Hypothetical" | "Notassociated" | "Historical"
- "value": numeric / qualitative value if applicable, else null
- "unit": unit string if applicable, else null
- "begin_date": YYYY[-MM[-DD]] when event began (if explicit), else null
- "end_date": YYYY[-MM[-DD]] when event ended (if explicit), else null

Extraction scope:
- diseases, symptoms, procedures, medications, labs, allergies, findings
- For panel tests, each numeric component is a separate entity
- Negated findings: extract entity + assertion=Absent
- Do NOT extract person names or standalone values/units

NOTE CHUNK:
\"\"\"
{chunk}
\"\"\"
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ChunkResult:
    chunk_index: int
    chunk_start: int          # char offset within full note where chunk begins
    chunk_text_len: int       # char count of chunk
    chunk_token_count: int    # cl100k_base tokens of chunk
    api_calls: int            # actual successful API calls for this chunk
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    wall_seconds: float
    entities_parsed: int


@dataclass
class NoteResult:
    note_id: str
    dataset_dir: str
    num_chunks: int
    total_api_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    wall_seconds: float
    entities_emitted: int
    chunks: List[ChunkResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Azure OpenAI client (self-contained, fail-fast)
# ---------------------------------------------------------------------------


def _make_client(api_version: str) -> AzureOpenAI:
    key = os.environ.get("OPENAIKEY")
    endpoint = os.environ.get("OPENAIENDPOINT")
    if not key:
        raise RuntimeError(
            "OPENAIKEY env var is required (HMS Azure OpenAI key from "
            "https://hu.sharepoint.com/sites/azureai). Refusing to proceed."
        )
    if not endpoint:
        # Default per project convention (run_inference.sh).
        endpoint = "https://azure-ai.hms.edu"
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_version=api_version,
        api_key=key,
    )


def call_model(
    client: AzureOpenAI,
    model_name: str,
    prompt: str,
    max_retries: int = 3,
    initial_backoff_sec: float = 2.0,
) -> Dict[str, Any]:
    """Single API call with bounded retry on transient failures.

    Returns {"content": str, "prompt_tokens": int, "completion_tokens": int,
             "total_tokens": int, "retries": int, "wall_seconds": float}

    Per CLAUDE.md §2 fail-fast: explicit retry only for transient network /
    rate-limit errors (bounded, logged). Non-transient errors raise.
    """
    spec = MODEL_REGISTRY[model_name]
    messages = [
        {
            "role": "system",
            "content": (
                "You are a medical record processing AI. Extract clinical "
                "concepts faithfully and follow the requested output format "
                "exactly."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    start = time.time()
    retries = 0
    last_err: Optional[Exception] = None
    while retries <= max_retries:
        try:
            if spec["is_reasoning"]:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_completion_tokens=16384,
                    reasoning_effort="medium",
                )
            else:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.2,  # near-deterministic for fair eval
                )
            content = resp.choices[0].message.content if resp.choices else None
            if not content:
                raise RuntimeError(
                    f"empty content from {model_name} "
                    f"(finish_reason={resp.choices[0].finish_reason if resp.choices else 'none'})"
                )
            usage = resp.usage
            return {
                "content": content.strip(),
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
                "retries": retries,
                "wall_seconds": time.time() - start,
            }
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            transient = (
                "rate limit" in err_str
                or "timeout" in err_str
                or "timed out" in err_str
                or "connection" in err_str
                or "429" in err_str
                or "500" in err_str
                or "502" in err_str
                or "503" in err_str
                or "504" in err_str
            )
            if not transient or retries >= max_retries:
                logger.error(
                    "call_model giving up on model=%s after retries=%d err=%s",
                    model_name, retries, e,
                )
                raise
            backoff = initial_backoff_sec * (2 ** retries)
            logger.warning(
                "call_model transient err model=%s retry=%d backoff=%.1fs err=%s",
                model_name, retries + 1, backoff, e,
            )
            time.sleep(backoff)
            retries += 1

    raise RuntimeError(f"call_model unreachable; last_err={last_err}")


# ---------------------------------------------------------------------------
# Output parsing — strict contract enforcement
# ---------------------------------------------------------------------------


_COT_ANSWER_RE = re.compile(r"<answer>\s*(.*?)\s*</answer>", re.DOTALL | re.IGNORECASE)


class ParseError(ValueError):
    """Raised when the model response does not satisfy the prompt contract.

    No silent fallback: a chunk that fails parsing after retries fails the
    whole note. SLURM HOLD_ON_FAIL is the intended recovery mechanism.
    """


def _extract_json_payload(raw: str, mode: str) -> str:
    """Pull the JSON payload from the model response, contract-strict.

    - mode='single': prompt says output starts with '[' and ends with ']'.
      We require those bookends after whitespace strip.
    - mode='cot': prompt says JSON lives inside <answer>...</answer>; we
      require the tags and require the inner content to start/end with
      brackets. No fall back to bare code fences or whole-string bracket
      slicing — those would be hidden leniency (CLAUDE.md §2).
    """
    s = raw.strip()
    if mode == "cot":
        m = _COT_ANSWER_RE.search(s)
        if not m:
            raise ParseError(
                "CoT response missing <answer>...</answer> tags; raw_head="
                + repr(s[:120])
            )
        payload = m.group(1).strip()
    elif mode == "single":
        payload = s
    else:
        raise ValueError(f"unknown mode={mode!r}")
    if not (payload.startswith("[") and payload.endswith("]")):
        raise ParseError(
            f"payload not a bare JSON array (mode={mode}); "
            f"start={payload[:60]!r} end={payload[-60:]!r}"
        )
    return payload


def parse_chunk_response(raw: str, mode: str) -> List[Dict[str, Any]]:
    """Parse model response into list of entity dicts (strict).

    Raises ParseError on any contract violation.
    """
    payload = _extract_json_payload(raw, mode)
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as e:
        # demjson3 is more forgiving (trailing commas, single quotes).
        # This fallback is permitted because real models occasionally emit
        # cosmetic non-issues; we LOG when it triggers so it's not silent.
        logger.warning("strict json parse failed; trying demjson3: %s", e)
        try:
            parsed = demjson3.decode(payload)
        except Exception as e2:
            raise ParseError(
                f"both json and demjson3 failed: json={e}; demjson3={e2}; "
                f"payload_head={payload[:120]!r}"
            )
    if not isinstance(parsed, list):
        raise ParseError(
            f"expected JSON array, got {type(parsed).__name__}; "
            f"value_head={str(parsed)[:120]!r}"
        )
    return parsed


# ---------------------------------------------------------------------------
# Span localization (used-span tracking for repeated mentions)
# ---------------------------------------------------------------------------


def locate_span_with_state(
    note: str,
    mention: str,
    chunk_offset: int,
    chunk_len: int,
    used_spans: set,
) -> Tuple[int, int]:
    """Find character span of `mention` in original note.

    Picks the FIRST occurrence not in `used_spans` (matches CLINES NER's
    sequential matching behavior, e.g. ner_processor.py:421-434), so two
    LLM hits on the same surface form get distinct character spans.

    Search order:
    1. Inside chunk window [chunk_offset, chunk_offset + chunk_len), exact
    2. Inside chunk window, case-insensitive
    3. Whole note, exact
    4. Whole note, case-insensitive

    Mutates `used_spans` when a span is allocated.

    Returns (-1, -1) if no occurrence is found (or all are used).
    eval_predictions.py drops rows with start_pos/end_pos == -1, which is
    the correct behavior for unlocatable LLM outputs.
    """
    if not isinstance(mention, str) or not mention.strip():
        return -1, -1
    mention = mention.strip()
    window_end = min(len(note), chunk_offset + chunk_len)

    def _find_all(haystack: str, needle: str, base_offset: int) -> List[Tuple[int, int]]:
        out: List[Tuple[int, int]] = []
        start = 0
        n_len = len(needle)
        if n_len == 0:
            return out
        while True:
            idx = haystack.find(needle, start)
            if idx < 0:
                break
            out.append((base_offset + idx, base_offset + idx + n_len))
            start = idx + 1
        return out

    candidates: List[Tuple[int, int]] = []
    candidates += _find_all(note[chunk_offset:window_end], mention, chunk_offset)
    if not candidates:
        lo = note[chunk_offset:window_end].lower()
        candidates += _find_all(lo, mention.lower(), chunk_offset)
    if not candidates:
        candidates += _find_all(note, mention, 0)
    if not candidates:
        candidates += _find_all(note.lower(), mention.lower(), 0)

    for span in candidates:
        if span not in used_spans:
            used_spans.add(span)
            return span
    return -1, -1


# ---------------------------------------------------------------------------
# Chunking — match CLINES pipeline_coordinator.py:499-504
# ---------------------------------------------------------------------------


def chunk_note(note: str, chunk_size_tokens: int = 768) -> List[Tuple[str, int]]:
    """Return [(chunk_text, char_offset_in_note), ...].

    Mirrors `PipelineCoordinator.__call__` chunking exactly:
      1. semchunk with `tiktoken.encoding_for_model('gpt-4')` @ 768 tokens
      2. Adjacent merge: `if len(prev) < 200 or len(item) < 300: prev += item`

    Offsets are computed by `str.find()` over the original note with a
    running cursor (same approach as pipeline_coordinator.py:530-541),
    including the fallback to running cursor when `find` returns -1.
    """
    tokenizer = tiktoken.encoding_for_model("gpt-4")
    chunker = semchunk.chunkerify(tokenizer, chunk_size_tokens)
    raw = chunker(note)
    if not raw:
        return []

    # Same merge rule as CLINES (seed with empty string, then append/extend).
    merged: List[str] = [""]
    for item in raw:
        item_str = item if isinstance(item, str) else str(item)
        if len(merged[-1]) < 200 or len(item_str) < 300:
            merged[-1] += item_str
        else:
            merged.append(item_str)
    if merged and not merged[0]:
        merged = merged[1:]
    if not merged:
        return []

    out: List[Tuple[str, int]] = []
    current_offset = 0
    for i, c in enumerate(merged):
        if i == 0:
            offset = 0
        else:
            idx = note.find(c, current_offset)
            offset = idx if idx >= 0 else current_offset
        out.append((c, offset))
        current_offset = offset + len(c)
    return out


# ---------------------------------------------------------------------------
# Per-note inference
# ---------------------------------------------------------------------------


def _empty_predictions_df() -> pd.DataFrame:
    """Empty DataFrame with full output schema so eval_predictions.py won't
    crash on a note that legitimately has zero predictions."""
    return pd.DataFrame({c: pd.Series(dtype=object) for c in OUTPUT_COLUMNS})


def process_note(
    client: Optional[AzureOpenAI],
    model_name: str,
    note_text: str,
    note_id: str,
    dataset_dir: str,
    agent_label: str,
    mode: str,
    chunk_size_tokens: int,
    chunk_max_retries: int,
) -> Tuple[pd.DataFrame, NoteResult]:
    """Run single-call baseline on one note.

    Raises (does NOT silently swallow) if any chunk's parse/API path fails
    after `chunk_max_retries`. Caller decides whether to abort the run or
    skip the note via `--start-index` on resume.
    """
    note_start = time.time()
    chunks = chunk_note(note_text, chunk_size_tokens=chunk_size_tokens)
    logger.info("note=%s/%s chunks=%d", dataset_dir, note_id, len(chunks))

    template = COT_PROMPT_TEMPLATE if mode == "cot" else SINGLE_PROMPT_TEMPLATE
    tokenizer = tiktoken.encoding_for_model("gpt-4")

    rows: List[Dict[str, Any]] = []
    chunk_results: List[ChunkResult] = []
    term_index = 0

    for c_idx, (chunk_text, chunk_offset) in enumerate(chunks):
        prompt = template.format(chunk=chunk_text)
        chunk_token_count = len(tokenizer.encode(chunk_text))
        c_start = time.time()
        chunk_prompt_tok = chunk_completion_tok = chunk_total_tok = 0
        chunk_api_calls = 0
        entities: List[Dict[str, Any]] = []
        last_err: Optional[BaseException] = None

        for attempt in range(chunk_max_retries + 1):
            try:
                resp = call_model(client, model_name, prompt)
                chunk_api_calls += 1
                chunk_prompt_tok += resp["prompt_tokens"]
                chunk_completion_tok += resp["completion_tokens"]
                chunk_total_tok += resp["total_tokens"]
                entities = parse_chunk_response(resp["content"], mode)
                last_err = None
                break  # success
            except ParseError as e:
                last_err = e
                logger.warning(
                    "note=%s/%s chunk=%d attempt=%d ParseError: %s",
                    dataset_dir, note_id, c_idx, attempt + 1, e,
                )
            except Exception as e:
                # call_model already retried transients. A bare exception
                # here is non-transient (auth, contract violation in
                # response object, etc.). Fail fast.
                logger.error(
                    "note=%s/%s chunk=%d non-transient API error: %s",
                    dataset_dir, note_id, c_idx, e,
                )
                raise

        if last_err is not None:
            # Out of parse retries. Raise: this fails the note and (when
            # HOLD_ON_FAIL=1) keeps the SLURM node alive for user debug.
            raise ParseError(
                f"chunk {c_idx} of note {dataset_dir}/{note_id} failed all "
                f"{chunk_max_retries + 1} parse attempts; last_err="
                f"{type(last_err).__name__}: {last_err}"
            )

        # Convert entities -> output rows.
        used_spans: set = set()
        emitted_this_chunk = 0
        for ent in entities:
            if not isinstance(ent, dict):
                logger.warning(
                    "note=%s/%s chunk=%d non-dict entity in array: %r",
                    dataset_dir, note_id, c_idx, ent,
                )
                continue
            mention = ent.get("mention", "")
            code = ent.get("code", "")
            assertion = ent.get("assertion_status", "")
            value = ent.get("value")
            unit = ent.get("unit")
            begin_date = ent.get("begin_date")
            end_date = ent.get("end_date")

            start_pos, end_pos = locate_span_with_state(
                note_text, str(mention) if mention else "",
                chunk_offset, len(chunk_text), used_spans,
            )

            term_index += 1
            rows.append({
                "term_index": term_index,
                "key": f"{dataset_dir}_{note_id}",
                "admission_date": "",
                "discharge_date": "",
                "gender": "",
                "death_date": "",
                "birth_date": "",
                "race": "",
                "ethnicity": "",
                "zip_code": "",
                "mention": mention,
                "context": "",
                "code": code,
                "type": "",
                "assertion_status": assertion,
                "body_location": "",
                "body_location_code": "",
                "value": value if value not in (None, "") else "",
                "unit": unit if unit not in (None, "") else "",
                "infer": "",
                "freq": "",
                "route": "",
                "note": "",
                "related": "[]",
                "begin_date": begin_date if begin_date not in (None, "") else "",
                "end_date": end_date if end_date not in (None, "") else "",
                "agent_type": agent_label,
                "start_pos": start_pos,
                "end_pos": end_pos,
            })
            emitted_this_chunk += 1

        chunk_results.append(
            ChunkResult(
                chunk_index=c_idx,
                chunk_start=chunk_offset,
                chunk_text_len=len(chunk_text),
                chunk_token_count=chunk_token_count,
                api_calls=chunk_api_calls,
                prompt_tokens=chunk_prompt_tok,
                completion_tokens=chunk_completion_tok,
                total_tokens=chunk_total_tok,
                wall_seconds=time.time() - c_start,
                entities_parsed=emitted_this_chunk,
            )
        )

    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS) if rows else _empty_predictions_df()

    note_result = NoteResult(
        note_id=note_id,
        dataset_dir=dataset_dir,
        num_chunks=len(chunks),
        total_api_calls=sum(c.api_calls for c in chunk_results),
        total_prompt_tokens=sum(c.prompt_tokens for c in chunk_results),
        total_completion_tokens=sum(c.completion_tokens for c in chunk_results),
        total_tokens=sum(c.total_tokens for c in chunk_results),
        wall_seconds=time.time() - note_start,
        entities_emitted=len(rows),
        chunks=chunk_results,
    )
    return df, note_result


# ---------------------------------------------------------------------------
# CLI driver
# ---------------------------------------------------------------------------


def _gather_notes(
    data_root: Path, datasets: List[str], gold_root: Path
) -> List[Tuple[str, str, Path]]:
    """Return [(dataset_dir, note_id, note_path)] for notes that have gold."""
    items: List[Tuple[str, str, Path]] = []
    for dataset_dir in datasets:
        data_dir = data_root / dataset_dir
        gold_dir = gold_root / dataset_dir
        if not data_dir.is_dir():
            raise FileNotFoundError(f"missing data dir: {data_dir}")
        if not gold_dir.is_dir():
            raise FileNotFoundError(f"missing gold dir: {gold_dir}")
        gold_note_ids = {
            f.stem.replace("_updated", "")
            for f in gold_dir.iterdir()
            if f.name.endswith("_updated.csv")
        }
        for note_path in sorted(data_dir.glob("*.txt")):
            note_id = note_path.stem
            if note_id not in gold_note_ids:
                continue
            items.append((dataset_dir, note_id, note_path))
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=sorted(MODEL_REGISTRY.keys()))
    parser.add_argument("--mode", required=True, choices=["single", "cot"])
    parser.add_argument("--datasets", nargs="+", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--agent-label", required=True)
    parser.add_argument("--chunk-size-tokens", type=int, default=768)
    parser.add_argument("--chunk-max-retries", type=int, default=2)
    parser.add_argument("--max-notes", type=int, default=None,
                        help="cap per dataset (smoke test)")
    parser.add_argument("--start-index", type=int, default=0,
                        help="skip first N notes globally (resume helper)")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )

    spec = MODEL_REGISTRY[args.model]
    client = _make_client(spec["api_version"])
    args.output_dir.mkdir(parents=True, exist_ok=True)

    notes = _gather_notes(args.data_root, args.datasets, args.gold_root)
    if args.start_index:
        notes = notes[args.start_index:]
    if args.max_notes is not None:
        by_ds: Dict[str, int] = {}
        kept: List[Tuple[str, str, Path]] = []
        for ds, nid, p in notes:
            if by_ds.get(ds, 0) >= args.max_notes:
                continue
            by_ds[ds] = by_ds.get(ds, 0) + 1
            kept.append((ds, nid, p))
        notes = kept

    logger.info(
        "EXP-F start model=%s mode=%s datasets=%s notes=%d output=%s",
        args.model, args.mode, args.datasets, len(notes), args.output_dir,
    )

    usage_summary: List[Dict[str, Any]] = []
    for i, (dataset_dir, note_id, note_path) in enumerate(notes):
        note_text = note_path.read_text(encoding="utf-8", errors="ignore")
        if not note_text.strip():
            logger.warning("note=%s/%s is empty, skipping", dataset_dir, note_id)
            continue

        try:
            df, result = process_note(
                client=client,
                model_name=args.model,
                note_text=note_text,
                note_id=note_id,
                dataset_dir=dataset_dir,
                agent_label=args.agent_label,
                mode=args.mode,
                chunk_size_tokens=args.chunk_size_tokens,
                chunk_max_retries=args.chunk_max_retries,
            )
        except Exception:
            logger.exception(
                "note=%s/%s failed irrecoverably; aborting "
                "(resume with --start-index=%d)",
                dataset_dir, note_id, args.start_index + i,
            )
            raise

        out_csv = args.output_dir / (
            f"{dataset_dir}_{note_id}_default_{args.agent_label}_with_positions.csv"
        )
        # index=True so read-back has the same `Unnamed: 0` column as
        # outputs/with_positions/*.csv.
        df.to_csv(out_csv, index=True)

        usage_path = args.output_dir / "usage.jsonl"
        with usage_path.open("a") as f:
            f.write(json.dumps({
                "note_id": result.note_id,
                "dataset_dir": result.dataset_dir,
                "num_chunks": result.num_chunks,
                "total_api_calls": result.total_api_calls,
                "total_prompt_tokens": result.total_prompt_tokens,
                "total_completion_tokens": result.total_completion_tokens,
                "total_tokens": result.total_tokens,
                "wall_seconds": result.wall_seconds,
                "entities_emitted": result.entities_emitted,
                "chunks": [
                    {
                        "chunk_index": ch.chunk_index,
                        "chunk_start": ch.chunk_start,
                        "chunk_text_len": ch.chunk_text_len,
                        "chunk_token_count": ch.chunk_token_count,
                        "api_calls": ch.api_calls,
                        "prompt_tokens": ch.prompt_tokens,
                        "completion_tokens": ch.completion_tokens,
                        "total_tokens": ch.total_tokens,
                        "wall_seconds": ch.wall_seconds,
                        "entities_parsed": ch.entities_parsed,
                    } for ch in result.chunks
                ],
            }) + "\n")
        usage_summary.append({
            "note_id": result.note_id,
            "dataset_dir": result.dataset_dir,
            "num_chunks": result.num_chunks,
            "total_prompt_tokens": result.total_prompt_tokens,
            "total_completion_tokens": result.total_completion_tokens,
            "total_tokens": result.total_tokens,
            "wall_seconds": result.wall_seconds,
            "entities_emitted": result.entities_emitted,
            "total_api_calls": result.total_api_calls,
        })
        logger.info(
            "DONE note=%s/%s entities=%d tokens=%d wall=%.1fs (%d/%d)",
            dataset_dir, note_id, result.entities_emitted, result.total_tokens,
            result.wall_seconds, i + 1, len(notes),
        )

    summary_path = args.output_dir / "run_summary.json"
    total_prompt = sum(u["total_prompt_tokens"] for u in usage_summary)
    total_completion = sum(u["total_completion_tokens"] for u in usage_summary)
    total_tokens = sum(u["total_tokens"] for u in usage_summary)
    total_wall = sum(u["wall_seconds"] for u in usage_summary)
    total_entities = sum(u["entities_emitted"] for u in usage_summary)
    total_api_calls = sum(u["total_api_calls"] for u in usage_summary)
    summary = {
        "model": args.model,
        "mode": args.mode,
        "agent_label": args.agent_label,
        "datasets": args.datasets,
        "n_notes_processed": len(usage_summary),
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "total_api_calls": total_api_calls,
        "total_wall_seconds": total_wall,
        "total_entities": total_entities,
        "chunk_size_tokens": args.chunk_size_tokens,
    }
    with summary_path.open("w") as f:
        json.dump(summary, f, indent=2)
    logger.info("EXP-F run summary -> %s", summary_path)
    logger.info(
        "TOTAL notes=%d entities=%d tokens=%d (prompt=%d completion=%d) "
        "api_calls=%d wall=%.1fs",
        len(usage_summary), total_entities, total_tokens, total_prompt,
        total_completion, total_api_calls, total_wall,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
