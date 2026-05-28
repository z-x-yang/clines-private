#!/bin/bash
#SBATCH --job-name=EXP-J2_cell
#SBATCH --time=05:00:00
#SBATCH --mem=96G
#SBATCH -c 8
#SBATCH -p short
#SBATCH --array=0-14%15
#SBATCH --output=runs/EXP-J2/logs/cell-%A_%a.out
#SBATCH --error=runs/EXP-J2/logs/cell-%A_%a.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=zongxin_yang@hms.harvard.edu

# EXP-J2 = output-consistency re-run on the OPTIMIZED i2b2 pipeline (commit
# adca819: chunk-window-restricted entity alignment [Lever 1, already on i2b2]
# + quick_ratio-pruned fuzzy matcher [Lever 2]). Supersedes EXP-J, which ran
# on a stale pre-window-fix worktree (d04b219) and was 5-7x slower for the
# wrong reason (whole-document O(N*M^2) fuzzy scan).
#
# Grid: SLURM_ARRAY_TASK_ID 0..14 -> (R in 1..5) x (slice in 4CE/breastca/pdac),
# now %15 (all cells concurrent) to overlap the HMS Azure proxy per-call
# latency across cells (the residual bottleneck once fuzzy is fixed; fuzzy
# itself is no longer dominant). CPU + API only.
#
# Compliance: §7 HOLD_ON_FAIL (opt-in env, default OFF); fail-fast; §10 Monitor.

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-.}"
if [[ ! -d data || ! -d jobs ]]; then
    echo "ERROR: must run from repo root (need data/ + jobs/). cwd=$(pwd)" >&2
    exit 4
fi

source scripts/slurm_failure_hold.sh   # default OFF; HOLD_ON_FAIL=1 to enable

MODEL_NAME="${MODEL_NAME:-gpt4omini}"
SCHEMA="default"
MAX_RETRIES=1
CHUNK_SIZE=768
NUM_WORKERS="${NUM_WORKERS:-4}"

# Key/endpoint from gitignored env file in $HOME (never echoed/committed)
source "$HOME/.clines_openai.env"
: "${OPENAIKEY:?OPENAIKEY env var is required (HMS Azure OpenAI API key)}"
: "${OPENAIENDPOINT:=https://azure-ai.hms.edu}"

if [[ ! -e umls_dictionary.txt ]]; then
    ln -sf /n/data1/hsph/biostat/celehs/lab/SHARE/From_Zongxin/language-into-clinical-data/umls_dictionary.txt umls_dictionary.txt
fi
if [[ ! -e umls_body_loc_dictionary.txt ]]; then
    ln -sf /n/data1/hsph/biostat/celehs/lab/SHARE/From_Zongxin/language-into-clinical-data/umls_body_loc_dictionary.txt umls_body_loc_dictionary.txt
fi

source /home/zoy043/miniconda3/etc/profile.d/conda.sh
conda activate sglang

# --- map array id -> (R, slice) ---
SLICES=(4CE coral_breastca coral_pdac)
TID="${SLURM_ARRAY_TASK_ID:?must run as a job array}"
R=$(( TID / 3 + 1 ))          # 1..5
SI=$(( TID % 3 ))             # 0..2
SLICE="${SLICES[$SI]}"

case "${SLICE}" in
    4CE)            NDIR="./data/4CE" ;;
    coral_breastca) NDIR="./data/coral_annotated_breastca" ;;
    coral_pdac)     NDIR="./data/coral_annotated_pdac" ;;
esac
NLIST="runs/EXP-J2/notes_lists/${SLICE}.txt"

MARKER="EXP-J2_run${R}_${SLICE}"
OUTPUT_DIR="runs/EXP-J2/run${R}/${SLICE}"
LOG_DIR="runs/EXP-J2/logs"
ERROR_LOG_FILE="${LOG_DIR}/${MARKER}_errors.log"
REPORT_FILE="${LOG_DIR}/${MARKER}_run_report.jsonl"
RETRY_FILE="${LOG_DIR}/${MARKER}_retry.jsonl"
mkdir -p "${OUTPUT_DIR}" "${LOG_DIR}"

echo "================================================================"
echo "EXP-J2 cell: array_id=${TID} -> RUN ${R} / SLICE ${SLICE}"
echo "  notes_dir=${NDIR}  note_id_list=${NLIST}  output_dir=${OUTPUT_DIR}"
echo "  model=${MODEL_NAME} num_workers=${NUM_WORKERS}  commit=$(git rev-parse --short HEAD 2>/dev/null)"
echo "  jobid=${SLURM_JOB_ID:-local}  node=$(hostname)"
echo "================================================================"

OPENAIKEY="${OPENAIKEY}" OPENAIENDPOINT="${OPENAIENDPOINT}" \
python main.py \
    --notes_dir "${NDIR}" \
    --note_id_list "${NLIST}" \
    --error_log_file "${ERROR_LOG_FILE}" \
    --model_name "${MODEL_NAME}" \
    --max_retries "${MAX_RETRIES}" \
    --schema "${SCHEMA}" \
    --marker "${MARKER}" \
    --output_dir "${OUTPUT_DIR}" \
    --chunk_size "${CHUNK_SIZE}" \
    --num_workers "${NUM_WORKERS}" \
    --run_report_file "${REPORT_FILE}" \
    --retry_list_file "${RETRY_FILE}"

echo "================================================================"
echo "EXP-J2 ${MARKER} COMPLETED"
echo "================================================================"
