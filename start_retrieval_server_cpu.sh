#!/usr/bin/env bash
# Start a shared retrieval server on CPU.

HOST="0.0.0.0"
PORT="50000"
AUTHKEY="retriever"
MODEL_PATH="cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
DICT_ALL="./umls_dictionary.txt"
DICT_BODYLOC="./umls_body_loc_dictionary.txt"
EMBED_BATCH=256

python -m llm_interface.retrieval.retrieval_server \
  --host "${HOST}" \
  --port "${PORT}" \
  --authkey "${AUTHKEY}" \
  --model_path "${MODEL_PATH}" \
  --dictionary_all "${DICT_ALL}" \
  --dictionary_bodyloc "${DICT_BODYLOC}" \
  --embed_batch_size "${EMBED_BATCH}" \
  --cpu
