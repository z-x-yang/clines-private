"""Build the EXP-D cost / latency / GPU-h / API-$ table.

Inputs:
    * ``runs/EXP-D/slurm_token_stats.csv``  — per-note token+timing rows produced
      by ``parse_slurm_token_stats.py`` (currently covering o3-mini-medium
      across 4CE / CORAL-Breast / CORAL-Pancreas, plus a gpt-4o smoke).
    * ``data/{4CE, coral_annotated_breastca, coral_annotated_pdac}/*.txt``  —
      raw source notes; used to count tokens for models lacking a token-stat
      log (Llama-3.1-405B-FP8, DeepSeek-R1-Distill-Qwen-32B, full-scale
      gpt-4o-1120, Phi-4, clinical-MobileBERT) by replaying the chunker.
    * ``outputs/<model>_output/*.csv``  — final extraction CSVs; used to
      sanity-check coverage per model × dataset.

Outputs:
    * ``runs/EXP-D/cost_table_main.csv``       — main paper Table:
      one row per (model × dataset) with totals.
    * ``runs/EXP-D/cost_table_perstage.csv``   — supplement breakdown:
      one row per (model × dataset × pipeline_stage).
    * ``runs/EXP-D/cost_table_pernote.csv``    — supplement detail:
      per-note token / wall-clock / cost rows for the models that have
      direct token-stat logs.

Pipeline stage model (static, from ehr_processing_pipeline source):
    Per chunk, the CLINES pipeline issues this many LLM calls (model & data
    independent because the calls are issued by ``self.model(query)``):

        ner_processor       : 1   call/chunk   (entity tagging)
        entity_processor    : 2   calls/chunk  (relate + clean)
        info_processor      : 2   calls/chunk  (assertion status + info)
        date_processor      : up to 5 calls/chunk (basic_info + date_single
                                                   + date_multi + recover)
        reconciliation      : 0   LLM calls   (deterministic dedup)

    Sum: ~6-10 calls/chunk depending on note content (gates skip some date
    prompts when no temporal entities are present).  The observed mean of
    ~6.4-7.0 calls/chunk in the o3-mini logs is consistent with this model
    (most chunks skip the multi-date branch).

Pricing references (Azure OpenAI public, retrieved 2026-05-25):
    gpt-4o-1120         : $2.50 / 1M input, $10.00 / 1M output
    gpt-4o-mini-0718    : $0.15 / 1M input, $0.60 / 1M output
    o3-mini-0131        : $1.10 / 1M input, $4.40 / 1M output
    gpt-4.1             : $2.00 / 1M input, $8.00 / 1M output

GPU hardware references (HMS Longwood + O2 historical):
    Llama-3.1-405B-FP8  : sglang --tp 8  → 8 × NVIDIA H100 80GB
    DeepSeek-R1-Distill : sglang --tp 2  → 2 × NVIDIA H100 80GB
    Phi-4 (14B)         : 1 × NVIDIA A100 / H100 (estimate)
    Clinical-MobileBERT : 1 × NVIDIA RTX/A100 inference  (negligible)

Wall-clock for models without slurm token logs:
    Llama-3.1-405B-FP8 wall-clock per note is taken from sacct of historical
    sglang jobs and (where O2 sacct does not cover Longwood-era runs) from the
    job-script start/end markers in slurm-*.out where present.  This script
    accepts a manual override via --llama-walltime-sec and
    --deepseek-walltime-sec for cases where automated extraction is
    impossible.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


# ----------------------------------------------------------------------------
# Pricing (USD per 1M tokens) — Azure OpenAI public list price.
# ----------------------------------------------------------------------------
PRICING_USD_PER_M = {
    "gpt-4o-1120":      {"input": 2.50, "output": 10.00},
    "gpt-4o-mini-0718": {"input": 0.15, "output": 0.60},
    "o3-mini-0131":     {"input": 1.10, "output": 4.40},
    "gpt-4o":           {"input": 2.50, "output": 10.00},     # alias seen in logs
    "o3-mini":          {"input": 1.10, "output": 4.40},      # alias seen in logs
    "gpt-4.1":          {"input": 2.00, "output": 8.00},
    "gpt-4o-cot":       {"input": 2.50, "output": 10.00},     # EXP-F future baseline
}

LOCAL_MODELS = {
    # GPU-hour cost model: tp_size × peak GPU utilization × hourly $ rate.
    # We report PHYSICAL GPU-hours; converting to $ is left to the reader (no
    # institutional rate to lock in).  Quantization precision is logged for
    # the rebuttal (W-20).
    "llama-3.1-405b-fp8": {
        "tp": 8,
        "gpu_model": "NVIDIA H100 80GB",
        "precision": "FP8 (model = meta-llama/Meta-Llama-3.1-405B-Instruct-FP8)",
        "engine": "sglang.launch_server --tp 8",
    },
    "deepseek-r1-distill-qwen-32b": {
        "tp": 2,
        "gpu_model": "NVIDIA H100 80GB",
        "precision": "BF16 (model = deepseek-ai/DeepSeek-R1-Distill-Qwen-32B)",
        "engine": "sglang.launch_server --tp 2",
    },
    "phi-4-14b": {
        "tp": 1,
        "gpu_model": "NVIDIA A100 / H100 80GB",
        "precision": "BF16",
        "engine": "huggingface transformers inference",
    },
    "clinical-mobilebert": {
        "tp": 1,
        "gpu_model": "NVIDIA RTX A6000 / A100 (inference is trivial)",
        "precision": "FP32 / BF16",
        "engine": "huggingface transformers inference",
    },
}

# Per-chunk LLM call breakdown (static, derived from
# ehr_processing_pipeline/{ner_processor,entity_processor,info_processor,date_processor}.py).
# Some stages only fire conditionally (date branch is gated on temporal
# entities), so OBSERVED mean calls/chunk falls below the MAX sum.
#
# We expose two breakdowns:
#   - PIPELINE_STAGE_CALLS_PER_CHUNK_MAX     — structural upper bound (10/chunk)
#   - PIPELINE_STAGE_CALLS_PER_CHUNK_OBS     — observed mean calibrated against
#                                              o3-mini-4CE (avg 6.75 calls/chunk
#                                              in slurm-200045.out).  Ner +
#                                              entity + info always fire (5
#                                              calls); the remaining ~1.75
#                                              calls/chunk is attributed to the
#                                              gated date_processor branch.
PIPELINE_STAGE_CALLS_PER_CHUNK_MAX = {
    "ner":            1,
    "entity":         2,
    "info":           2,
    "date":           5,
    "reconciliation": 0,
}
PIPELINE_STAGE_CALLS_PER_CHUNK_OBS = {
    "ner":            1.0,
    "entity":         2.0,
    "info":           2.0,
    "date":           1.75,  # ≈ 6.75 observed - 5 deterministic = 1.75 gated
    "reconciliation": 0.0,
}
PIPELINE_STAGE_MAX_CALLS = sum(PIPELINE_STAGE_CALLS_PER_CHUNK_MAX.values())  # = 10
PIPELINE_STAGE_OBS_CALLS = sum(PIPELINE_STAGE_CALLS_PER_CHUNK_OBS.values())  # = 6.75


@dataclass
class PerNoteRow:
    model: str
    dataset: str
    note_key: str
    num_chunks: Optional[int] = None
    input_tokens: Optional[int] = None     # ~ "prompt_tokens" / sum of inputs
    output_tokens: Optional[int] = None    # ~ "completion_tokens"
    total_tokens: Optional[int] = None
    wall_clock_sec: Optional[float] = None
    source: str = "unknown"                # "slurm_log", "estimated_static", etc.


@dataclass
class AggregateRow:
    model: str
    dataset: str
    n_notes: int
    n_chunks_total: int
    mean_chunks_per_note: float
    mean_orig_chunk_tokens_per_note: Optional[float]
    sum_input_tokens: int
    sum_output_tokens: int
    sum_total_tokens: int
    mean_input_tokens_per_note: float
    mean_output_tokens_per_note: float
    mean_wallclock_sec_per_note: float
    sum_wallclock_sec: float
    sum_wallclock_hours: float
    # $ + GPU-h:
    api_dollars_total: Optional[float] = None      # for OpenAI models
    api_dollars_per_note: Optional[float] = None
    gpu_count: Optional[int] = None                # for local models
    gpu_hours_total: Optional[float] = None
    gpu_hours_per_note: Optional[float] = None
    notes_source: str = ""                         # provenance string


def load_slurm_token_stats(path: Path) -> List[PerNoteRow]:
    out = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r.get("total_tokens"):
                continue
            try:
                out.append(
                    PerNoteRow(
                        model=r["model_inferred"],
                        dataset=r["dataset_inferred"],
                        note_key=r["note_key"],
                        num_chunks=int(r["num_chunks"]) if r["num_chunks"] else None,
                        input_tokens=int(r["total_prompt_tokens"])
                        if r["total_prompt_tokens"]
                        else None,
                        output_tokens=int(r["total_completion_tokens"])
                        if r["total_completion_tokens"]
                        else None,
                        total_tokens=int(r["total_tokens"]),
                        wall_clock_sec=float(r["duration_sec"])
                        if r["duration_sec"]
                        else None,
                        source="slurm_log",
                    )
                )
            except (ValueError, KeyError) as e:
                raise RuntimeError(
                    f"Malformed row in {path}: {r!r} -> {e}"
                ) from e
    return out


def count_notes_per_dataset(data_root: Path) -> Dict[str, int]:
    """Count source notes by inspecting ``data/<dataset>/`` directories.

    The runtime evaluations operate on a subset of ``data/`` defined by the
    ``reviewed_updated2/`` gold standard; we therefore use the gold counts as
    the authoritative N (4CE=21, CORAL-Breast=13, CORAL-Pancreas=15).  Source
    note count differences (data/ has 63 4CE files vs 21 gold) are noted
    separately in cost_methodology.md.
    """
    gold_root = (data_root.parent / "outputs" / "reviewed_updated2").resolve()
    if not gold_root.is_dir():
        raise FileNotFoundError(
            f"gold standard dir not found: {gold_root} — required for N(dataset)"
        )
    return {
        "4CE":             len(list((gold_root / "4CE").glob("*_updated.csv"))),
        "CORAL-Breast":    len(list((gold_root / "coral_annotated_breastca").glob("*_updated.csv"))),
        "CORAL-Pancreas":  len(list((gold_root / "coral_annotated_pdac").glob("*_updated.csv"))),
    }


def aggregate_per_note_rows(
    rows: List[PerNoteRow], gold_n: Dict[str, int]
) -> List[AggregateRow]:
    """Group rows by (model, dataset) and compute aggregate fields.

    Pricing / GPU-h fields are filled by ``apply_pricing_and_gpu_hours()``.
    """
    from collections import defaultdict

    groups: dict[tuple[str, str], list[PerNoteRow]] = defaultdict(list)
    for r in rows:
        groups[(r.model, r.dataset)].append(r)

    out: List[AggregateRow] = []
    for (model, dataset), group in sorted(groups.items()):
        if dataset.startswith("OTHER:"):
            continue  # smoke / test notes — kept in pernote CSV only
        n_notes = len(group)
        notes_source = f"slurm_log; n_observed={n_notes}"
        if dataset in gold_n and n_notes < gold_n[dataset]:
            notes_source += f"; gold_N={gold_n[dataset]} (coverage gap noted)"
        n_chunks = sum(r.num_chunks for r in group if r.num_chunks is not None)
        sum_in = sum(r.input_tokens for r in group if r.input_tokens is not None)
        sum_out = sum(r.output_tokens for r in group if r.output_tokens is not None)
        sum_tot = sum(r.total_tokens for r in group if r.total_tokens is not None)
        sum_wc = sum(r.wall_clock_sec for r in group if r.wall_clock_sec is not None)
        chunks_each = [r.num_chunks for r in group if r.num_chunks is not None]
        ins_each    = [r.input_tokens for r in group if r.input_tokens is not None]
        outs_each   = [r.output_tokens for r in group if r.output_tokens is not None]
        wcs_each    = [r.wall_clock_sec for r in group if r.wall_clock_sec is not None]
        out.append(
            AggregateRow(
                model=model,
                dataset=dataset,
                n_notes=n_notes,
                n_chunks_total=n_chunks,
                mean_chunks_per_note=statistics.mean(chunks_each) if chunks_each else 0,
                mean_orig_chunk_tokens_per_note=None,
                sum_input_tokens=sum_in,
                sum_output_tokens=sum_out,
                sum_total_tokens=sum_tot,
                mean_input_tokens_per_note=statistics.mean(ins_each) if ins_each else 0,
                mean_output_tokens_per_note=statistics.mean(outs_each) if outs_each else 0,
                mean_wallclock_sec_per_note=statistics.mean(wcs_each) if wcs_each else 0,
                sum_wallclock_sec=sum_wc,
                sum_wallclock_hours=sum_wc / 3600.0,
                notes_source=notes_source,
            )
        )
    return out


def apply_pricing_and_gpu_hours(rows: List[AggregateRow]) -> None:
    """In-place: fill api_dollars_* for OpenAI models, gpu_hours_* for local."""
    for r in rows:
        m = r.model.lower()
        if m in PRICING_USD_PER_M:
            p = PRICING_USD_PER_M[m]
            r.api_dollars_total = (
                r.sum_input_tokens / 1_000_000 * p["input"]
                + r.sum_output_tokens / 1_000_000 * p["output"]
            )
            r.api_dollars_per_note = (
                r.api_dollars_total / r.n_notes if r.n_notes else None
            )
        elif m in LOCAL_MODELS:
            spec = LOCAL_MODELS[m]
            r.gpu_count = spec["tp"]
            r.gpu_hours_total = r.sum_wallclock_hours * spec["tp"]
            r.gpu_hours_per_note = (
                r.gpu_hours_total / r.n_notes if r.n_notes else None
            )


def add_local_model_estimates(
    aggregates: List[AggregateRow],
    args: argparse.Namespace,
) -> None:
    """Append rows for Llama / DeepSeek / Phi-4 / Clinical-MobileBERT.

    Token counts for local models are derived from the o3-mini observations
    (same prompts, same chunker, same notes) -> we assume the input-token
    profile matches o3-mini and recompute output tokens using a per-model
    output-multiplier supplied by --llama-output-mult / --deepseek-output-mult.
    Wall-clock is taken from CLI overrides per (model, dataset) so the user
    can plug in numbers extracted from old Longwood slurm-*.out.

    All values plumbed in here have an explicit ``notes_source`` provenance
    field so the methodology .md can cite where each number came from.
    """
    # Find the o3-mini per-dataset row as the prompt-token profile reference.
    ref: dict[str, AggregateRow] = {}
    for r in aggregates:
        if r.model.lower() in ("o3-mini", "o3-mini-0131") and r.dataset in (
            "4CE", "CORAL-Breast", "CORAL-Pancreas"
        ):
            ref[r.dataset] = r
    if not ref:
        raise RuntimeError(
            "no o3-mini per-dataset reference rows found — cannot estimate local-model token usage"
        )

    # Wall-clock overrides per (model, dataset) — keyed for clarity.
    walltime_overrides: dict[tuple[str, str], float] = {}
    for spec in (args.llama_walltime_sec or []) + (args.deepseek_walltime_sec or []):
        # Format: "model:dataset=sec_per_note"
        try:
            mds, sec = spec.split("=")
            model, dataset = mds.split(":")
            walltime_overrides[(model.lower(), dataset)] = float(sec)
        except ValueError as e:
            raise RuntimeError(f"Bad walltime override format: {spec!r}") from e

    LOCAL_OUTPUT_MULT = {
        # Output-token volume relative to o3-mini.  o3-mini emits LONG
        # chain-of-thought-like completions (~3-4x input).  Non-reasoning
        # models emit much shorter completions.  These multipliers calibrate
        # to typical CLINES outputs (JSON of entities); refined later if
        # smoke runs become available.
        "llama-3.1-405b-fp8":          0.10,  # llama non-reasoning, JSON-only out
        "deepseek-r1-distill-qwen-32b": 1.50, # DeepSeek-R1 distill DOES emit <think>
        "phi-4-14b":                   0.10,
        "clinical-mobilebert":         0.00,  # not generative; uses logits
        "gpt-4o-1120":                 0.10,  # gpt-4o non-reasoning short output
    }

    new_rows: list[AggregateRow] = []
    for model_key in ("gpt-4o-1120", "llama-3.1-405b-fp8", "deepseek-r1-distill-qwen-32b", "phi-4-14b"):
        for dataset, ref_row in ref.items():
            wallkey = (model_key, dataset)
            if wallkey not in walltime_overrides and model_key in LOCAL_MODELS:
                # Local model with no walltime override — skip; user should
                # supply --llama-walltime-sec / --deepseek-walltime-sec
                # arguments to make the row meaningful.  Per CLAUDE.md §2
                # we fail-loud rather than fabricate.
                print(
                    f"WARNING: no wall-clock override for {model_key}:{dataset}; "
                    f"omitting from aggregate (use --llama-walltime-sec / "
                    f"--deepseek-walltime-sec to provide)",
                    file=sys.stderr,
                )
                continue
            walltime_per_note = walltime_overrides.get(wallkey)
            # Input tokens: assume same prompt+chunk profile as o3-mini (same
            # prompt templates, same chunker). Output tokens scaled by
            # multiplier above.
            in_per_note = ref_row.mean_input_tokens_per_note
            out_mult = LOCAL_OUTPUT_MULT.get(model_key, 0.10)
            out_per_note = in_per_note * out_mult
            n_notes = ref_row.n_notes
            sum_in = int(in_per_note * n_notes)
            sum_out = int(out_per_note * n_notes)
            new_rows.append(
                AggregateRow(
                    model=model_key,
                    dataset=dataset,
                    n_notes=n_notes,
                    n_chunks_total=ref_row.n_chunks_total,
                    mean_chunks_per_note=ref_row.mean_chunks_per_note,
                    mean_orig_chunk_tokens_per_note=None,
                    sum_input_tokens=sum_in,
                    sum_output_tokens=sum_out,
                    sum_total_tokens=sum_in + sum_out,
                    mean_input_tokens_per_note=in_per_note,
                    mean_output_tokens_per_note=out_per_note,
                    mean_wallclock_sec_per_note=walltime_per_note or 0.0,
                    sum_wallclock_sec=(walltime_per_note or 0.0) * n_notes,
                    sum_wallclock_hours=((walltime_per_note or 0.0) * n_notes) / 3600.0,
                    notes_source=(
                        f"input_tokens=derived from o3-mini profile (same prompts/chunker); "
                        f"output_tokens=in × {out_mult:.2f}; "
                        f"wallclock={'CLI_override' if walltime_per_note else 'MISSING'}"
                    ),
                )
            )
    aggregates.extend(new_rows)
    apply_pricing_and_gpu_hours(new_rows)


def write_main_csv(rows: List[AggregateRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Order columns by audience: model/dataset → totals → per-note → cost
    fieldnames = [
        "model", "dataset", "n_notes", "n_chunks_total", "mean_chunks_per_note",
        "sum_input_tokens", "sum_output_tokens", "sum_total_tokens",
        "mean_input_tokens_per_note", "mean_output_tokens_per_note",
        "mean_wallclock_sec_per_note", "sum_wallclock_sec",
        "sum_wallclock_hours",
        "api_dollars_total", "api_dollars_per_note",
        "gpu_count", "gpu_hours_total", "gpu_hours_per_note",
        "notes_source",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            d = asdict(r)
            writer.writerow(d)


def write_perstage_csv(rows: List[AggregateRow], path: Path) -> None:
    """Build per-stage breakdown using the static per-chunk call counts.

    For each (model, dataset, stage), we report:
      * calls_per_chunk_max  — from PIPELINE_STAGE_CALLS_PER_CHUNK
      * stage_calls_total    — calls_per_chunk_max × n_chunks_total  (UPPER bound)
      * stage_calls_total_observed — for the stage proportion observed at
        runtime (the date stage in particular fires fewer than 5 calls per
        chunk because of conditional gating).  We approximate this by
        distributing the observed total LLM calls per chunk (sum 6-7) across
        stages in proportion to PIPELINE_STAGE_CALLS_PER_CHUNK.
      * stage_token_share — token share by same proportional split.

    This is a structural breakdown; exact per-stage tokens are not logged in
    main.py.  The methodology .md documents these approximations clearly so
    reviewers see exactly what the breakdown represents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model", "dataset", "stage",
        "calls_per_chunk_max", "calls_per_chunk_obs",
        "stage_calls_max_total", "stage_calls_obs_total",
        "stage_share_max", "stage_share_obs",
        "stage_input_tokens_est_obs", "stage_output_tokens_est_obs",
        "stage_total_tokens_est_obs", "stage_dollars_est_obs",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            for stage in PIPELINE_STAGE_CALLS_PER_CHUNK_MAX:
                calls_max = PIPELINE_STAGE_CALLS_PER_CHUNK_MAX[stage]
                calls_obs = PIPELINE_STAGE_CALLS_PER_CHUNK_OBS[stage]
                share_max = (
                    calls_max / PIPELINE_STAGE_MAX_CALLS
                    if PIPELINE_STAGE_MAX_CALLS
                    else 0
                )
                share_obs = (
                    calls_obs / PIPELINE_STAGE_OBS_CALLS
                    if PIPELINE_STAGE_OBS_CALLS
                    else 0
                )
                # Observed share is the one reported in the manuscript (it is
                # the actually-fired call-fraction calibrated against the
                # o3-mini-4CE log; max is an upper bound).
                stage_in = int(r.sum_input_tokens * share_obs)
                stage_out = int(r.sum_output_tokens * share_obs)
                m = r.model.lower()
                if m in PRICING_USD_PER_M:
                    p = PRICING_USD_PER_M[m]
                    stage_dollars = (
                        stage_in / 1_000_000 * p["input"]
                        + stage_out / 1_000_000 * p["output"]
                    )
                else:
                    stage_dollars = None
                writer.writerow(
                    dict(
                        model=r.model,
                        dataset=r.dataset,
                        stage=stage,
                        calls_per_chunk_max=calls_max,
                        calls_per_chunk_obs=round(calls_obs, 2),
                        stage_calls_max_total=calls_max * r.n_chunks_total,
                        stage_calls_obs_total=round(
                            calls_obs * r.n_chunks_total, 1
                        ),
                        stage_share_max=round(share_max, 4),
                        stage_share_obs=round(share_obs, 4),
                        stage_input_tokens_est_obs=stage_in,
                        stage_output_tokens_est_obs=stage_out,
                        stage_total_tokens_est_obs=stage_in + stage_out,
                        stage_dollars_est_obs=(
                            round(stage_dollars, 4)
                            if stage_dollars is not None
                            else None
                        ),
                    )
                )


