# Language into Clinical Data

A pipeline for processing electronic health records (EHR) using various NLP tasks including named entity recognition (NER), entity linking, information extraction, and date extraction.

## Prerequisites

- Python 3.8 or higher
- CUDA-capable GPU (recommended for better performance)
- Azure OpenAI API access with GPT-4o model

## Environment Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install required packages:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers tqdm pandas numpy faiss-cpu openai tiktoken semchunk demjson3
```

3. Set up environment variables:
```bash
export OPENAIKEY="your_azure_openai_api_key"
export OPENAIENDPOINT="your_azure_openai_endpoint"
```

## Project Structure

- `main.py`: Main pipeline implementation
- `model.py`: LLM and retriever implementations
- `schema.py`: Output schema definitions
- `data_types.py`: Data type definitions
- `prompt.py`: Prompt templates
- `check.py`: Helper functions
- `scripts/`: Utility scripts for evaluation and processing
- `data/`: Directory for input data
- `outputs/`: Directory for output files
- `logs/`: Directory for log files

## Required Data Files

Place the following files in the project root directory:
- `umls_dictionary.txt`: UMLS dictionary file
- `umls_body_loc_dictionary.txt`: UMLS body location dictionary file

## Running the Pipeline

1. Prepare your input data:
   - Place your EHR text files in the `data/` directory
   - Each file should be a `.txt` file containing the EHR text

2. Run the pipeline:
```bash
# Basic run
python main.py --model_name gpt4o --notes_dir ./data/your_data_directory

# With additional options
python main.py \
    --model_name gpt4o \
    --notes_dir ./data/your_data_directory \
    --output_dir ./outputs \
    --schema default \
    --marker your_marker \
    --use_faiss_gpu \
    --debug true
```

### Command Line Arguments

- `--model_name`: Name of the model to use (default: 'gpt4o')
- `--notes_dir`: Directory containing input EHR text files
- `--output_dir`: Directory for output files (default: 'outputs')
- `--schema`: Output schema type (default: 'default')
- `--marker`: Marker for output files
- `--use_faiss_gpu`: Use GPU for FAISS indexing (recommended if GPU available)
- `--debug`: Enable debug mode
- `--max_retries`: Maximum number of retries for processing each note
- `--chunk_size`: Chunk size for the model (default: 768)

## Output

The pipeline generates the following outputs:
- CSV files in the specified output directory
- Log files in the `logs/` directory
- Error logs for failed processing attempts

## Troubleshooting

1. If you encounter GPU memory issues:
   - Reduce the chunk size using `--chunk_size`
   - Disable FAISS GPU with `--use_faiss_gpu false`

2. If you encounter API rate limits:
   - Increase the `--max_retries` value
   - Add delays between API calls

3. For debugging:
   - Enable debug mode with `--debug true`
   - Check the log files in the `logs/` directory
