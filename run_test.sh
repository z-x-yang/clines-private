# Other settings
SCHEMA="i2b2"

# Model settings
MODEL_NAME="gpt4o"
MAX_RETRIES=1

OPENAIKEY="***REVOKED_OLD_AZURE_KEY***"
OPENAIENDPOINT="https://azure-ai-dev.hms.edu"

# Add timestamp variable at the beginning
TIMESTAMP=$(date +"%Y%m%d_%H%M")
# Marker settings
MARKER="Test"
NOTES_DIR="data/test2/"
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"
OUTPUT_DIR="./test_outputs/${MODEL_NAME}_${TIMESTAMP}_${MARKER}"
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