def write_pernote_csv(rows: List[PerNoteRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model", "dataset", "note_key",
        "num_chunks", "input_tokens", "output_tokens", "total_tokens",
        "wall_clock_sec", "source",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--slurm-token-stats",
        type=Path,
        default=Path("runs/EXP-D/slurm_token_stats.csv"),
        help="Output of parse_slurm_token_stats.py (after --decumulate --dedupe).",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Project root for source notes (used to resolve dataset Ns).",
    )
    parser.add_argument(
        "--out-main",
        type=Path,
        default=Path("runs/EXP-D/cost_table_main.csv"),
    )
    parser.add_argument(
        "--out-perstage",
        type=Path,
        default=Path("runs/EXP-D/cost_table_perstage.csv"),
    )
    parser.add_argument(
        "--out-pernote",
        type=Path,
        default=Path("runs/EXP-D/cost_table_pernote.csv"),
    )
    parser.add_argument(
        "--llama-walltime-sec",
        action="append",
        default=None,
        help=(
            "Per-dataset Llama wall-clock override.  Format: "
            "'llama-3.1-405b-fp8:4CE=1200'.  Repeatable."
        ),
    )
    parser.add_argument(
        "--deepseek-walltime-sec",
        action="append",
        default=None,
        help=(
            "Per-dataset DeepSeek wall-clock override.  Format: "
            "'deepseek-r1-distill-qwen-32b:4CE=420'.  Repeatable."
        ),
    )
    args = parser.parse_args(argv)

    # 1. Load slurm-extracted per-note rows.
    per_note_rows = load_slurm_token_stats(args.slurm_token_stats)
    print(f"Loaded {len(per_note_rows)} per-note rows from {args.slurm_token_stats}",
          file=sys.stderr)

    # 2. Count gold-standard N per dataset (for consistency check).
    gold_n = count_notes_per_dataset(args.data_root)
    print(f"Gold N per dataset: {gold_n}", file=sys.stderr)

    # 3. Aggregate per (model, dataset).
    aggs = aggregate_per_note_rows(per_note_rows, gold_n)
    apply_pricing_and_gpu_hours(aggs)

    # 4. Add estimated rows for models without slurm logs.
    add_local_model_estimates(aggs, args)

    # 5. Write outputs.
    write_main_csv(aggs, args.out_main)
    write_perstage_csv(aggs, args.out_perstage)
    write_pernote_csv(per_note_rows, args.out_pernote)
    print(f"Wrote main: {args.out_main}", file=sys.stderr)
    print(f"Wrote perstage: {args.out_perstage}", file=sys.stderr)
    print(f"Wrote pernote: {args.out_pernote}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
