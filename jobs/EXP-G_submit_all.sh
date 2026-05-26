#!/bin/bash
# EXP-G launcher — submit (ablation × dataset) sbatch jobs.
#
# Ablations: full | sapbert_off | semchunk_off | date_off | step4_off
# Datasets : 4CE | coral_pdac | coral_breastca
#
# Total = 5 × 3 = 15 sbatch jobs (Plan A re-launch 2026-05-26: each ~60-80min
# on gpu_quad with 90min walltime cap; original batch 1+2 with 30min walltime
# all timed out / failed and were the trigger for this re-launch).
# "full" runs serve as the matched-sample control (3 representative notes
# per dataset on the full pipeline, with the same GPT-4o-1120 deployment as
# the ablations). Reuse of `outputs/with_positions/` is NOT possible because
# that artifact covers different note sets; we need the matched 3-note slice
# for a fair ΔF1 comparison.
#
# Usage:
#   HOLD_ON_FAIL=1 bash jobs/EXP-G_submit_all.sh   # opt into §7 hold
#   bash jobs/EXP-G_submit_all.sh                  # plain submit, no hold
#
# Writes a job-id ledger to runs/EXP-G/logs/job_ids.txt for later monitor +
# eval bookkeeping.

set -euo pipefail

: "${OPENAIKEY:?OPENAIKEY required}"

ABLATIONS=(full sapbert_off semchunk_off date_off step4_off)
DATASETS=(4CE coral_pdac coral_breastca)

LEDGER="runs/EXP-G/logs/job_ids.txt"
mkdir -p runs/EXP-G/logs
: > "${LEDGER}"

for abl in "${ABLATIONS[@]}"; do
    for ds in "${DATASETS[@]}"; do
        JOB_NAME="EXP-G_${abl}_${ds}"
        echo "==> submitting ${JOB_NAME} (HOLD_ON_FAIL=${HOLD_ON_FAIL:-0})"
        # export so sbatch script sees them
        export ABLATION="${abl}"
        export DATASET="${ds}"
        export MODEL_NAME="${MODEL_NAME:-gpt4o}"
        out=$(sbatch --job-name="${JOB_NAME}" --parsable jobs/EXP-G_run.sh)
        jobid="${out%%;*}"  # strip cluster suffix if present
        echo "${abl} ${ds} ${jobid}" >> "${LEDGER}"
        echo "    job_id=${jobid}"
    done
done

echo
echo "All EXP-G jobs submitted. Ledger: ${LEDGER}"
echo "Monitor each with: bash scripts/slurm_monitor.sh <jobid> runs/EXP-G/logs/slurm-<jobid>.err runs/EXP-G/logs/slurm-<jobid>.out"
