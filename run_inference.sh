# Add timestamp variable at the beginning
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Other settings
SCHEMA="default"
MARKER="4CE"

# Data and output paths
NOTES_DIR="/home/zoy043/Works/language-into-clinical-data/data/4CE"
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
RESULTS_FILE="./results/${MARKER}.json"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"

# Model settings
MODEL_NAME="llama-3-405b"
START_IDX=0
MAX_RETRIES=1

CUDA_VISIBLE_DEVICES=7 python main_llama.py \
    --results_file ${RESULTS_FILE} \
    --notes_dir ${NOTES_DIR} \
    --error_log_file ${ERROR_LOG_FILE} \
    --start_index ${START_IDX} \
    --model_name ${MODEL_NAME} \
    --max_retries ${MAX_RETRIES} \
    --schema ${SCHEMA} \
    --marker ${MARKER} \
    2>&1 | tee ${LOG_FILE}

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

MARKER="coral_annotated_breastca"
NOTES_DIR="/home/zoy043/Works/language-into-clinical-data/data/coral_annotated_breastca"
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
RESULTS_FILE="./results/${MARKER}.json"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"
START_IDX=0

CUDA_VISIBLE_DEVICES=7 python main_llama.py \
    --results_file ${RESULTS_FILE} \
    --notes_dir ${NOTES_DIR} \
    --error_log_file ${ERROR_LOG_FILE} \
    --start_index ${START_IDX} \
    --model_name ${MODEL_NAME} \
    --max_retries ${MAX_RETRIES} \
    --schema ${SCHEMA} \
    --marker ${MARKER} \
    2>&1 | tee ${LOG_FILE}

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

MARKER="coral_annotated_pdac"
NOTES_DIR="/home/zoy043/Works/language-into-clinical-data/data/coral_annotated_pdac"
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
RESULTS_FILE="./results/${MARKER}.json"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"
START_IDX=0

CUDA_VISIBLE_DEVICES=7 python main_llama.py \
    --results_file ${RESULTS_FILE} \
    --notes_dir ${NOTES_DIR} \
    --error_log_file ${ERROR_LOG_FILE} \
    --start_index ${START_IDX} \
    --model_name ${MODEL_NAME} \
    --max_retries ${MAX_RETRIES} \
    --schema ${SCHEMA} \
    --marker ${MARKER} \
    2>&1 | tee ${LOG_FILE}