# CLINES: Clinical LLM‐based Information Extraction and Structuring Agent

A comprehensive pipeline for processing electronic health records (EHR) using advanced natural language processing techniques including named entity recognition (NER), entity linking, information extraction, and temporal analysis.

## Features

- **Multi-modal NLP Pipeline**: Named entity recognition, relation extraction, and temporal processing
- **Flexible LLM Integration**: Support for OpenAI GPT models and local LLM deployments
- **Modular Architecture**: Clean separation of concerns with specialized processors
- **Scalable Processing**: Parallel processing capabilities for improved performance
- **Multiple Output Formats**: Support for CSV, JSON, and i2b2 formats
- **Entity Linking**: UMLS-based medical entity linking with FAISS indexing
- **Temporal Analysis**: Advanced date and time extraction with normalization

## Prerequisites

- Python 3.10 or higher
- CUDA-capable GPU (recommended for optimal performance)
- Azure OpenAI API access or local LLM setup

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd language-into-clinical-data
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**For CPU-only environments**, modify `requirements.txt` to use `faiss-cpu` instead of `faiss-gpu`:
```bash
sed -i 's/faiss-gpu/faiss-cpu/g' requirements.txt
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
export OPENAIKEY="your_azure_openai_api_key"
export OPENAIENDPOINT="your_azure_openai_endpoint"
```

### 5. Download Required Data Files

Place the following files in the project root directory:
- `umls_dictionary.txt`: UMLS dictionary file
- `umls_body_loc_dictionary.txt`: UMLS body location dictionary file

## Project Structure

```
language-into-clinical-data/
├── main.py                          # Main application entry point
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── prompt.py                        # Prompt template manager
├── run_test.sh                      # Test execution script
├── run_inference.sh                 # Inference execution script
├── core/                            # Core functionality modules
│   ├── __init__.py
│   ├── config_manager.py            # Configuration management utilities
│   ├── data_types.py                # Data type definitions
│   ├── schema.py                    # Output schema processors
│   └── utils.py                     # Utility functions
├── ehr_processing_pipeline/         # EHR processing modules
│   ├── __init__.py
│   ├── pipeline_coordinator.py      # Main pipeline orchestrator
│   ├── ner_processor.py             # Named entity recognition
│   ├── entity_processor.py          # Entity processing and linking
│   ├── info_processor.py            # Information extraction
│   ├── date_processor.py            # Date and temporal processing
│   └── processing_utils.py          # Processing utilities
├── llm_interface/                   # LLM integration layer
│   ├── __init__.py
│   ├── llm_manager.py               # LLM management
│   ├── providers/                   # LLM provider implementations
│   │   ├── openai_provider.py       # OpenAI/Azure OpenAI
│   │   ├── local_llm_provider.py    # Local LLM support
│   │   └── huggingface_provider.py  # Hugging Face models
│   └── retrieval/                   # Information retrieval
│       ├── retriever_coordinator.py # Retrieval coordination
│       ├── index_service.py         # Indexing services
│       └── embedding_service.py     # Embedding services
├── scripts/                         # Utility scripts
│   ├── convert_default_to_i2b2.py   # Format conversion
│   ├── eval_predictions.py          # Evaluation tools
│   └── ...                         # Other processing scripts
├── prompt_templates/                # Prompt template files
├── data/                            # Input data directory
├── outputs/                         # Output files directory
├── logs/                            # Log files directory
└── cache/                           # Cache directory
```

## Quick Start

### Basic Usage

```bash
# Process EHR files with default settings
python main.py --notes_dir data/your_notes/ --output_dir outputs/

# Use specific model and schema
python main.py \
    --model_name gpt4o \
    --notes_dir data/your_notes/ \
    --output_dir outputs/ \
    --schema i2b2 \
    --use_faiss_gpu
```

### Test Script

```bash
# Run test with default settings
./run_test.sh

# Run test with environment variables
TEST_MODEL=gpt4o TEST_SCHEMA=i2b2 ./run_test.sh
```

## Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--model_name` | str | llama-3-405b | LLM model to use |
| `--notes_dir` | str | - | Directory containing EHR notes |
| `--output_dir` | str | outputs | Output directory |
| `--schema` | str | default | Output schema (default/i2b2) |
| `--output_type` | str | csv | Output format (csv/json/sqlite) |
| `--chunk_size` | int | 768 | Text chunking size |
| `--max_retries` | int | 1 | Maximum retry attempts |
| `--debug` | bool | false | Enable debug mode |
| `--use_faiss_gpu` | flag | - | Use GPU for FAISS indexing |
| `--marker` | str | Test | Marker for output files |
| `--start_index` | int | 0 | Starting index for processing |
| `--error_log_file` | str | error_log.log | Error log file path |

## Input Data Formats

### Directory of Text Files
```
data/
├── note_001.txt
├── note_002.txt
└── ...
```

### CSV Format
CSV file with columns:
- `note_id`: Unique identifier
- `text`: EHR note content

## Output Formats

### Default Schema (CSV)
Comprehensive output with all extracted information including entities, relationships, temporal data, and metadata.

### i2b2 Schema (CSV)  
Clinical NLP challenge compatible format for evaluation and comparison.

### JSON Format
Structured JSON output for programmatic access and integration.

## Model Support

### Providers and Models

