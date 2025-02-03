# Other settings
SCHEMA="default"

# Model settings
# MODEL_NAME="llama-3-405b"
# MODEL_NAME="gpt4o"
MODEL_NAME="deepseek"
MAX_RETRIES=1
OPENAIKEY="95611e3e803c4f49b8735f8c899572c5"
OPENAIENDPOINT="https://azure-ai-dev.hms.edu"

# Add timestamp variable at the beginning
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
# Marker settings
MARKER="Test"
NOTES_DIR="/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/Test"
LOG_FILE="./logs/${MARKER}_${TIMESTAMP}.log"
RESULTS_FILE="./results/${MARKER}.json"
ERROR_LOG_FILE="./logs/${MARKER}_errors_${TIMESTAMP}.log"
START_IDX=0

CUDA_VISIBLE_DEVICES=0 OPENAIKEY=${OPENAIKEY} OPENAIENDPOINT=${OPENAIENDPOINT} python main_llama.py \
    --results_file ${RESULTS_FILE} \
    --notes_dir ${NOTES_DIR} \
    --error_log_file ${ERROR_LOG_FILE} \
    --start_index ${START_IDX} \
    --model_name ${MODEL_NAME} \
    --max_retries ${MAX_RETRIES} \
    --schema ${SCHEMA} \
    --marker ${MARKER} \
    2>&1 | tee ${LOG_FILE}