#!/usr/bin/env bash
# Run main.py and launch a local CPU retrieval service inside this script.

set -euo pipefail

# Schema / model settings
SCHEMA="default"          # or "i2b2"
MODEL_NAME="azure:gpt4omini"
MAX_RETRIES=5
NUM_WORKERS=5             # main.py caps at 5
CHUNK_SIZE=1024

# Marker / paths
TIMESTAMP=$(date +"%Y%m%d_%H%M")
MARKER="DAS_Human_Label_1228"
NOTES_DIR="/PHShome/zy098/Zongxin_yang/Works/DAS-Agent/data/DAS_human_label_251228/notes"
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"
REPORT_FILE="./logs/${MARKER}_report_${TIMESTAMP}.json"
OUTPUT_DIR="./outputs/${MARKER}"
START_IDX=0

# Local retrieval server (CPU) settings
SRV_HOST="127.0.0.1"
SRV_PORT="50000"
SRV_AUTHKEY="retriever"
MODEL_PATH="cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
DICT_ALL="./umls_dictionary.txt"
DICT_BODYLOC="./umls_body_loc_dictionary.txt"
EMBED_BATCH=256
SRV_LOG="./logs/retrieval_server_${TIMESTAMP}.log"

mkdir -p ./logs

# Start retrieval server in background
python -m llm_interface.retrieval.retrieval_server \
  --host "${SRV_HOST}" \
  --port "${SRV_PORT}" \
  --authkey "${SRV_AUTHKEY}" \
  --model_path "${MODEL_PATH}" \
  --dictionary_all "${DICT_ALL}" \
  --dictionary_bodyloc "${DICT_BODYLOC}" \
  --embed_batch_size "${EMBED_BATCH}" \
  --cpu \
  > "${SRV_LOG}" 2>&1 &

SRV_PID=$!
echo "Started CPU retrieval server PID=${SRV_PID} on ${SRV_HOST}:${SRV_PORT}"
trap 'kill ${SRV_PID} 2>/dev/null || true' EXIT

# Run main workflow pointing to the local server
RETRIEVER_SERVER="${SRV_HOST}:${SRV_PORT}" RETRIEVER_AUTHKEY="${SRV_AUTHKEY}" \
CUDA_VISIBLE_DEVICES=0 python main.py \
  --notes_dir "${NOTES_DIR}" \
  --error_log_file "${ERROR_LOG_FILE}" \
  --start_index "${START_IDX}" \
  --model_name "${MODEL_NAME}" \
  --max_retries "${MAX_RETRIES}" \
  --schema "${SCHEMA}" \
  --marker "${MARKER}" \
  --output_dir "${OUTPUT_DIR}" \
  --chunk_size "${CHUNK_SIZE}" \
  --num_workers "${NUM_WORKERS}" \
  --run_report_file "${REPORT_FILE}" \
  --retriever_server "${SRV_HOST}:${SRV_PORT}" \
  --retriever_authkey "${SRV_AUTHKEY}" \
  2>&1 | tee "${LOG_FILE}"