- Azure (AAD bearer token) provider
  - `--model_name "azure:gpt4o"` → engine "gpt-4o"
  - `--model_name "azure:gpt4omini"` → engine "xx"
  - Auth: DefaultAzureCredential chain (Azure CLI, environment variables, or Managed Identity)
  - Endpoint is fixed in the provider to your institutional Azure OpenAI resource

- Azure (API key) provider
  - `--model_name gpt4o` → engine "gpt-4o"
  - `--model_name gpt4omini` → engine "gpt-4o-mini"
  - `--model_name o3mini` → engine "o3-mini" (reasoning)
  - Requires env vars: `OPENAIKEY`, `OPENAIENDPOINT`

- Local LLM provider (OpenAI-compatible server)
  - `--model_name llama` → base_url `http://127.0.0.1:30000/v1`, model `default`
  - `--model_name llama-3-405b` → same as above (local backend)
  - `--model_name deepseek` → same as above (local reasoning model)

- HuggingFace/Custom host provider (OpenAI-compatible service)
  - `--model_name mistral`
  - Requires env var: `MODELHOST` (e.g., `http://your-host:port/v1`)

### Reasoning vs Non-Reasoning

- Reasoning models: `o3mini` (o3-mini), `deepseek`
- Non-reasoning: `gpt4o` (gpt-4o), `gpt4omini` (gpt-4o-mini or "xx" in AAD provider), `llama-3-405b`,

### How to Invoke

- Azure AAD (recommended for institutional environments):
```bash
# Option 1: Azure CLI
az login
python main.py \
  --model_name "azure:gpt4o" \
  --notes_dir data/your_notes/ \
  --output_dir outputs/ \
  --schema i2b2

# Option 2: Service principal (environment variables)
export AZURE_TENANT_ID="<tenant>"
export AZURE_CLIENT_ID="<appId>"
export AZURE_CLIENT_SECRET="<secret>"
python main.py --model_name "azure:gpt4o" --notes_dir data/ --output_dir outputs/
```

- Azure API Key (OPENAIKEY/OPENAIENDPOINT):
```bash
export OPENAIKEY="<api_key>"
export OPENAIENDPOINT="https://<your-azure-openai-endpoint>"
python main.py --model_name gpt4o --notes_dir data/ --output_dir outputs/
python main.py --model_name o3mini --notes_dir data/ --output_dir outputs/
```

- Local LLM (OpenAI-compatible service, default http://127.0.0.1:30000/v1):
```bash
python main.py --model_name llama --notes_dir data/ --output_dir outputs/
python main.py --model_name deepseek --notes_dir data/ --output_dir outputs/
```

- HuggingFace/Custom service (set MODELHOST):
```bash
export MODELHOST="http://your-host:port/v1"
python main.py --model_name mistral --notes_dir data/ --output_dir outputs/
```

## Performance Optimization

### GPU Acceleration
```bash
# Enable GPU for FAISS indexing
python main.py --use_faiss_gpu --notes_dir data/

# Check GPU memory usage
nvidia-smi
```

### Parallel Processing
The pipeline automatically uses parallel processing for:
- Entity relationship extraction
- Information extraction  
- Date processing

### Memory Management
```bash
# Reduce chunk size for memory-constrained environments
python main.py --chunk_size 512 --notes_dir data/

# Monitor memory usage
htop
```

## Advanced Usage

### Custom Processing Parameters

```bash
# High-throughput processing with larger chunks
python main.py \
    --model_name gpt4o \
    --chunk_size 1024 \
    --use_faiss_gpu \
    --notes_dir data/large_dataset/ \
    --output_dir outputs/high_throughput/

# Debug mode with detailed logging
python main.py \
    --debug true \
    --model_name gpt4o \
    --notes_dir data/test/ \
    --max_retries 3
```

### Batch Processing

```bash
# Process multiple datasets
for dataset in data/*/; do
    python main.py \
        --notes_dir "$dataset" \
        --output_dir "outputs/$(basename $dataset)" \
        --marker "$(basename $dataset)"
done
```

## Development

### Running Tests
```bash
# Run integration tests
./run_test.sh

# Test specific components
python -c "from core.data_types import NERData; print('✓ Core imports work')"
python -c "from ehr_processing_pipeline.pipeline_coordinator import PipelineCoordinator; print('✓ Pipeline imports work')"
```

### Code Quality
```bash
# Check imports and basic syntax
python -m py_compile main.py

# Run with minimal data for testing
python main.py --notes_dir data/test/ --debug true
```

### Adding New Models
1. Create provider in `llm_interface/providers/`
2. Update model name mapping in the provider
3. Test with sample data

## Troubleshooting

### Common Issues

#### 1. GPU Memory Issues
```bash
# Solution: Reduce chunk size
python main.py --chunk_size 256

# Solution: Disable GPU for FAISS
python main.py  # (without --use_faiss_gpu)
```

#### 2. API Rate Limits
```bash
# Solution: Increase retry attempts
python main.py --max_retries 5
```

#### 3. Import Errors
```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version
python --version  # Should be 3.10+
```

#### 4. Missing Data Files
```bash
# Check required files exist
ls -la umls_dictionary.txt umls_body_loc_dictionary.txt

# Verify file permissions
file umls_dictionary.txt
```

### Debug Mode
```bash
# Enable verbose logging
python main.py --debug true --notes_dir data/
```

### Log Analysis
```bash
# View recent logs
ls -la logs/

# Search for errors in console output
python main.py --notes_dir data/ 2>&1 | grep -i error
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
