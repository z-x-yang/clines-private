# Other settings
SCHEMA="default"
# SCHEMA="i2b2"

# Model settings
MODEL_NAME="gpt4o"
MAX_RETRIES=1

# OPENAIKEY / OPENAIENDPOINT must be set in the environment (or a sourced .env
# file that is .gitignored). Earlier hardcoded values removed when the legacy
# https://azure-ai-dev.hms.edu endpoint was deprecated; current HMS endpoint is
# https://azure-ai.hms.edu (key obtained from the HMS SharePoint).
: "${OPENAIKEY:?OPENAIKEY env var is required (HMS Azure OpenAI API key)}"
: "${OPENAIENDPOINT:=https://azure-ai.hms.edu}"

# Add timestamp variable at the beginning
TIMESTAMP=$(date +"%Y%m%d_%H%M")
# Marker settings
MARKER="gene"
# MARKER="test2"
# NOTES_DIR="data/test2/"
NOTES_DIR="/n/data1/hsph/biostat/celehs/lab/huaiyuan/language-into-clinical-data-i2b2/gene_pages"
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"
OUTPUT_DIR="./outputs/${MODEL_NAME}_${MARKER}"
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
    --chunk_size 1024 \
    2>&1 | tee ${LOG_FILE}