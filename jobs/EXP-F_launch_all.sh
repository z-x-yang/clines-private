#!/usr/bin/env bash
# EXP-F launcher: submit all 6 jobs (2 baselines × 3 datasets).
#
# Prerequisite: OPENAIKEY must be set in the calling shell so that sbatch's
# --export=ALL forwards it to the compute node. The script aborts fast if
# the key is missing (CLAUDE.md §2 fail-fast).
#
# Usage:
#   export OPENAIKEY="<key from SharePoint>"
#   bash jobs/EXP-F_launch_all.sh
#
# Optional env:
#   HOLD_ON_FAIL=1  # default — let failed jobs hold the node for debug
#   MAX_NOTES=N     # cap per dataset for smoke test
#   PARTITION       # default 'short'; override if backfill is slow

set -euo pipefail

: "${OPENAIKEY:?OPENAIKEY env var required — get from https://hu.sharepoint.com/sites/azureai}"
export OPENAIENDPOINT="${OPENAIENDPOINT:-https://azure-ai.hms.edu}"
export HOLD_ON_FAIL="${HOLD_ON_FAIL:-1}"

# Resolve project root (this script lives in $PROJECT_ROOT/jobs/).
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd)
export PROJECT_ROOT

export CONDA_PYTHON="${CONDA_PYTHON:-/home/zoy043/miniconda3/envs/sglang/bin/python}"
if [[ ! -x "$CONDA_PYTHON" ]]; then
    echo "ERROR: CONDA_PYTHON not executable: $CONDA_PYTHON" >&2
    exit 2
fi

DATASETS=(4CE coral_annotated_pdac coral_annotated_breastca)

mkdir -p "$PROJECT_ROOT/logs/slurm" "$PROJECT_ROOT/runs/EXP-F"

submit_one() {
    local model="$1"
    local mode="$2"
    local agent_label="$3"
    local dataset="$4"
    local output_dir="$PROJECT_ROOT/runs/EXP-F/${agent_label}/${dataset}"
    mkdir -p "$output_dir"

    # Build --export string. Note: SLURM --export uses comma separators,
    # so values that contain commas must be quoted with caution. We avoid
    # commas in values here.
    local export_str="ALL"
    export_str+=",MODEL=${model}"
    export_str+=",MODE=${mode}"
    export_str+=",DATASETS=${dataset}"
    export_str+=",AGENT_LABEL=${agent_label}"
    export_str+=",PROJECT_ROOT=${PROJECT_ROOT}"
    export_str+=",OUTPUT_DIR=${output_dir}"
    export_str+=",CONDA_PYTHON=${CONDA_PYTHON}"
    export_str+=",HOLD_ON_FAIL=${HOLD_ON_FAIL}"
    if [[ -n "${MAX_NOTES:-}" ]]; then
        export_str+=",MAX_NOTES=${MAX_NOTES}"
    fi

    local jobname="EXP-F_${agent_label}_${dataset}"
    local out_log="${PROJECT_ROOT}/logs/slurm/${jobname}_%j.out"
    local err_log="${PROJECT_ROOT}/logs/slurm/${jobname}_%j.err"

    local jobid
    jobid=$(sbatch --parsable \
        --job-name="${jobname}" \
        --partition="${PARTITION:-short}" \
        --time="${TIME_LIMIT:-08:00:00}" \
        --output="$out_log" \
        --error="$err_log" \
        --export="$export_str" \
        "$PROJECT_ROOT/jobs/EXP-F_baseline.sh")

    echo "submitted jobid=${jobid} agent=${agent_label} dataset=${dataset}"
    echo "${jobid}|${agent_label}|${dataset}|${out_log/\%j/$jobid}|${err_log/\%j/$jobid}" \
        >> "$PROJECT_ROOT/runs/EXP-F/job_dispatch.log"
}

echo "EXP-F launching @ $(date -Iseconds)"
echo "  PROJECT_ROOT: $PROJECT_ROOT"
echo "  CONDA_PYTHON: $CONDA_PYTHON"
echo "  HOLD_ON_FAIL: $HOLD_ON_FAIL"
echo "  MAX_NOTES:    ${MAX_NOTES:-<unset, full run>}"
echo

# o3-mini single-prompt × 3 datasets
for ds in "${DATASETS[@]}"; do
    submit_one "o3-mini-0131" "single" "o3mini_sp" "$ds"
done

# gpt-4o CoT × 3 datasets
for ds in "${DATASETS[@]}"; do
    submit_one "gpt-4o-1120" "cot" "gpt4o_cot" "$ds"
done

echo
echo "All 6 jobs submitted. Track with:"
echo "  squeue -u \$USER --name=EXP-F_*"
echo
echo "Per-job monitor (after sbatch returns):"
echo "  bash ~/.claude/templates/slurm_monitor.sh <jobid> <err_log> <out_log>"
echo
echo "Dispatch log: $PROJECT_ROOT/runs/EXP-F/job_dispatch.log"
