#!/bin/bash

# Base paths
BASE_DIR="/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data"
SCRIPTS_DIR="${BASE_DIR}/scripts"
OUTPUT_DIR="${BASE_DIR}/outputs"

# Create evaluation results directory
EVAL_DIR="${OUTPUT_DIR}/evaluation_results"
mkdir -p "${EVAL_DIR}"

# Get current timestamp for unique output files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Function to run evaluation
run_evaluation() {
    local model_name=$1
    local prediction_dir=$2
    local groundtruth_dir=$3
    local output_file=$4
    
    echo "Running evaluation for ${model_name}..."
    echo "Prediction directory: ${prediction_dir}"
    echo "Groundtruth directory: ${groundtruth_dir}"
    echo "Output file: ${output_file}"
    
    python "${SCRIPTS_DIR}/eval_predictions.py" \
        --prediction_dir "${prediction_dir}" \
        --groundtruth_dir "${groundtruth_dir}" \
        --columns code assertion_status begin_date end_date value unit \
        --output_file "${output_file}" \
        --model_name "${model_name}"
    
    echo "Evaluation completed for ${model_name}"
    echo "----------------------------------------"
}

# Run evaluations for different models
echo "Starting entity extraction evaluation..."
echo "Timestamp: ${TIMESTAMP}"
echo "=========================================="

# Evaluate GPT-4 output
run_evaluation "gpt4o" \
    "${OUTPUT_DIR}/with_positions" \
    "${OUTPUT_DIR}/reviewed_updated" \
    "${EVAL_DIR}/gpt4_eval_${TIMESTAMP}.json"

# Evaluate DeepSeek output
run_evaluation "deepseek" \
    "${OUTPUT_DIR}/with_positions" \
    "${OUTPUT_DIR}/reviewed_updated" \
    "${EVAL_DIR}/deepseek_eval_${TIMESTAMP}.json"

# Evaluate LLaMA output
run_evaluation "llama" \
    "${OUTPUT_DIR}/with_positions" \
    "${OUTPUT_DIR}/reviewed_updated" \
    "${EVAL_DIR}/llama_eval_${TIMESTAMP}.json"

echo "All evaluations completed!"
echo "Results saved in: ${EVAL_DIR}"
echo "==========================================" 