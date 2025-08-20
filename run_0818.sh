# Other settings
SCHEMA="default"
# SCHEMA="i2b2"

# Model settings
MODEL_NAME="azure:gpt4o"
MAX_RETRIES=1
NUM_WORKERS=3

# Add timestamp variable at the beginning
TIMESTAMP=$(date +"%Y%m%d_%H%M")
# Marker settings
MARKER="MH_0818"
# MARKER="test2"
# NOTES_DIR="data/test2/"
NOTES_DIR="./data/med_notes11"
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"
REPORT_FILE="./logs/${MARKER}_report_${TIMESTAMP}.json"
OUTPUT_DIR="./outputs/${MARKER}"
START_IDX=0


CUDA_VISIBLE_DEVICES=0 OPENAIKEY=${OPENAIKEY} OPENAIENDPOINT=${OPENAIENDPOINT} python main.py \
    --notes_dir ${NOTES_DIR} \
    --error_log_file ${ERROR_LOG_FILE} \
    --start_index ${START_IDX} \
    --model_name ${MODEL_NAME} \
    --max_retries ${MAX_RETRIES} \
    --schema ${SCHEMA} \
    --marker ${MARKER} \
    --output_dir ${OUTPUT_DIR} \
    --chunk_size 1024 \
    --num_workers ${NUM_WORKERS} \
    --run_report_file ${REPORT_FILE} \
    2>&1 | tee ${LOG_FILE}