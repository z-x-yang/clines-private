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
                 shared_retriever: RetrieverCoordinator | None = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model
        self.output_schema = SchemaProcessor(
            schema, format_type, marker, output_dir)

        if shared_retriever is not None:
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
            self.prompt_json_debug, self.retriever, self.deduplication
        )
        # Instantiate InfoProcessor, passing the deduplication method from this class
        self.info_processor = InfoProcessor(
            self.model, self.prompt_status, self.prompt_info,
            self.prompt_json_debug, self.retriever, self.deduplication
        )
        # Instantiate DateProcessor
        self.date_processor = DateProcessor(
            self.model, self.prompt_basic_info, self.prompt_date_single,
            # norm_date is a PromptManager object
            self.prompt_date_multi, self.norm_date, self.prompt_json_debug,
            self.deduplication
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
                msg = str(e) if str(e) else repr(e)
                error_messages.append(msg)
                if attempts < self.chunk_max_retries:
                    self.logger.warning(
                        f"Chunk {chunk_index}/{total_chunks} failed: {msg}. Will retry after {self.chunk_retry_delay}s.")
                    time.sleep(self.chunk_retry_delay)
                else:
                    self.logger.error(
                        f"Chunk {chunk_index}/{total_chunks} failed after {self.chunk_max_retries} retries: {msg}",
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
            'parsed_ner_context': [], 'relate_results': [], 'parsed_ner_positions': [],
            'parsed_ner_tags': []
        }
        # NER renumbers entity tags 1..N PER CHUNK (see ner_processor), so every
        # chunk reuses the same low integers. _aggregate_results adds this
        # running offset to each chunk's tags so the accumulated pipeline_result
        # lives in one collision-free tag namespace, which is what lets
        # result_aggregation join its per-step lists by TAG instead of by index.
        self._tag_offset = 0
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
        parsed_ner_tags_list = self.pipeline_result.get('parsed_ner_tags', [])

        # Join every per-step list to clean_results by entity TAG, not by list
        # position. The per-step lists are produced in different orders/lengths
        # (aux is deduped to unique tags; parsed-NER keeps its own order;
        # clean_results may repeat a tag), so zipping them by index silently
        # attached a field to the wrong entity. _aggregate_results globalized
        # tags into one namespace, so TAG is a unique, stable join key.
        status_by_tag = {it['tag']: it for it in status_results_list
                         if isinstance(it, dict) and it.get('tag') is not None}
        info_by_tag = {it['tag']: it for it in info_results_list
                       if isinstance(it, dict) and it.get('tag') is not None}
        date_by_tag = {it['tag']: it for it in date_results_list
                       if isinstance(it, dict) and it.get('tag') is not None}
        relate_by_tag = {it['tag']: it for it in relate_results_list
                         if isinstance(it, dict) and it.get('tag') is not None}
        mention_by_tag = {}
        for idx, raw_tag in enumerate(parsed_ner_tags_list):
            tag = int(raw_tag)
            if tag not in mention_by_tag:
                mention_by_tag[tag] = (
                    parsed_ner_result_list[idx] if idx < len(parsed_ner_result_list) else None,
                    parsed_ner_context_list[idx] if idx < len(parsed_ner_context_list) else None,
                    parsed_ner_positions_list[idx] if idx < len(parsed_ner_positions_list) else None,
                )

        for i, clean_item in enumerate(clean_results_list):
            tmp = {}
            try:
                tag = int(clean_item['TAG'])
                mention, context, position = mention_by_tag.get(tag, (None, None, None))
                has_pos = position is not None and position != (-1, -1)
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
                    'mention': mention,
                    'context': context,
                    'mention_start_pos': position[0] if has_pos else None,
                    'mention_end_pos': position[1] if has_pos else None,
                }

                code_raw = clean_item.get('CODE') if isinstance(clean_item, dict) else None
                if code_raw:
                    mapped_code = json.loads(code_raw)
                    tmp['code'] = list(mapped_code.keys())[0]
                    tmp['type'] = mapped_code[tmp['code']][1]
                    tmp['code'] = tmp['code'] + '||' + mapped_code[tmp['code']][0]
                else:
                    self.logger.warning(f"Missing CODE for key {key}, item {i}; setting code/type to None")
                    tmp['code'] = None
                    tmp['type'] = None

                status_item = status_by_tag.get(tag, {})
                tmp['assertion_status'] = status_item.get(
                    'assertion_status', None)

                info_item = info_by_tag.get(tag, {})
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

                relate_item = relate_by_tag.get(tag, {})
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

                date_item = date_by_tag.get(tag, {})
                tmp['begin_date'] = date_item.get('date', [None, None])[0]
                tmp['end_date'] = date_item.get('date', [None, None])[1]
                if 'inferred' in date_item:
                    tmp['begin_date_inferred'] = date_item['inferred'][0]
                    tmp['end_date_inferred'] = date_item['inferred'][1]

                aggregated_result.append(tmp)
            except Exception as e:
                # Fail-fast (§2): this loop processes internal pipeline data, so
                # any error is an invariant violation, not a recoverable input.
                # The old handlers appended a partial `tmp` here — that silently
                # dropped fields (it's how the missing-CODE KeyError masked lost
                # assertion/value/date for unlinkable entities). The caller wraps
                # result_aggregation per-note, so re-raising fails one note
                # visibly (no output + error in its report) and continues the
                # run, instead of emitting a degraded record.
                self.logger.error(
                    f"Result aggregation failed for key {key}, item {i}: {e}", exc_info=True)
                raise

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
        filtered_ner_tags = [parsed_ner_tags[i] for i in filtered_indices]
        return filtered_ner_results, filtered_ner_context, filtered_ner_positions, filtered_ner_tags

    def _aggregate_results(self, ner_data: NERData, entity_data: EntityData,
                           info_data: InfoData, date_data: DateData) -> None:
        tag_offset = self._tag_offset
        n_chunk_tags = len(ner_data.parsed_tags)

        # Align aux lists to this chunk's (local) clean tags first — the
        # processors emitted their 'tag' fields in the same local 1..N space.
        info_results, status_results, date_results, relate_results = process_lists_based_on_list1(
            entity_data.clean_results, info_data.info_results,
            info_data.status_results, date_data.date_results, entity_data.relate_results
        )

        # Now lift every tag reference for this chunk by the running offset so
        # the accumulated pipeline_result lives in one collision-free namespace.
        # All tags become ints here, which also removes the str/int comparison
        # mismatch that filter_parsed_results / the by-tag join would otherwise
        # hit. clean['TAG'], aux 'tag', parsed tags and related-target tags are
        # all shifted by the SAME offset so relations keep resolving.
        for item in entity_data.clean_results:
            item['TAG'] = int(item['TAG']) + tag_offset
        for aux_list in (info_results, status_results, date_results, relate_results):
            for it in aux_list:
                if isinstance(it, dict) and it.get('tag') is not None:
                    it['tag'] = int(it['tag']) + tag_offset
        ner_data.parsed_tags = [int(t) + tag_offset for t in ner_data.parsed_tags]

        # Globalize related-target tags (LLM relation references, local 1..N)
        # by the SAME offset as the entities so they keep resolving. A target
        # outside this chunk's 1..N NER range, or non-numeric, is a hallucinated
        # reference: fail-fast (§2) instead of silently offsetting it into a
        # different chunk's namespace, which would fabricate a wrong edge. JSON
        # string-encoded relations are parsed first so they go through the same
        # validation rather than keeping un-globalized local tags.
        for result in relate_results:
            related = result.get('related')
            if not related:
                continue
            if isinstance(related, str):
                related = json.loads(related if related.strip() else '{}')
            if not isinstance(related, dict):
                raise TypeError(
                    f"Unexpected 'related' type {type(related)} on source tag {result.get('tag')}")
            new_related = {}
            for tgt_tag, rel_type in related.items():
                local_tgt = int(tgt_tag)
                if not (1 <= local_tgt <= n_chunk_tags):
                    raise ValueError(
                        f"Related-target tag {local_tgt} outside chunk NER range "
                        f"1..{n_chunk_tags} (source tag {result.get('tag')})")
                new_related[str(local_tgt + tag_offset)] = rel_type
            result['related'] = new_related

        filtered_ner_results, filtered_ner_context, filtered_ner_positions, filtered_ner_tags = self.filter_parsed_results(
            ner_data.parsed_results, ner_data.parsed_context,
            ner_data.parsed_tags, entity_data.clean_results, ner_data.parsed_positions
        )

        # Commit atomically: only touch self.pipeline_result after ALL of the
        # above (globalization, relation validation, filtering) has succeeded.
        # _process_chunk_with_retry re-runs this whole method on failure, so a
        # raise above must leave pipeline_result untouched — otherwise the retry
        # would duplicate this chunk's partial appends.
        self.pipeline_result['clean_results'] += entity_data.clean_results
        self.pipeline_result['info_results'] += info_results
        self.pipeline_result['status_results'] += status_results
        self.pipeline_result['date_results'] += date_results
        self.pipeline_result['relate_results'] += relate_results
        self.pipeline_result['parsed_ner_result'] += filtered_ner_results
        self.pipeline_result['parsed_ner_context'] += filtered_ner_context
        self.pipeline_result['parsed_ner_positions'] += filtered_ner_positions
        self.pipeline_result['parsed_ner_tags'] += filtered_ner_tags
        self._tag_offset += n_chunk_tags

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
