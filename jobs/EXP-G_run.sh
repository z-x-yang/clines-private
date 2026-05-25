#!/bin/bash
#SBATCH --job-name=EXP-G_ablation
#SBATCH --time=00:30:00
#SBATCH --mem=64G
#SBATCH -c 4
#SBATCH --gres=gpu:1
#SBATCH -p gpu_quad
#SBATCH --output=runs/EXP-G/logs/slurm-%j.out
#SBATCH --error=runs/EXP-G/logs/slurm-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=zongxin_yang@hms.harvard.edu

# EXP-G ablation sbatch — parametrized via env vars (set from caller):
#   ABLATION   = full | sapbert_off | semchunk_off | date_off | step4_off
#   DATASET    = 4CE | coral_pdac | coral_breastca
#   MODEL_NAME = gpt4o (default; matches main paper baseline)
#
# All four ablations + control "full" share this sbatch. Per RESPONSE_PLAN
# §1.5 user decision, each (ablation, dataset) run processes only 5
# representative notes (note_id_list under runs/EXP-G/notes_lists/).
#
# Compliance:
#   - §7 HOLD_ON_FAIL sourced; opt-in via env (set by submitter)
#   - §8 walltime 30min for smoke-size jobs
#   - fail-fast: set -euo pipefail; no silent fallback
#   - logs under runs/EXP-G/logs/slurm-<jobid>.{out,err} per CLAUDE.md §10

set -euo pipefail

# Resolve to the directory from which sbatch was submitted (SLURM sets
# SLURM_SUBMIT_DIR). Fall back to script-relative when running locally.
if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
    cd "${SLURM_SUBMIT_DIR}"
fi
# Sanity check: we should be at project root with data/ + jobs/ both visible.
if [[ ! -d data || ! -d jobs ]]; then
    echo "ERROR: EXP-G_run.sh must run from project root (need data/ + jobs/). cwd=$(pwd)" >&2
    exit 4
fi

# HOLD_ON_FAIL hook (per CLAUDE.md §7) — only installs trap if env var set.
source scripts/slurm_failure_hold.sh

# --- mandatory inputs ---
: "${ABLATION:?ABLATION env var required (full|sapbert_off|semchunk_off|date_off|step4_off)}"
: "${DATASET:?DATASET env var required (4CE|coral_pdac|coral_breastca)}"
MODEL_NAME="${MODEL_NAME:-gpt4o}"
SCHEMA="default"
MAX_RETRIES=1
CHUNK_SIZE=768

# --- HMS Azure OpenAI ---
: "${OPENAIKEY:?OPENAIKEY env var is required (HMS Azure OpenAI API key)}"
: "${OPENAIENDPOINT:=https://azure-ai.hms.edu}"

# --- map DATASET → notes_dir + note_id_list ---
case "${DATASET}" in
    4CE)
        NOTES_DIR="./data/4CE"
        NOTE_ID_LIST="runs/EXP-G/notes_lists/4CE.txt"
        ;;
    coral_pdac)
        NOTES_DIR="./data/coral_annotated_pdac"
        NOTE_ID_LIST="runs/EXP-G/notes_lists/coral_pdac.txt"
        ;;
    coral_breastca)
        NOTES_DIR="./data/coral_annotated_breastca"
        NOTE_ID_LIST="runs/EXP-G/notes_lists/coral_breastca.txt"
        ;;
    *)
        echo "ERROR: unknown DATASET=${DATASET}" >&2
        exit 2
        ;;
esac

# --- map ABLATION → CLI flags ---
ABLATION_FLAGS=()
case "${ABLATION}" in
    full)            ;;  # no extra flags — control
    sapbert_off)     ABLATION_FLAGS+=(--disable_sapbert) ;;
    semchunk_off)    ABLATION_FLAGS+=(--disable_semchunk) ;;
    date_off)        ABLATION_FLAGS+=(--disable_date) ;;
    step4_off)       ABLATION_FLAGS+=(--disable_step4_reconcile) ;;
    *)
        echo "ERROR: unknown ABLATION=${ABLATION}" >&2
        exit 2
        ;;
esac

# --- output paths ---
MARKER="EXP-G_${ABLATION}_${DATASET}"
OUTPUT_DIR="runs/EXP-G/preds/${ABLATION}/${DATASET}"
LOG_DIR="runs/EXP-G/logs"
ERROR_LOG_FILE="${LOG_DIR}/${MARKER}_errors.log"
REPORT_FILE="${LOG_DIR}/${MARKER}_run_report.jsonl"
RETRY_FILE="${LOG_DIR}/${MARKER}_retry.jsonl"
mkdir -p "${OUTPUT_DIR}" "${LOG_DIR}"

# --- umls dictionary symlinks (only needed when SapBERT is ON) ---
if [[ "${ABLATION}" != "sapbert_off" ]]; then
    if [[ ! -e umls_dictionary.txt ]]; then
        ln -sf /n/data1/hsph/biostat/celehs/lab/SHARE/From_Zongxin/language-into-clinical-data/umls_dictionary.txt umls_dictionary.txt
    fi
    if [[ ! -e umls_body_loc_dictionary.txt ]]; then
        ln -sf /n/data1/hsph/biostat/celehs/lab/SHARE/From_Zongxin/language-into-clinical-data/umls_body_loc_dictionary.txt umls_body_loc_dictionary.txt
    fi
fi

# --- activate env ---
source /home/zoy043/miniconda3/etc/profile.d/conda.sh
conda activate sglang

echo "================================================================"
echo "EXP-G ablation: ABLATION=${ABLATION} DATASET=${DATASET} MODEL=${MODEL_NAME}"
echo "  notes_dir=${NOTES_DIR}  note_id_list=${NOTE_ID_LIST}"
echo "  output_dir=${OUTPUT_DIR}"
echo "  flags: ${ABLATION_FLAGS[*]:-<none = full pipeline>}"
echo "  jobid=${SLURM_JOB_ID:-local}  node=$(hostname)"
echo "================================================================"

CUDA_VISIBLE_DEVICES=0 OPENAIKEY="${OPENAIKEY}" OPENAIENDPOINT="${OPENAIENDPOINT}" \
python main.py \
    --notes_dir "${NOTES_DIR}" \
    --note_id_list "${NOTE_ID_LIST}" \
    --error_log_file "${ERROR_LOG_FILE}" \
    --model_name "${MODEL_NAME}" \
    --max_retries "${MAX_RETRIES}" \
    --schema "${SCHEMA}" \
    --marker "${MARKER}" \
    --output_dir "${OUTPUT_DIR}" \
    --chunk_size "${CHUNK_SIZE}" \
    --num_workers 2 \
    --run_report_file "${REPORT_FILE}" \
    --retry_list_file "${RETRY_FILE}" \
    "${ABLATION_FLAGS[@]}"

echo "================================================================"
echo "EXP-G ${MARKER} COMPLETED"
echo "================================================================"
