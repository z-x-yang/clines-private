import os
import pandas as pd
from tqdm import tqdm
import json
import torch
import numpy as np
from llm_interface.llm_manager import LLMManager
# from prompt import PROMPT # Unused import
import re
import demjson3
from core.utils import process_lists_based_on_list1
import traceback
import sqlite3
# from schema import Schema # Unused import
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from core.data_types import NERData, EntityData, InfoData, DateData
import time
import logging
import pprint

# Import the new PipelineCoordinator
from ehr_processing_pipeline.pipeline_coordinator import PipelineCoordinator

logger = logging.getLogger(__name__)


def convert_to_serializable(obj):
    """
    Convert numpy float32 to Python float for JSON serialization.

    Args:
        obj: Object to be serialized.

    Returns:
        float: Serializable float value.

    Raises:
        TypeError: If the object is not JSON serializable.
    """
    if isinstance(obj, np.float32):
        return float(obj)
    raise TypeError(
        f"Object of type {obj.__class__.__name__} is not JSON serializable")


if __name__ == '__main__':
    import argparse
    # json, pandas, tqdm, torch, traceback, datetime are already imported above

    parser = argparse.ArgumentParser(description='Process some EHR notes.')
    parser.add_argument('--model_name', type=str,
                        default='llama-3-405b', help='Name of the model to use')
    parser.add_argument('--max_retries', type=int, default=1,
                        help='Maximum number of retries for processing each note')
    parser.add_argument('--debug', type=bool, default=False,
                        help='Debug mode')  # Changed to store_true
    parser.add_argument('--notes_dir', type=str,
                        default='./mimic-data-processing/cleaned_mimiciii_notes.csv', help='CSV file or directory containing the notes')
    parser.add_argument('--error_log_file', type=str,
                        default='error_log.log', help='File to save the error logs')
    parser.add_argument('--start_index', type=int, default=0,
                        help='Index to start processing from')
    parser.add_argument('--schema', type=str, default="default", help='schema')
    parser.add_argument('--marker', type=str, default="Test",
                        help='markerfortheoutput')
    parser.add_argument('--output_type', type=str, default="csv",
                        help='output type')
    parser.add_argument('--output_dir', type=str, default="outputs",
                        help='Output directory for schema outputs')
    parser.add_argument('--chunk_size', type=int, default=768,
                        help='Chunk size for the model')
    parser.add_argument('--use_faiss_gpu', action='store_true',
                        help='Use GPU for FAISS')
    parser.add_argument('--chunk_max_retries', type=int, default=2,
                        help='Maximum retries for a single chunk before skipping it')
    parser.add_argument('--chunk_retry_delay', type=float, default=0.5,
                        help='Delay in seconds between chunk retry attempts')
    parser.add_argument('--num_workers', type=int, default=2,
                        help='Number of parallel workers for processing notes (>=1)')
    parser.add_argument('--run_report_file', type=str, default='run_report.jsonl',
                        help='Path to JSONL run report file')
    parser.add_argument('--retry_list_file', type=str, default='retry_list.jsonl',
                        help='Path to JSONL retry list file for failed/partial notes')
    parser.add_argument('--retriever_server', type=str, default=None,
                        help="Use remote retrieval service (host:port) instead of local RetrieverCoordinator")
    parser.add_argument('--retriever_authkey', type=str, default='retriever',
                        help="Auth key for remote retrieval server")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])

    logger.info("Start initializing model")
    # model instance name matches the one used in PipelineCoordinator
    llm_model = LLMManager(args.model_name, chunk_size=args.chunk_size)
    logger.info("Model initialized")
    logger.info("Start initializing pipeline")

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Instantiate PipelineCoordinator instead of PIPELINE
    # Initialize shared retriever once (local or remote)
    if args.retriever_server:
        from llm_interface.retrieval.remote_retriever import RemoteRetrieverProxy
        shared_retriever = RemoteRetrieverProxy(args.retriever_server, args.retriever_authkey)
        logger.info(f"Using remote retriever at {args.retriever_server}")
    else:
        from llm_interface.retrieval.retriever_coordinator import RetrieverCoordinator
        shared_retriever = RetrieverCoordinator('cambridgeltl/SapBERT-from-PubMedBERT-fulltext',
                                                use_gpu=torch.cuda.is_available(),
                                                use_faiss_gpu=args.use_faiss_gpu)
        shared_retriever.load_dictionary_all('./umls_dictionary.txt')
        shared_retriever.load_dictionary_bodyloc('./umls_body_loc_dictionary.txt')
        shared_retriever.embed_dictionary(32768)
        shared_retriever.faiss_setup()

    # Helper to append a JSON line thread-safely
    import threading, json as _json
    write_lock = threading.Lock()
    def append_jsonl(path, obj):
        line = _json.dumps(obj, ensure_ascii=False)
        with write_lock:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
    logger.info("PipelineCoordinator initialized")

    if args.start_index > 0 and os.path.exists(args.error_log_file):
        try:
            with open(args.error_log_file, 'r') as f:
                error_log = json.load(f)
            error_log = [error for error in error_log if int(
                error.get('result_index', float('inf'))) < args.start_index]
        except Exception as e:
            logger.error(
                f"Error loading existing error log file ({args.error_log_file}): {e}", exc_info=True)
            error_log = []
    else:
        error_log = []

    with open(args.error_log_file, 'w') as f:
        json.dump(error_log, f, indent=4)

    # Adapt notes loading based on whether notes_dir is a CSV or a directory of .txt files
    notes = []
    if os.path.isdir(args.notes_dir):
        notes = [item for item in os.listdir(
            args.notes_dir) if item.endswith('.txt')]
        notes_source_type = 'dir'
    elif os.path.isfile(args.notes_dir) and args.notes_dir.endswith('.csv'):
        try:
            notes_df = pd.read_csv(args.notes_dir)
            # Assuming the CSV has columns like 'note_id' and 'text'
            # You might need to adjust column names based on your CSV structure
            if 'note_id' in notes_df.columns and 'text' in notes_df.columns:
                notes = notes_df.apply(lambda row: {'id': str(
                    row['note_id']), 'text': row['text']}, axis=1).tolist()
                notes_source_type = 'csv'
            else:
                logger.error(
                    "CSV file must contain 'note_id' and 'text' columns.")
                exit(1)
        except Exception as e:
            logger.error(
                f"Error reading or processing CSV file {args.notes_dir}: {e}")
            exit(1)
    else:
        logger.error(
            f"notes_dir path {args.notes_dir} is not a valid directory or .csv file.")
        exit(1)

    total_processing_time = 0
    processed_notes_count = 0

    # Prepare worker for parallel execution
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def process_one_note(idx_and_item):
        i, note_item = idx_and_item
        start_time = time.time()
        key_prefix = args.marker
        ehr_text = ""
        note_id_for_key = ""

        if notes_source_type == 'dir':
            note_filename = note_item
            note_id_for_key = note_filename.rstrip('.txt')
            try:
                with open(os.path.join(args.notes_dir, note_filename), 'r', encoding='utf-8') as f:
                    ehr_text = f.read()
            except UnicodeDecodeError:
                with open(os.path.join(args.notes_dir, note_filename), 'r', encoding='latin-1') as f:
                    ehr_text = f.read()
        elif notes_source_type == 'csv':
            note_id_for_key = note_item['id']
            ehr_text = note_item['text']

        key = f"{key_prefix}_{note_id_for_key}"
        logger.info(f"========= Processing note {i+1}/{len(notes)}: {key} ==========")

        # Skip if output exists
        output_file = f"{args.output_dir}/{key}_{args.schema}.csv"
        if args.output_type != 'csv':
            output_file = f"{args.output_dir}/{key}_{args.schema}.{args.output_type}"
        if os.path.exists(output_file):
            logger.info(f"Skipping {key} - output file already exists: {output_file}")
            return {'note_key': key, 'skipped': True}

        # Create per-note LLMManager and Coordinator (inject shared retriever)
        local_llm = LLMManager(args.model_name, chunk_size=args.chunk_size)
        coord = PipelineCoordinator(local_llm, args.schema, args.output_type,
                                    args.marker, use_gpu=torch.cuda.is_available(),
                                    use_faiss_gpu=args.use_faiss_gpu, output_dir=args.output_dir,
                                    chunk_max_retries=args.chunk_max_retries,
                                    chunk_retry_delay=args.chunk_retry_delay,
                                    shared_retriever=shared_retriever)

        report = None
        for attempt in range(args.max_retries):
            try:
                report = coord(ehr_text, key)  # returns report dict
                break
            except Exception as e:
                if attempt < args.max_retries - 1:
                    logger.info(f"Attempt {attempt + 1} failed for {key}: {e}. Retrying...")
                    continue
                else:
                    traceback_str = traceback.format_exc()
                    error_log.append({"index": i, "key": key, "error": str(e), "traceback": traceback_str})
                    logger.error(f"Error processing note {key} after {args.max_retries} attempts: {e}")
                    logger.debug(f"Traceback: {traceback_str}")
        
        # Append to run report
        if report is None:
            report = {'note_key': key, 'overall_status': 'failed', 'errors': ['unhandled exception'], 'chunk_stats': [], 'aggregation_success': False}
        append_jsonl(args.run_report_file, report)

        # Append retry list for partial/failed
        if report.get('overall_status') in ['failed', 'partial']:
            reason = []
            if any(not cs.get('success', False) for cs in report.get('chunk_stats', [])):
                skipped = sum(1 for cs in report['chunk_stats'] if not cs.get('success', False))
                reason.append(f"chunks_skipped={skipped}")
            if not report.get('aggregation_success', True):
                reason.append('aggregation_failed')
            if report.get('errors'):
                reason.append('errors_present')
            append_jsonl(args.retry_list_file, {'note_key': key, 'reason': ','.join(reason) or 'unknown', 'attempts': args.max_retries, 'last_error': (report.get('errors') or [None])[-1]})

        logger.info(f"========= Processing of {key} complete. ==========")
        elapsed_time = time.time() - start_time
        return {'note_key': key, 'skipped': False, 'duration_sec': elapsed_time}

    # Constrain workers to at least 1 (no upper cap enforced here)
    workers = max(1, int(args.num_workers))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_one_note, (i, note)) for i, note in enumerate(notes[args.start_index:])]
        for fut in as_completed(futures):
            try:
                _ = fut.result()
            except Exception as e:
                logger.error(f"Unhandled exception in worker: {e}")

        # Token usage summary from the previous single-threaded flow is omitted in parallel mode
