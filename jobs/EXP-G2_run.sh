#!/bin/bash
#SBATCH --job-name=EXP-G2_ablation
#SBATCH --time=08:00:00
#SBATCH --mem=96G
#SBATCH -c 8
#SBATCH -p short
#SBATCH --output=runs/EXP-G2/logs/slurm-%j.out
#SBATCH --error=runs/EXP-G2/logs/slurm-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=zongxin_yang@hms.harvard.edu

# EXP-G2 = EXP-G ablation grid re-run with MODEL_NAME=gpt4omini
# (gpt-4o-mini-0718 deployment). Sister experiment to EXP-G (gpt-4o-1120),
# branched from EXP-G commit 69d0a52 (which includes the result_aggregation
# missing-CODE fix). Tests whether the CLINES architecture's per-module
# contribution (the ablation ΔF1 pattern) generalizes to a cheaper model.
#
# Env vars (set from caller):
#   ABLATION   = full | sapbert_off | semchunk_off | date_off | step4_off
#   DATASET    = 4CE | coral_pdac | coral_breastca
#   MODEL_NAME = gpt4omini (default here; → gpt-4o-mini-0718 via n2n_dict)
#
# Same 2-notes-per-dataset matched slice as EXP-G. CPU `short` partition
# (SapBERT auto-CPU via use_gpu AND cuda.is_available(); 17.4GB embed cache
# at ./cache makes embed_dictionary a cache hit). 8h walltime because
# coral_breastca cells ran 3h+ for gpt-4o; gpt-4o-mini retry behavior on
# the cheaper model is unknown so the extra margin avoids a TIMEOUT round.
#
# Compliance: §7 HOLD_ON_FAIL sourced (opt-in via env); fail-fast
# (set -euo pipefail); logs under runs/EXP-G2/logs per §10.

set -euo pipefail

if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
    cd "${SLURM_SUBMIT_DIR}"
fi
if [[ ! -d data || ! -d jobs ]]; then
    echo "ERROR: EXP-G2_run.sh must run from project root (need data/ + jobs/). cwd=$(pwd)" >&2
    exit 4
fi

source scripts/slurm_failure_hold.sh

: "${ABLATION:?ABLATION env var required (full|sapbert_off|semchunk_off|date_off|step4_off)}"
: "${DATASET:?DATASET env var required (4CE|coral_pdac|coral_breastca)}"
MODEL_NAME="${MODEL_NAME:-gpt4omini}"
SCHEMA="default"
MAX_RETRIES=1
CHUNK_SIZE=768

: "${OPENAIKEY:?OPENAIKEY env var is required (HMS Azure OpenAI API key)}"
: "${OPENAIENDPOINT:=https://azure-ai.hms.edu}"

# --- map DATASET → notes_dir + note_id_list (same matched slice as EXP-G) ---
case "${DATASET}" in
    4CE)
        NOTES_DIR="./data/4CE"
        NOTE_ID_LIST="runs/EXP-G2/notes_lists/4CE.txt"
        ;;
    coral_pdac)
        NOTES_DIR="./data/coral_annotated_pdac"
        NOTE_ID_LIST="runs/EXP-G2/notes_lists/coral_pdac.txt"
        ;;
    coral_breastca)
        NOTES_DIR="./data/coral_annotated_breastca"
        NOTE_ID_LIST="runs/EXP-G2/notes_lists/coral_breastca.txt"
        ;;
    *)
        echo "ERROR: unknown DATASET=${DATASET}" >&2
        exit 2
        ;;
esac

ABLATION_FLAGS=()
case "${ABLATION}" in
    full)            ;;
    sapbert_off)     ABLATION_FLAGS+=(--disable_sapbert) ;;
    semchunk_off)    ABLATION_FLAGS+=(--disable_semchunk) ;;
    date_off)        ABLATION_FLAGS+=(--disable_date) ;;
    step4_off)       ABLATION_FLAGS+=(--disable_step4_reconcile) ;;
    *)
        echo "ERROR: unknown ABLATION=${ABLATION}" >&2
        exit 2
        ;;
esac

MARKER="EXP-G2_${ABLATION}_${DATASET}"
OUTPUT_DIR="runs/EXP-G2/preds/${ABLATION}/${DATASET}"
LOG_DIR="runs/EXP-G2/logs"
ERROR_LOG_FILE="${LOG_DIR}/${MARKER}_errors.log"
REPORT_FILE="${LOG_DIR}/${MARKER}_run_report.jsonl"
RETRY_FILE="${LOG_DIR}/${MARKER}_retry.jsonl"
mkdir -p "${OUTPUT_DIR}" "${LOG_DIR}"

if [[ "${ABLATION}" != "sapbert_off" ]]; then
    if [[ ! -e umls_dictionary.txt ]]; then
        ln -sf /n/data1/hsph/biostat/celehs/lab/SHARE/From_Zongxin/language-into-clinical-data/umls_dictionary.txt umls_dictionary.txt
    fi
    if [[ ! -e umls_body_loc_dictionary.txt ]]; then
        ln -sf /n/data1/hsph/biostat/celehs/lab/SHARE/From_Zongxin/language-into-clinical-data/umls_body_loc_dictionary.txt umls_body_loc_dictionary.txt
    fi
fi

source /home/zoy043/miniconda3/etc/profile.d/conda.sh
conda activate sglang

echo "================================================================"
echo "EXP-G2 ablation: ABLATION=${ABLATION} DATASET=${DATASET} MODEL=${MODEL_NAME}"
echo "  notes_dir=${NOTES_DIR}  note_id_list=${NOTE_ID_LIST}"
echo "  output_dir=${OUTPUT_DIR}"
echo "  flags: ${ABLATION_FLAGS[*]:-<none = full pipeline>}"
echo "  jobid=${SLURM_JOB_ID:-local}  node=$(hostname)"
echo "================================================================"

OPENAIKEY="${OPENAIKEY}" OPENAIENDPOINT="${OPENAIENDPOINT}" \
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
echo "EXP-G2 ${MARKER} COMPLETED"
echo "================================================================"
