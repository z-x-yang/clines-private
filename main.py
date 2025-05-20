import os
import pandas as pd
from tqdm import tqdm
import json
import torch
import numpy as np
from llm_interface.llm_manager import LLMManager
from llm_interface.retrieval.retriever_coordinator import RetrieverCoordinator
# from prompt import PROMPT # Unused import
import re
import demjson3
from check import process_lists_based_on_list1
import traceback
import sqlite3
# from schema import Schema # Unused import
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from data_types import NERData, EntityData, InfoData, DateData
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
    parser.add_argument('--results_file', type=str,
                        default='./results_0927_3.json', help='File to save the results')
    parser.add_argument('--max_retries', type=int, default=1,
                        help='Maximum number of retries for processing each note')
    parser.add_argument('--debug', type=bool, default=False,
                        help='Debug mode')  # Changed to store_true
    parser.add_argument('--notes_dir', type=str,
                        default='./mimic-data-processing/cleaned_mimiciii_notes.csv', help='CSV file or directory containing the notes')
    parser.add_argument('--error_log_file', type=str,
                        help='File to save the error logs')
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

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])

    base_results_file = args.results_file.rsplit('.', 1)[0]
    args.results_file = f"{base_results_file}.json"

    if not args.error_log_file:
        args.error_log_file = f"{base_results_file}_errors.log"

    logger.info("Start initializing model")
    # model instance name matches the one used in PipelineCoordinator
    llm_model = LLMManager(args.model_name, chunk_size=args.chunk_size)
    logger.info("Model initialized")
    logger.info("Start initializing pipeline")

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Instantiate PipelineCoordinator instead of PIPELINE
    pipeline_executor = PipelineCoordinator(llm_model, args.schema, args.output_type,
                                            args.marker, use_gpu=torch.cuda.is_available(),
                                            use_faiss_gpu=args.use_faiss_gpu, output_dir=args.output_dir)
    logger.info("PipelineCoordinator initialized")

    if args.start_index > 0 and os.path.exists(args.results_file):
        try:
            with open(args.results_file, 'r') as f:
                all_results = json.load(f)
            all_results = [result for result in all_results if int(
                result.get('result_index', float('inf'))) < args.start_index]
        except Exception as e:
            logger.error(
                f"Error loading existing results file ({args.results_file}): {e}", exc_info=True)
            all_results = []
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
        all_results = []
        error_log = []

    with open(args.results_file, 'w') as f:
        json.dump(all_results, f, indent=4)

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

    for i in tqdm(range(args.start_index, len(notes)), desc="Processing notes"):
        start_time = time.time()

        note_item = notes[i]
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
        logger.info(
            f"========= Processing note {i+1}/{len(notes)}: {key} ==========")

        output_file = f"{args.output_dir}/{key}_{args.schema}.csv"
        if args.output_type != 'csv':  # Adjust for other output types if necessary
            output_file = f"{args.output_dir}/{key}_{args.schema}.{args.output_type}"

        if os.path.exists(output_file):
            logger.info(
                f"Skipping {key} - output file already exists: {output_file}")
            continue

        # Actual processing call
        if args.debug:
            pipeline_executor(ehr_text, key)  # Call the instance
        else:
            for attempt in range(args.max_retries):
                try:
                    pipeline_executor(ehr_text, key)  # Call the instance
                    break
                except Exception as e:
                    if attempt < args.max_retries - 1:
                        logger.info(
                            f"Attempt {attempt + 1} failed for {key}: {e}. Retrying...")
                    else:
                        traceback_str = traceback.format_exc()
                        error_log.append(
                            {"index": i, "key": key, "error": str(e), "traceback": traceback_str})
                        logger.error(
                            f"Error processing note {key} after {args.max_retries} attempts: {e}")
                        logger.debug(f"Traceback: {traceback_str}")
                        with open(args.error_log_file, 'w') as f:
                            json.dump(error_log, f, indent=4)

        logger.info(f"========= Processing of {key} complete. ==========")
        elapsed_time = time.time() - start_time
        total_processing_time += elapsed_time
        processed_notes_count += 1
        avg_time = total_processing_time / \
            processed_notes_count if processed_notes_count else 0

        if llm_model.note_token_stats:
            latest_note_stats = llm_model.note_token_stats[-1]
            logger.info("\nToken Usage Statistics for the note:")
            logger.info(
                f"  Total prompt tokens: {latest_note_stats['total_prompt_tokens']}")
            logger.info(
                f"  Total completion tokens: {latest_note_stats['total_completion_tokens']}")
            logger.info(f"  Total tokens: {latest_note_stats['total_tokens']}")
            logger.info(
                f"  Number of chunks: {latest_note_stats['num_chunks']}")
            logger.info(
                f"  Average tokens per chunk: {latest_note_stats['avg_tokens_per_chunk']:.2f}")

            # Overall averages might be better calculated across all notes processed in this run
            # This requires accumulating totals outside the loop or adjusting LLMManager
            # For now, displaying based on current llm_model.note_token_stats accumulation
            total_notes_processed_in_run = len(llm_model.note_token_stats)
            if total_notes_processed_in_run > 0:
                avg_prompt_tokens_overall = sum(
                    note['total_prompt_tokens'] for note in llm_model.note_token_stats) / total_notes_processed_in_run
                avg_completion_tokens_overall = sum(
                    note['total_completion_tokens'] for note in llm_model.note_token_stats) / total_notes_processed_in_run
                avg_total_tokens_overall = sum(
                    note['total_tokens'] for note in llm_model.note_token_stats) / total_notes_processed_in_run

                logger.info("\nOverall Token Usage Averages (this run):")
                logger.info(
                    f"  Average prompt tokens per note: {avg_prompt_tokens_overall:.2f}")
                logger.info(
                    f"  Average completion tokens per note: {avg_completion_tokens_overall:.2f}")
                logger.info(
                    f"  Average total tokens per note: {avg_total_tokens_overall:.2f}")

        logger.info(
            f"Time taken for {key}: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
        logger.info(
            f"Average processing time per note (this run): {avg_time:.2f} seconds ({avg_time/60:.2f} minutes)")

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
