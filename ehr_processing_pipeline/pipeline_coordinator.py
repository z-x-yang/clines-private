import logging
import json
import re
import demjson3
import pprint
import threading
import concurrent.futures
import os
import time
from typing import List, Optional, Tuple, Dict, Any, Union
import torch
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime

from llm_interface.llm_manager import LLMManager
from llm_interface.retrieval.retriever_coordinator import RetrieverCoordinator
from prompt import PromptManager
from core.schema import SchemaProcessor, SchemaName, OutputType
from core.data_types import NERData, EntityData, InfoData, DateData
from core.utils import process_lists_based_on_list1
from .processing_utils import safe_deduplication_input

from .ner_processor import NERProcessor
# Import the new EntityProcessor
from .entity_processor import EntityProcessor
# Import the new InfoProcessor
from .info_processor import InfoProcessor
# Import the new DateProcessor
from .date_processor import DateProcessor


class PipelineCoordinator:
    """
    Orchestrates the EHR processing pipeline, coordinating various NLP tasks.
    """

    def __init__(self, model, schema='i2b2', format_type='csv', marker="", use_gpu=True, use_faiss_gpu=None, output_dir="outputs",
                 chunk_max_retries: int = 2, chunk_retry_delay: float = 0.5,
                 shared_retriever: RetrieverCoordinator | None = None,
                 ablation_flags: dict | None = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model
        self.output_schema = SchemaProcessor(
            schema, format_type, marker, output_dir)

        # EXP-G ablation flags
        flags = ablation_flags or {}
        self.disable_sapbert = bool(flags.get('disable_sapbert', False))
        self.disable_semchunk = bool(flags.get('disable_semchunk', False))
        self.disable_date = bool(flags.get('disable_date', False))
        self.disable_step4_reconcile = bool(flags.get('disable_step4_reconcile', False))
        if any([self.disable_sapbert, self.disable_semchunk, self.disable_date, self.disable_step4_reconcile]):
            self.logger.info(
                f"EXP-G ablation flags active: sapbert={self.disable_sapbert} "
                f"semchunk={self.disable_semchunk} date={self.disable_date} "
                f"step4_reconcile={self.disable_step4_reconcile}")

        if self.disable_sapbert:
            self.logger.info("EXP-G ablation: SapBERT DISABLED; retriever skipped")
            self.retriever = None
        elif shared_retriever is not None:
            self.retriever = shared_retriever
            self.logger.info("Using shared RetrieverCoordinator instance (skipping local initialization)")
        else:
            self.retriever = RetrieverCoordinator(
                'cambridgeltl/SapBERT-from-PubMedBERT-fulltext', use_gpu=use_gpu, use_faiss_gpu=use_faiss_gpu)
            self.retriever.load_dictionary_all('./umls_dictionary.txt')
            self.retriever.load_dictionary_bodyloc(
                './umls_body_loc_dictionary.txt')
            self.retriever.embed_dictionary(32768)
            self.retriever.faiss_setup()

        self.prompt_ner = PromptManager('findentity')
        self.prompt_relate = PromptManager('findrelated')
        self.prompt_clean = PromptManager('recoverentity')
        self.prompt_status = PromptManager('findstatus')
        self.prompt_info = PromptManager('findinfo')
        self.prompt_date_single = PromptManager('finddate_single')
        self.prompt_date_multi = PromptManager('finddate_multi')
        self.prompt_date_range = PromptManager('date_range')
        self.prompt_basic_info = PromptManager('basic_info')
        self.prompt_json_debug = PromptManager('json_debug')
        self.norm_date = PromptManager('norm_date')

        self.ner_processor = NERProcessor(
            self.model, self.prompt_ner, self.prompt_json_debug)
        # Instantiate EntityProcessor, passing the deduplication method from this class
        self.entity_processor = EntityProcessor(
            self.model, self.prompt_relate, self.prompt_clean,
            self.prompt_json_debug, self.retriever, self.deduplication,
            disable_sapbert=self.disable_sapbert,
            disable_step4_reconcile=self.disable_step4_reconcile,
        )
        # Instantiate InfoProcessor, passing the deduplication method from this class
        self.info_processor = InfoProcessor(
            self.model, self.prompt_status, self.prompt_info,
            self.prompt_json_debug, self.retriever, self.deduplication,
            disable_sapbert=self.disable_sapbert,
            disable_step4_reconcile=self.disable_step4_reconcile,
        )
        # Instantiate DateProcessor
        self.date_processor = DateProcessor(
            self.model, self.prompt_basic_info, self.prompt_date_single,
            # norm_date is a PromptManager object
            self.prompt_date_multi, self.norm_date, self.prompt_json_debug,
            self.deduplication,
            disable_step4_reconcile=self.disable_step4_reconcile,
        )

        # Chunk-level retry configuration
        self.chunk_max_retries = chunk_max_retries
        self.chunk_retry_delay = chunk_retry_delay

        self.reinitialize()
        self.logger.info(
            "PipelineCoordinator initialized with retriever, prompts, and processors.")

    def _process_chunk_with_retry(self, chunk_text: str, prev_chunk_text: str | None,
                                   chunk_offset: int, original_ehr: str,
                                   chunk_index: int, total_chunks: int,
                                   chunk_stats: list | None = None) -> None:
        """
        Process a single chunk with bounded retries. Failures are logged and the
        pipeline continues with subsequent chunks. Always finalizes chunk stats once.

        Args:
            chunk_text: Current chunk text
            prev_chunk_text: Previous chunk text or None
            chunk_offset: Offset of current chunk in original document
            original_ehr: The full original EHR text
            chunk_index: 1-based index of current chunk
            total_chunks: Total number of chunks
        """
        attempts = 0
        success = False
        error_messages: list[str] = []
        start_ts = time.time()
        while attempts <= self.chunk_max_retries and not success:
            try:
                if attempts > 0:
                    self.logger.warning(
                        f"Retrying chunk {chunk_index}/{total_chunks} (attempt {attempts}/{self.chunk_max_retries})…")

                # Set original chunk token count before processing
                self.model.set_chunk_original_tokens(chunk_text)
                self.call_single(chunk_text, prev_ehr=prev_chunk_text,
                                  chunk_offset=chunk_offset, original_ehr=original_ehr)
                success = True
            except Exception as e:
                error_messages.append(str(e))
                if attempts < self.chunk_max_retries:
                    self.logger.warning(
                        f"Chunk {chunk_index}/{total_chunks} failed: {e}. Will retry after {self.chunk_retry_delay}s.")
                    time.sleep(self.chunk_retry_delay)
                else:
                    self.logger.error(
                        f"Chunk {chunk_index}/{total_chunks} failed after {self.chunk_max_retries} retries: {e}",
                        exc_info=True)
                attempts += 1
            finally:
                # Ensure we finalize chunk statistics once per attempt cycle only when success
                # We will finalize after loop to ensure exactly-once semantics per chunk
                pass

        # Finalize chunk statistics once per chunk regardless of success
        try:
            self.model.finish_chunk()
        except Exception as e:
            self.logger.error(f"Error finalizing chunk {chunk_index}/{total_chunks}: {e}", exc_info=True)

        # Record per-chunk stats
        if chunk_stats is not None:
            duration_sec = max(0.0, time.time() - start_ts)
            entry = {
                'index': chunk_index,
                'offset': chunk_offset,
                'size_chars': len(chunk_text) if isinstance(chunk_text, str) else 0,
                'attempts': attempts if attempts > 0 else 1,
                'success': bool(success),
                'skipped': (not success),
                'error_messages': error_messages,
                'duration_sec': duration_sec,
            }
            # Attach module stats if success
            if success:
                entry['module_stats'] = {
                    'ner': getattr(self.ner_processor, 'last_run_stats', None),
                    'entity': getattr(self.entity_processor, 'last_run_stats', None),
                    'info': getattr(self.info_processor, 'last_run_stats', None),
                    'date': getattr(self.date_processor, 'last_run_stats', None),
                }
            else:
                entry['module_stats'] = None
            chunk_stats.append(entry)

    def reinitialize(self):
        self.pipeline_result = {
            'ner_result': [], 'clean_results': [], 'info_results': [],
            'status_results': [], 'date_results': [], 'parsed_ner_result': [],
            'parsed_ner_context': [], 'relate_results': [], 'parsed_ner_positions': []
        }
        self.admission_date = None
        self.discharge_date = None

    def parse_result(self, string):
        """
        Parse the JSON result from the model output.

        Args:
            string (str): The raw string output from the model.

        Returns:
            str: Cleaned JSON string.
        """
        results = re.findall('```[^`]+```', string)
        if len(results) == 0:
            return string

        result = results[-1]
        result = result.strip('```').lstrip('json')
        result = result.replace('None', 'null')
        result = result.replace('"null"', 'null')
        result = result.replace('"NA"', 'null')
        result = result.replace('```', '')

        # Remove inline comments
        result = re.sub(r'\s*#.*$', '', result, flags=re.MULTILINE)
        # Remove C-style comments (both single-line and multi-line)
        result = re.sub(r'//.*?$|/\*.*?\*/', '', result,
                        flags=re.MULTILINE | re.DOTALL)
        return result

    def result_aggregation(self, key):
        aggregated_result = []
        num_items = len(self.pipeline_result.get('clean_results', []))
        clean_results_list = self.pipeline_result.get('clean_results', [])
        status_results_list = self.pipeline_result.get('status_results', [])
        info_results_list = self.pipeline_result.get('info_results', [])
        relate_results_list = self.pipeline_result.get('relate_results', [])
        date_results_list = self.pipeline_result.get('date_results', [])
        parsed_ner_result_list = self.pipeline_result.get(
            'parsed_ner_result', [])
        parsed_ner_context_list = self.pipeline_result.get(
            'parsed_ner_context', [])
        parsed_ner_positions_list = self.pipeline_result.get(
            'parsed_ner_positions', [])

        for i in range(num_items):
            tmp = {}
            try:
                tmp = {
                    'term_index': i + 1,
                    'key': key,
                    'admission_date': self.admission_date,
                    'discharge_date': self.discharge_date,
                    'gender': self.pipeline_result.get('gender', None),
                    'death_date': self.pipeline_result.get('death_date', None),
                    'birth_date': self.pipeline_result.get('birth_date', None),
                    'race': self.pipeline_result.get('race', None),
                    'ethnicity': self.pipeline_result.get('ethnicity', None),
                    'zip_code': self.pipeline_result.get('zip_code', None),
                    'mention': parsed_ner_result_list[i] if i < len(parsed_ner_result_list) else None,
                    'context': parsed_ner_context_list[i] if i < len(parsed_ner_context_list) else None,
                    'mention_start_pos': parsed_ner_positions_list[i][0] if i < len(parsed_ner_positions_list) and parsed_ner_positions_list[i] != (-1, -1) else None,
                    'mention_end_pos': parsed_ner_positions_list[i][1] if i < len(parsed_ner_positions_list) and parsed_ner_positions_list[i] != (-1, -1) else None,
                }

                clean_item = clean_results_list[i]
                # EXP-G ablation: step4_off skips entity_linking entirely so
                # clean_item has no 'CODE' key. Other ablations (sapbert_off)
                # still populate CODE with a NORM_OFF placeholder. Outside
                # ablation mode, missing CODE is a real bug — fail fast.
                if self.disable_step4_reconcile:
                    mapped_code_raw = clean_item.get('CODE')
                else:
                    mapped_code_raw = clean_item['CODE']
                if mapped_code_raw:
                    mapped_code = json.loads(mapped_code_raw)
                    tmp['code'] = list(mapped_code.keys())[0]
                    tmp['type'] = mapped_code[tmp['code']][1]
                    tmp['code'] = tmp['code'] + '||' + mapped_code[tmp['code']][0]
                else:
                    tmp['code'] = None
                    tmp['type'] = None

                status_item = status_results_list[i] if i < len(
                    status_results_list) else {}
                tmp['assertion_status'] = status_item.get(
                    'assertion_status', None)

                info_item = info_results_list[i] if i < len(
                    info_results_list) else {}
                tmp['body_location'] = info_item.get('body_location', None)
                body_code_val = info_item.get('body_code', None)
                if body_code_val is not None:
                    mapped_body_code = json.loads(body_code_val)
                    tmp['body_location_code'] = list(
                        mapped_body_code.keys())[0]
                    tmp['body_location_code'] = tmp['body_location_code'] + \
                        '||' + mapped_body_code[tmp['body_location_code']][0]
                else:
                    tmp['body_location_code'] = None
                tmp['value'] = info_item.get('value', None)
                tmp['unit'] = info_item.get('unit', None)
                tmp['infer'] = info_item.get('infer', None)
                tmp['freq'] = info_item.get('freq', None)
                tmp['route'] = info_item.get('route', None)
                tmp['note'] = info_item.get('note', None)
                tmp['other'] = info_item.get('other', None)

                relate_item = relate_results_list[i] if i < len(
                    relate_results_list) else {}
                related_data = relate_item.get('related')
                if isinstance(related_data, dict):
                    tmp['related'] = related_data
                elif isinstance(related_data, str):
                    try:
                        tmp['related'] = json.loads(
                            related_data if related_data.strip() else '{}')
                    except json.JSONDecodeError:
                        self.logger.warning(
                            f"Could not decode 'related' JSON string: {related_data}. Using empty dict.")
                        tmp['related'] = {}
                else:
                    tmp['related'] = {}

                date_item = date_results_list[i] if i < len(
                    date_results_list) else {}
                tmp['begin_date'] = date_item.get('date', [None, None])[0]
                tmp['end_date'] = date_item.get('date', [None, None])[1]
                if 'inferred' in date_item:
                    tmp['begin_date_inferred'] = date_item['inferred'][0]
                    tmp['end_date_inferred'] = date_item['inferred'][1]

                aggregated_result.append(tmp)
            except IndexError as e:
                self.logger.error(
                    f"Index error during result aggregation for key {key}, item {i}: {e}", exc_info=True)
                # Append a partial record or skip, depending on desired error handling
                # For now, appending what we have, which might be just the initial tmp fields
                aggregated_result.append(tmp)  # tmp might be partially filled
            except json.JSONDecodeError as e:
                self.logger.error(
                    f"JSON decode error for key {key}, item {i}: {e} - Data: {clean_item.get('CODE', '') if 'clean_item' in locals() else 'N/A'}", exc_info=True)
                aggregated_result.append(tmp)  # Append partial data
            except Exception as e:
                self.logger.error(
                    f"Unexpected error during result aggregation for key {key}, item {i}: {e}", exc_info=True)
                aggregated_result.append(tmp)  # Append partial data

        self.output_schema(aggregated_result, key)

    def deduplication(self, list_of_dict: Union[List[Dict], Dict, Any], key: str, parsed_ner_tags: Optional[List[str]] = None) -> List[Dict]:
        """
        Deduplication method with type-safe checks and defensive programming
        
        Args:
            list_of_dict: Input data (expected to be list of dicts, but will auto-handle other types)
            key: Key name for deduplication
            parsed_ner_tags: Optional NER tags list for filtering
            
        Returns:
            Deduplicated list of dictionaries
        """
        # Use safe input validation and conversion
        safe_input = safe_deduplication_input(list_of_dict, self.logger)
        
        if not safe_input:
            self.logger.warning("Empty or invalid input for deduplication, returning empty list")
            return []
        
        # Execute deduplication logic
        unique_list = []
        seen = set()
        
        try:
            for d in safe_input[::-1]:
                if not isinstance(d, dict):
                    self.logger.warning(f"Skipping non-dict item in deduplication: {type(d)}")
                    continue
                    
                key_value = str(d.get(key, ''))
                if parsed_ner_tags is not None and key_value not in map(str, parsed_ner_tags):
                    continue
                if key_value not in seen:
                    unique_list.append(d)
                    seen.add(key_value)
            
            result = unique_list[::-1]
            self.logger.debug(f"Deduplication completed: {len(safe_input)} -> {len(result)} items")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in deduplication process: {e}", exc_info=True)
            # Return safe result even if error occurs
            return safe_input if isinstance(safe_input, list) else []

    def filter_parsed_results(self, parsed_ner_results, parsed_ner_context, parsed_ner_tags, clean_results, parsed_ner_positions=None):
        clean_result_tags = [item['TAG'] for item in clean_results]
        filtered_indices = [i for i, tag in enumerate(
            parsed_ner_tags) if tag in clean_result_tags]
        filtered_ner_results = [parsed_ner_results[i]
                                for i in filtered_indices]
        filtered_ner_context = [parsed_ner_context[i]
                                for i in filtered_indices]
        filtered_ner_positions = [parsed_ner_positions[i]
                                  for i in filtered_indices] if parsed_ner_positions else []
        return filtered_ner_results, filtered_ner_context, filtered_ner_positions

    def _aggregate_results(self, ner_data: NERData, entity_data: EntityData,
                           info_data: InfoData, date_data: DateData) -> None:
        self.pipeline_result['clean_results'] += entity_data.clean_results
        # EXP-G ablation (d): when Step 4 reconciliation is OFF, skip the
        # tag-based alignment / default-filling. Just pad each parallel list
        # to the clean_results length so downstream result_aggregation can
        # zip them positionally — duplicate / unaligned rows produced by the
        # LLM are preserved as-is (this is what reviewers want to see).
        if self.disable_step4_reconcile:
            self.logger.info("EXP-G ablation: Step 4 reconcile DISABLED in _aggregate_results; using positional concat")
            n = len(entity_data.clean_results)
            def _pad(lst, default):
                lst = list(lst) if lst else []
                if len(lst) < n:
                    lst = lst + [dict(default) for _ in range(n - len(lst))]
                else:
                    lst = lst[:n]
                return lst
            info_results = _pad(info_data.info_results, {
                "tag": None, "body_location": None, "value": None, "unit": None,
                "infer": None, "note": None, "freq": None, "route": None, "other": None,
            })
            status_results = _pad(info_data.status_results, {"tag": None, "assertion_status": None})
            date_results = _pad(date_data.date_results, {"tag": None, "date": [None, None], "inferred": [None, None]})
            relate_results = _pad(entity_data.relate_results, {"tag": None, "related": {}})
        else:
            info_results, status_results, date_results, relate_results = process_lists_based_on_list1(
                entity_data.clean_results, info_data.info_results,
                info_data.status_results, date_data.date_results, entity_data.relate_results
            )
        self.pipeline_result['info_results'] += info_results
        self.pipeline_result['status_results'] += status_results
        self.pipeline_result['date_results'] += date_results

        offset = len(self.pipeline_result.get('relate_results', []))
        for result in relate_results:
            if result.get('related') and isinstance(result['related'], dict):
                new_related = {}
                for tag, rel_type in result['related'].items():
                    try:
                        new_tag = str(int(tag) + offset)
                        new_related[new_tag] = rel_type
                    except ValueError:
                        self.logger.error(
                            f"Error converting related tag: {tag} to int with offset {offset}", exc_info=True)
                        continue
                result['related'] = new_related
        if 'relate_results' not in self.pipeline_result:
            self.pipeline_result['relate_results'] = []
        self.pipeline_result['relate_results'] += relate_results

        filtered_ner_results, filtered_ner_context, filtered_ner_positions = self.filter_parsed_results(
            ner_data.parsed_results, ner_data.parsed_context,
            ner_data.parsed_tags, entity_data.clean_results, ner_data.parsed_positions
        )
        self.pipeline_result['parsed_ner_result'] += filtered_ner_results
        self.pipeline_result['parsed_ner_context'] += filtered_ner_context
        self.pipeline_result['parsed_ner_positions'] += filtered_ner_positions

    def call_single(self, ehr: str, prev_ehr: str | None = None, chunk_offset: int = 0, original_ehr: str = None) -> None:
        self.logger.info("=== Starting Single EHR Processing ===")
        self.logger.info(f"Input EHR length: {len(ehr)} characters")
        self.logger.info(f"Previous EHR provided: {prev_ehr is not None}")
        self.logger.info(f"Chunk offset in original document: {chunk_offset}")

        # Pass the original EHR text and chunk offset to NER processor
        ner_data = self.ner_processor.process_ner(
            ehr, original_ehr or ehr, chunk_offset)
        self.logger.info(f"Found {len(ner_data.parsed_tags)} entities")
        if len(ner_data.parsed_tags) == 0:
            self.logger.info("No entities found - skipping further processing")
            return

        entity_data, info_data, date_data = self._process_parallel_with_executor(
            ehr, ner_data, prev_ehr)

        self.logger.info(
            f"Processed {len(entity_data.clean_results)} cleaned entities")
        # Error if entity_data is None
        self.logger.info(
            f"Found {len(entity_data.relate_results)} entity relationships")
        self.logger.info(
            f"Extracted status for {len(info_data.status_results)} entities")
        self.logger.info(
            f"Extracted additional info for {len(info_data.info_results)} entities")
        self.logger.info(
            f"Processed {len(date_data.date_results)} date entries")
        if date_data.basic_results:
            self.logger.info(
                f"Admission date: {date_data.basic_results.get('admission_date')}")
            self.logger.info(
                f"Discharge date: {date_data.basic_results.get('discharge_date')}")

        self._aggregate_results(
            ner_data=ner_data, entity_data=entity_data,
            info_data=info_data, date_data=date_data
        )
        self.logger.info("Results aggregation complete")
        self.logger.info("=== Single EHR Processing Complete ===")

    def _process_parallel_with_executor(self, ehr: str, ner_data: NERData, prev_ehr: str | None = None) -> tuple:
        self.logger.info(
            "Starting parallel processing with ThreadPoolExecutor...")
        entity_data_res, info_data_res, date_data_res = None, None, None
        # EXP-G ablation (c): when Date module is OFF, skip the date worker
        # entirely and return an empty DateData. This isolates the contribution
        # of date parsing / normalization to overall pipeline F1.
        if self.disable_date:
            self.logger.info("EXP-G ablation: Date module DISABLED; skipping DateProcessor")
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                entity_future = executor.submit(
                    self.entity_processor.process_entities, ner_data.ner_results, ner_data.parsed_tags)
                info_future = executor.submit(
                    self.info_processor.process_information, ner_data.ner_results, ner_data.parsed_tags)
                entity_data_res = entity_future.result()
                info_data_res = info_future.result()
            date_data_res = DateData(basic_results=None, date_results=[])
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Use ner_data.ner_results (the string with updated tags) and ner_data.parsed_tags
                entity_future = executor.submit(
                    self.entity_processor.process_entities, ner_data.ner_results, ner_data.parsed_tags)
                info_future = executor.submit(
                    self.info_processor.process_information, ner_data.ner_results, ner_data.parsed_tags)
                date_future = executor.submit(
                    self.date_processor.process_dates, ehr, ner_data.ner_results, prev_ehr,
                    ner_data.parsed_tags, self.admission_date, self.discharge_date
                )

                entity_data_res = entity_future.result()
                info_data_res = info_future.result()
                date_data_res = date_future.result()

        # Update PipelineCoordinator's date state from DateProcessor's results
        if date_data_res and date_data_res.basic_results:
            self.admission_date = date_data_res.basic_results.get(
                'admission_date', self.admission_date)
            self.discharge_date = date_data_res.basic_results.get(
                'discharge_date', self.discharge_date)
            # Update other basic info fields in pipeline_result dictionary
            self.pipeline_result.update(date_data_res.basic_results)
            self.logger.debug(
                f"Updated basic info from DateProcessor: Admission: {self.admission_date}, Discharge: {self.discharge_date}")

        self.logger.info(
            "Parallel processing with ThreadPoolExecutor complete")
        return entity_data_res, info_data_res, date_data_res

    def __call__(self, ehr, key):
        self.reinitialize()
        # Reset token statistics for new note processing
        self.model.start_new_note()
        note_started_at = datetime.utcnow().isoformat()
        note_errors: list[str] = []
        note_warnings: list[str] = []
        chunk_stats: list[dict] = []
        self.logger.info("====== Starting EHR chunking process... ======")
        chunked_ehr = [""]
        for item in self.model.chunker(ehr):
            if len(chunked_ehr[-1]) < 200 or len(item) < 300:
                chunked_ehr[-1] += item
            else:
                chunked_ehr.append(item)

        self.logger.info(
            f"Chunking complete. Split into {len(chunked_ehr)} chunks:")
        for i, chunk_text in enumerate(chunked_ehr):
            self.logger.debug(f"Chunk {i+1}: {len(chunk_text)} characters")

        if len(chunked_ehr) == 1:
            self.logger.info("Processing single chunk...")
            self._process_chunk_with_retry(
                chunk_text=ehr,
                prev_chunk_text=None,
                chunk_offset=0,
                original_ehr=ehr,
                chunk_index=1,
                total_chunks=1,
                chunk_stats=chunk_stats,
            )
        else:
            self.logger.info("Processing multiple chunks sequentially...")
            current_offset = 0
            for i in range(len(chunked_ehr)):
                self.logger.info(f"Processing chunk {i+1}/{len(chunked_ehr)}")
                current_chunk_ehr = chunked_ehr[i]
                prev_chunk_ehr = chunked_ehr[i-1] if i > 0 else None

                # Calculate the offset of this chunk in the original document
                if i > 0:
                    # Find the position of this chunk in the original text
                    chunk_start_in_original = ehr.find(
                        current_chunk_ehr, current_offset)
                    if chunk_start_in_original != -1:
                        current_offset = chunk_start_in_original
                    else:
                        # Fallback: estimate offset based on previous chunks
                        current_offset += len(chunked_ehr[i-1])
                        self.logger.warning(
                            f"Could not find exact position for chunk {i+1}, using estimated offset {current_offset}")

                self.logger.info(
                    f"Chunk {i+1} offset in original document: {current_offset}")

                self._process_chunk_with_retry(
                    chunk_text=current_chunk_ehr,
                    prev_chunk_text=prev_chunk_ehr,
                    chunk_offset=current_offset,
                    original_ehr=ehr,
                    chunk_index=i+1,
                    total_chunks=len(chunked_ehr),
                    chunk_stats=chunk_stats,
                )

                # Update offset for next iteration
                current_offset += len(current_chunk_ehr)

        self.logger.info("====== Chunk processing complete. ======")
        self.logger.info("====== Starting result aggregation... ======")
        aggregation_success = True
        try:
            self.result_aggregation(key)
            self.logger.info("====== Aggregation processing complete. ======")
        except Exception as e:
            aggregation_success = False
            note_errors.append(f"Aggregation error: {e}")
            self.logger.error(f"Aggregation failed for key {key}: {e}", exc_info=True)
        
        # Finalize note-level token statistics
        self.model.finish_note()
        self.logger.info("====== Note statistics finalized. ======")

        # Build report
        note_finished_at = datetime.utcnow().isoformat()
        # Determine overall status
        any_skipped = any(not cs.get('success', False) for cs in chunk_stats)
        if not any_skipped and aggregation_success:
            overall_status = 'success'
        elif aggregation_success:
            overall_status = 'partial'
        else:
            overall_status = 'partial'

        # Derive output path
        output_path = None
        try:
            schema_name = self.output_schema.schema_name.value
            output_type = self.output_schema.output_type.value
            base_dir = self.output_schema.output_dir
            if output_type == 'csv':
                output_path = os.path.join(base_dir, f"{key}_{schema_name}.csv")
            elif output_type == 'json':
                output_path = os.path.join(base_dir, f"{key}_{schema_name}.json")
            elif output_type == 'sqlite':
                # database path
                output_path = getattr(getattr(self.output_schema, 'formatter', None), 'db_path', None)
        except Exception:
            pass

        report = {
            'note_key': key,
            'started_at': note_started_at,
            'finished_at': note_finished_at,
            'duration_sec': max(0.0, (datetime.fromisoformat(note_finished_at) - datetime.fromisoformat(note_started_at)).total_seconds()) if note_started_at and note_finished_at else None,
            'overall_status': overall_status,
            'chunk_stats': chunk_stats,
            'module_stats': {
                'ner': getattr(self.ner_processor, 'last_run_stats', None),
                'entity': getattr(self.entity_processor, 'last_run_stats', None),
                'info': getattr(self.info_processor, 'last_run_stats', None),
                'date': getattr(self.date_processor, 'last_run_stats', None),
            },
            'aggregation_success': aggregation_success,
            'output_file_path': output_path,
            'errors': note_errors,
            'warnings': note_warnings,
        }

        return report
