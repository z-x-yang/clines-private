set -euo pipefail

# Other settings
SCHEMA="default"

# Model settings
# MODEL_NAME="llama-3-405b"
# MODEL_NAME="deepseek"
# MODEL_NAME="o3mini"
MODEL_NAME="gpt4o"
MAX_RETRIES=1

# OPENAIKEY / OPENAIENDPOINT must be set in the environment (or a sourced .env file
# that is .gitignored). Old hard-coded values were removed when the legacy
# https://azure-ai-dev.hms.edu endpoint was deprecated. Current endpoint:
#   https://azure-ai.hms.edu  (key obtained from https://hu.sharepoint.com/sites/azureai)
: "${OPENAIKEY:?OPENAIKEY env var is required (HMS Azure OpenAI API key)}"
: "${OPENAIENDPOINT:=https://azure-ai.hms.edu}"

# Add timestamp variable at the beginning
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
# Marker settings
MARKER="huaiyuan_0919"
NOTES_DIR="/home/zoy043/Works/language-into-clinical-data/data/huaiyuan_0919"
mkdir -p ./logs
mkdir -p ./results
mkdir -p ./outputs
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"
OUTPUT_DIR="./outputs/gpt4o_huaiyuan_0919"
START_IDX=0


CUDA_VISIBLE_DEVICES=0 OPENAIKEY=${OPENAIKEY} OPENAIENDPOINT=${OPENAIENDPOINT} python main.py \
    --notes_dir ${NOTES_DIR} \
    --error_log_file ${ERROR_LOG_FILE} \
    --start_index ${START_IDX} \
    --model_name ${MODEL_NAME} \
    --max_retries ${MAX_RETRIES} \
    --schema ${SCHEMA} \
    --marker ${MARKER} \
    --debug true \
    --output_dir ${OUTPUT_DIR} \
    2>&1 | tee ${LOG_FILE}
