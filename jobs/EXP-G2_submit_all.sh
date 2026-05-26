#!/bin/bash
# EXP-G2 launcher — submit (ablation × dataset) sbatch jobs with gpt-4o-mini.
#
# Sister of EXP-G (gpt-4o-1120). Same 5 ablations × 3 datasets = 15 jobs,
# same 2-notes-per-dataset matched slice, same fixed pipeline (branched
# from EXP-G 69d0a52 with the missing-CODE fix). Only MODEL_NAME differs:
# gpt4omini → gpt-4o-mini-0718 deployment.
#
#   HOLD_ON_FAIL=1 bash jobs/EXP-G2_submit_all.sh   # opt into §7 hold
#   bash jobs/EXP-G2_submit_all.sh                  # plain submit
#
# Ledger: runs/EXP-G2/logs/job_ids.txt

set -euo pipefail

: "${OPENAIKEY:?OPENAIKEY required}"

ABLATIONS=(full sapbert_off semchunk_off date_off step4_off)
DATASETS=(4CE coral_pdac coral_breastca)

LEDGER="runs/EXP-G2/logs/job_ids.txt"
mkdir -p runs/EXP-G2/logs
: > "${LEDGER}"

for abl in "${ABLATIONS[@]}"; do
    for ds in "${DATASETS[@]}"; do
        JOB_NAME="EXP-G2_${abl}_${ds}"
        echo "==> submitting ${JOB_NAME} (HOLD_ON_FAIL=${HOLD_ON_FAIL:-0})"
        export ABLATION="${abl}"
        export DATASET="${ds}"
        export MODEL_NAME="${MODEL_NAME:-gpt4omini}"
        out=$(sbatch --job-name="${JOB_NAME}" --parsable jobs/EXP-G2_run.sh)
        jobid="${out%%;*}"
        echo "${abl} ${ds} ${jobid}" >> "${LEDGER}"
        echo "    job_id=${jobid}"
    done
done

echo
echo "All EXP-G2 jobs submitted. Ledger: ${LEDGER}"
