#!/usr/bin/env bash
# Post-process: aggregate per-dataset predictions and run eval for each baseline.
#
# scripts/eval_predictions.py expects:
#   - prediction_dir: flat directory containing
#     "{dataset_dir}_{note_id}_default_{model_name}_with_positions.csv"
#   - groundtruth_dir: dir with subdirs per dataset
#   - model_name: substring used to construct the prediction filename
#
# After EXP-F sbatch jobs complete, predictions live in:
#   runs/EXP-F/{agent_label}/{dataset_dir}/*_with_positions.csv
#
# This script symlinks them into runs/EXP-F/{agent_label}/all/ and runs eval.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." &> /dev/null && pwd)

CONDA_PYTHON="${CONDA_PYTHON:-/home/zoy043/miniconda3/envs/sglang/bin/python}"
GOLD_ROOT="${GOLD_ROOT:-$PROJECT_ROOT/outputs/reviewed_updated2}"
RUNS_ROOT="${RUNS_ROOT:-$PROJECT_ROOT/runs/EXP-F}"

# Comma-separated list of agent labels (matches what was passed to baseline runs).
AGENTS="${AGENTS:-o3mini_sp,gpt4o_cot}"

for agent in ${AGENTS//,/ }; do
    agent_root="$RUNS_ROOT/$agent"
    if [[ ! -d "$agent_root" ]]; then
        echo "[WARN] $agent_root not found, skipping" >&2
        continue
    fi
    flat_dir="$agent_root/all"
    # Start from a clean flat dir. If we don't, a prior run's symlinks in
    # all/ are themselves at depth 2 under agent_root, so the find below
    # re-matches them and ln -sfn overwrites each to point at itself
    # (self-referencing). That silently dropped whichever dataset find
    # traversed before "all/" (alphabetically 4CE) from the eval.
    rm -rf "$flat_dir"
    mkdir -p "$flat_dir"
    # Symlink every per-dataset CSV into the flat dir. -path prune on the
    # flat dir is belt-and-suspenders in case it gets recreated mid-loop.
    find "$agent_root" -mindepth 2 -maxdepth 2 \
        -path "$flat_dir/*" -prune -o \
        -name "*_with_positions.csv" -print0 \
        | while IFS= read -r -d '' f; do
            ln -sfn "$f" "$flat_dir/$(basename "$f")"
        done

    eval_out_dir="$agent_root/eval"
    mkdir -p "$eval_out_dir"
    eval_json="$eval_out_dir/results.json"
    echo "=== Evaluating $agent → $eval_json ==="
    "$CONDA_PYTHON" "$PROJECT_ROOT/scripts/eval_predictions.py" \
        --prediction_dir "$flat_dir" \
        --groundtruth_dir "$GOLD_ROOT" \
        --columns mention code assertion_status value unit \
        --model_name "$agent" \
        --output_file "$eval_json" \
        --no_note_metrics
done

echo
echo "EXP-F eval complete. Metrics files:"
for agent in ${AGENTS//,/ }; do
    [[ -f "$RUNS_ROOT/$agent/eval/results_metrics.csv" ]] && \
        echo "  $RUNS_ROOT/$agent/eval/results_metrics.csv"
done
