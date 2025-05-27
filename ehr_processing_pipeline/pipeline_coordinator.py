import logging
import json
import re
import demjson3
import pprint
import threading
import concurrent.futures

from llm_interface.llm_manager import LLMManager
from llm_interface.retrieval.retriever_coordinator import RetrieverCoordinator
from prompt import PromptManager
from schema import SchemaProcessor, SchemaName, OutputType
from data_types import NERData, EntityData, InfoData, DateData
from check import process_lists_based_on_list1

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

    def __init__(self, model, schema='i2b2', format_type='csv', marker="", use_gpu=True, use_faiss_gpu=None, output_dir="outputs"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = model
        self.output_schema = SchemaProcessor(
            schema, format_type, marker, output_dir)

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

        self.reinitialize()
        self.logger.info(
            "PipelineCoordinator initialized with retriever, prompts, and processors.")

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
                mapped_code = json.loads(clean_item['CODE'])
                tmp['code'] = list(mapped_code.keys())[0]
                tmp['type'] = mapped_code[tmp['code']][1]
                tmp['code'] = tmp['code'] + '||' + mapped_code[tmp['code']][0]

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

    def deduplication(self, list_of_dict, key, parsed_ner_tags=None):
        # This method is kept here as it's used by other _process methods for now
        # and also passed to EntityProcessor.
        unique_list = []
        seen = set()
        for d in list_of_dict[::-1]:
            key_value = str(d.get(key))
            if parsed_ner_tags is not None and key_value not in map(str, parsed_ner_tags):
                continue
            if key_value not in seen:
                unique_list.append(d)
                seen.add(key_value)
        return unique_list[::-1]

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
            # Set original chunk token count before processing
            self.model.set_chunk_original_tokens(ehr)
            self.call_single(ehr, prev_ehr=None,
                             chunk_offset=0, original_ehr=ehr)
            self.model.finish_chunk()
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

                # Set original chunk token count before processing
                self.model.set_chunk_original_tokens(current_chunk_ehr)
                self.call_single(current_chunk_ehr, prev_ehr=prev_chunk_ehr,
                                 chunk_offset=current_offset, original_ehr=ehr)
                self.model.finish_chunk()

                # Update offset for next iteration
                current_offset += len(current_chunk_ehr)

        self.logger.info("====== Chunk processing complete. ======")
        self.logger.info("====== Starting result aggregation... ======")
        self.result_aggregation(key)
        self.logger.info("====== Aggregation processing complete. ======")
