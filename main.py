import os
import pandas as pd
from tqdm import tqdm
import json
import torch
import numpy as np
from model import LLM, Retriever
from prompt import PROMPT
import re
import demjson3
from check import process_lists_based_on_list1
import traceback
import sqlite3
from schema import Schema
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from data_types import NERData, EntityData, InfoData, DateData
import time


class PIPELINE:
    """
    A pipeline for processing electronic health records (EHR) using various NLP tasks.

    This class integrates multiple NLP tasks including named entity recognition (NER),
    entity linking, information extraction, and date extraction from EHR notes.

    Attributes:
        model (LLM): An instance of the language model for text generation.
        retriever (Retriever): An instance of the retriever for entity linking.
        prompt_ner (PROMPT): Prompt for named entity recognition.
        prompt_clean (PROMPT): Prompt for cleaning and recovering entities.
        prompt_info (PROMPT): Prompt for extracting additional information.
        prompt_date_single (PROMPT): Prompt for extracting dates from a single note.
        prompt_date_multi (PROMPT): Prompt for extracting dates from multiple notes.
        prompt_date_range (PROMPT): Prompt for extracting admission and discharge dates.
        pipeline_result (dict): Dictionary to store intermediate results.
        admission_date (str): Admission date extracted from the EHR.
        discharge_date (str): Discharge date extracted from the EHR.
    """

    def __init__(self, model, schema='i2b2', format_type='csv', marker="", use_gpu=True, use_faiss_gpu=None, output_dir="outputs"):
        """
        Initialize the PIPELINE with a language model and set up necessary components.

        Args:
            model (LLM): An instance of the language model.
        """
        self.model = model
        self.output_schema = Schema(schema, format_type, marker, output_dir)

        self.retriever = Retriever(
            'cambridgeltl/SapBERT-from-PubMedBERT-fulltext', use_gpu=use_gpu, use_faiss_gpu=use_faiss_gpu)
        self.retriever.load_dictionary_all('./umls_dictionary.txt')
        self.retriever.load_dictionary_bodyloc(
            './umls_body_loc_dictionary.txt')
        self.retriever.embed_dictionary(32768)

        self.retriever.faiss_setup()
        self.prompt_ner = PROMPT('findentity')
        self.prompt_relate = PROMPT('findrelated')
        self.prompt_clean = PROMPT('recoverentity')
        self.prompt_status = PROMPT('findstatus')
        self.prompt_info = PROMPT('findinfo')
        self.prompt_date_single = PROMPT('finddate_single')
        self.prompt_date_multi = PROMPT('finddate_multi')
        self.prompt_date_range = PROMPT('date_range')
        self.prompt_basic_info = PROMPT('basic_info')
        self.prompt_json_debug = PROMPT('json_debug')
        self.norm_date = PROMPT('norm_date')

        self.reinitialize()

    def reinitialize(self):
        """Reset the pipeline results and dates."""
        self.pipeline_result = {'ner_result': [],
                                'clean_results': [],
                                'info_results': [],
                                'status_results': [],
                                'date_results': [],
                                'parsed_ner_result': [],
                                'parsed_ner_context': [],
                                'relate_results': []}
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

    def parse_ner_result(self, string):
        """
        Extract named entities and their tags from the NER result string.
        Converts tags to sequential numbers and updates the original string.
        Handles repeated tags by assigning new sequential numbers to each instance.

        Args:
            string (str): The NER result string.

        Returns:
            tuple: (entities_list, tags_list, updated_string) containing:
                - entities_list: List of extracted named entities
                - tags_list: List of corresponding sequential tags
                - updated_string: NER string with updated sequential tags
        """
        # Find all tag positions and content
        matches = list(re.finditer(r'<([^<>]+)>(.*?)</\1>', string, re.DOTALL))

        # Filter out none/null/empty entities and remove their tags
        valid_matches = []
        updated_string = string

        # Process matches in reverse order to avoid position shifts
        for match in matches[::-1]:
            if match.group(2).lower() not in ['none', 'null', '']:
                # Insert at beginning to maintain original order
                valid_matches.insert(0, match)
            else:
                # Remove the tags but keep the content for invalid matches
                start, end = match.span()
                content = match.group(2)
                updated_string = updated_string[:start] + \
                    content + updated_string[end:]

        if not valid_matches:
            return [], [], updated_string

        # Extract entities and prepare for sequential numbering
        entities = [match.group(2) for match in valid_matches]
        old_tags = [match.group(1) for match in valid_matches]
        new_tags = [str(i+1) for i in range(len(valid_matches))]

        # Create list of replacements (position, old tag, new tag)
        replacements = []
        for i, match in enumerate(valid_matches):
            start = match.start()
            replacements.append((start, old_tags[i], new_tags[i]))

        # Sort replacements by position in reverse order
        replacements.sort(reverse=True)

        # Apply replacements from end to start to avoid position shifts
        for _, old_tag, new_tag in replacements:
            # Replace closing tag first, then opening tag
            updated_string = re.sub(
                f'</({old_tag})>',
                f'</{new_tag}>',
                updated_string,
                count=1
            )
            updated_string = re.sub(
                f'<({old_tag})>',
                f'<{new_tag}>',
                updated_string,
                count=1
            )

        # Print tag mapping if changes were made
        changes_made = any(old != new for old, new in zip(old_tags, new_tags))
        if changes_made:
            print("Tag corrections made:")
            for old, new in zip(old_tags, new_tags):
                if old != new:
                    print(f"  Tag {old} -> {new}")

        return entities, new_tags, updated_string

    def parse_ner_context(self, string, tag_list):
        """
        Extract context around named entities from the NER result string for specific tags.

        Args:
            string (str): The NER result string.
            tag_list (list): List of tags to extract context for.

        Returns:
            list: List of context strings for each tag in tag_list. If a tag is not found,
                 its corresponding context will be an empty string. If multiple matches are found
                 for a tag, only the first match's context is returned to maintain alignment with tag_list.
        """
        result = []

        # Create a dictionary to store all matches for each tag
        all_matches = {}

        # Find all tag patterns in the string first
        for match in re.finditer(r'<([^<>]+)>(.*?)</\1>', string, re.DOTALL):
            tag = match.group(1)
            if tag not in all_matches:
                all_matches[tag] = []
            all_matches[tag].append(match)

        # Process each tag in tag_list
        for tag in tag_list:
            if tag in all_matches and all_matches[tag]:
                # Use the first match for this tag
                match = all_matches[tag][0]

                # Extract context around the match
                start, end = match.span()
                before_start = max(0, start - 200)
                after_end = min(len(string), end + 200)
                context = string[before_start:after_end]

                # Clean up the context by removing tags
                context = re.sub(r'<[^>]+>', '', context).replace('\n', ' ')
                context = re.sub(r'[^\s]*>', '', context, 1)
                context = re.sub(r'<[^\s]*', '', context, 1)
                result.append(context)
            else:
                # If tag not found, add empty string
                result.append("")

        return result

    def entity_linking(self, results, type='all'):
        """
        Perform entity linking on the NER results.

        Args:
            results (list): List of dictionaries containing NER results.

        Returns:
            list: NER results with added entity codes.
        """

        if type == 'all':
            term_for_test = []
            for item in results:
                term_for_test.append(item['CLEAN'])
            linking_result = self.retriever.embedding_retrieval_all(
                term_for_test, 256)
            for i in range(len(results)):
                results[i]['CODE'] = linking_result[i]
        elif type == 'bodyloc':
            term_for_test = []
            for item in results:
                if 'body_location' in item:
                    term_for_test.append(item['body_location'])
                else:
                    term_for_test.append(None)
            linking_result = self.retriever.embedding_retrieval_bodyloc(
                term_for_test, 256)
            for i in range(len(linking_result)):
                if linking_result[i] is not None:
                    results[i]['body_code'] = linking_result[i]

        return results

    def result_aggregation(self, key):
        """
        Aggregate results from various pipeline steps into a single DataFrame.

        Returns:
            pd.DataFrame: Aggregated results.
        """
        aggregated_result = []
        for i in range(len(self.pipeline_result['clean_results'])):
            try:
                tmp = {
                    # self.pipeline_result['clean_results'][i]['TAG'],
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
                    'mention': self.pipeline_result['parsed_ner_result'][i],
                    'context': self.pipeline_result['parsed_ner_context'][i],
                }
                mapped_code = json.loads(
                    self.pipeline_result['clean_results'][i]['CODE'])
                tmp['code'] = list(mapped_code.keys())[0]
                tmp['type'] = mapped_code[tmp['code']][1]
                tmp['code'] = tmp['code'] + '||' + mapped_code[tmp['code']][0]
                tmp['assertion_status'] = self.pipeline_result['status_results'][i].get(
                    'assertion_status', None)
                tmp['body_location'] = self.pipeline_result['info_results'][i].get(
                    'body_location', None)

                mapped_code = self.pipeline_result['info_results'][i].get(
                    'body_code', None)
                if mapped_code is not None:
                    mapped_code = json.loads(mapped_code)
                    tmp['body_location_code'] = list(mapped_code.keys())[0]
                    tmp['body_location_code'] = tmp['body_location_code'] + \
                        '||' + mapped_code[tmp['body_location_code']][0]
                else:
                    tmp['body_location_code'] = None

                tmp['value'] = self.pipeline_result['info_results'][i].get(
                    'value', None)
                tmp['unit'] = self.pipeline_result['info_results'][i].get(
                    'unit', None)
                tmp['infer'] = self.pipeline_result['info_results'][i].get(
                    'infer', None)
                tmp['freq'] = self.pipeline_result['info_results'][i].get(
                    'freq', None)
                tmp['route'] = self.pipeline_result['info_results'][i].get(
                    'route', None)
                tmp['note'] = self.pipeline_result['info_results'][i].get(
                    'note', None)
                tmp['related'] = self.pipeline_result['relate_results'][i].get(
                    'related', None)
                # tmp['related'] = [json.dumps(item) if item is not None else None for item in tmp['related']]

                tmp['begin_date'] = self.pipeline_result['date_results'][i]['date'][0]
                tmp['end_date'] = self.pipeline_result['date_results'][i]['date'][1]
                aggregated_result.append(tmp)
            except Exception as e:
                print("tmp:", tmp)
                print("error:", e)
                raise e

        self.output_schema(aggregated_result)

    def deduplication(self, list_of_dict, key, parsed_ner_tags=None):
        """
        Remove duplicates from a list of dictionaries based on a specific key.
        Also removes entries if their key value is not in parsed_ner_tags.

        Args:
            list_of_dict (list): List of dictionaries.
            key (str): Key to use for deduplication.
            parsed_ner_tags (list, optional): List of valid tags. Defaults to None.

        Returns:
            list: Deduplicated list of dictionaries.
        """
        unique_list = []
        seen = set()
        for d in list_of_dict[::-1]:
            # Convert key value to string for consistent comparison
            key_value = str(d[key])

            # Skip if key value not in parsed_ner_tags (when provided)
            if parsed_ner_tags is not None and key_value not in map(str, parsed_ner_tags):
                continue

            if key_value not in seen:
                if 'related' in d:
                    d['related'] = list(map(int, d['related']))
                unique_list.append(d)
                seen.add(key_value)
        return unique_list[::-1]

    def filter_parsed_results(self, parsed_ner_results, parsed_ner_context, parsed_ner_tags, clean_results):
        """
        Filter parsed NER results and context based on clean results tags.

        Args:
            parsed_ner_results (list): List of parsed NER results
            parsed_ner_context (list): List of parsed NER contexts
            parsed_ner_tags (list): List of parsed NER tags
            clean_results (list): List of clean results with TAGs

        Returns:
            tuple: (filtered_ner_results, filtered_ner_context)
        """
        clean_result_tags = [item['TAG'] for item in clean_results]
        filtered_indices = [i for i, tag in enumerate(
            parsed_ner_tags) if tag in clean_result_tags]
        filtered_ner_results = [parsed_ner_results[i]
                                for i in filtered_indices]
        filtered_ner_context = [parsed_ner_context[i]
                                for i in filtered_indices]
        return filtered_ner_results, filtered_ner_context

    def safe_json_decode(self, json_string, max_retries=3):
        if max_retries > 0:
            max_retries = max_retries - 1
            try:
                output = demjson3.decode(json_string)
                return output
            except Exception as e:
                print(f"Error decoding JSON: {e}")
                print(f"Error result: {json_string}")
                print(f"Retrying... (remaining retries: {max_retries})")
                debug_query = self.prompt_json_debug.apply_template(
                    {'error_message': str(e), 'json_content': json_string})
                corrected_json = self.model(debug_query)
                corrected_json = self.parse_result(corrected_json)
                print("corrected json:", corrected_json)
                return self.safe_json_decode(corrected_json, max_retries)
        else:
            raise Exception("Failed to decode JSON after multiple retries")

    def _process_llm_query(self, prompt_obj, template_vars, parse_json=True, new_chat=True):
        """
        Helper method to process LLM queries with standard pattern of:
        new chat -> apply template -> get model response -> parse JSON result

        Args:
            prompt_obj (PROMPT): The prompt object to use
            template_vars (dict): Variables to apply to the template
            parse_json (bool): Whether to parse the result as JSON (default: True)
            max_retries (int): Maximum number of retries for decoding JSON (default: 3)

        Returns:
            The processed result (parsed JSON if parse_json=True, otherwise raw string)
        """
        if new_chat:
            self.model.new_chat()
        query = prompt_obj.apply_template(template_vars)
        result = self.model(query)
        if parse_json:
            parsed_result = self.parse_result(result)
            return self.safe_json_decode(parsed_result)
        return result

    def call_single(self, ehr: str, prev_ehr: Optional[str] = None) -> None:
        """
        Process a single Electronic Health Record (EHR) through the complete NLP pipeline.

        Args:
            ehr: The full EHR text to process
            prev_ehr: Optional previous EHR context for date extraction
        """
        print("\n=== Starting Single EHR Processing ===")
        print(f"Input EHR length: {len(ehr)} characters")
        print(f"Previous EHR provided: {prev_ehr is not None}")

        # 1. Named Entity Recognition
        print("\n1. Starting Named Entity Recognition...")
        ner_data = self._process_ner(ehr)
        print(f"Found {len(ner_data.parsed_tags)} entities")

        if len(ner_data.parsed_tags) == 0:
            print("No entities found - skipping further processing")
            return

        # 2. Entity Processing
        print("\n2. Starting Entity Processing...")
        entity_data = self._process_entities(
            ner_data.ner_results,
            ner_data.parsed_tags
        )
        print(f"Processed {len(entity_data.clean_results)} cleaned entities")
        print(f"Found {len(entity_data.relate_results)} entity relationships")

        # 3. Information Extraction
        print("\n3. Starting Information Extraction...")
        info_data = self._process_information(
            ner_data.ner_results,
            ner_data.parsed_tags
        )
        print(f"Extracted status for {len(info_data.status_results)} entities")
        print(
            f"Extracted additional info for {len(info_data.info_results)} entities")

        # 4. Date Processing
        print("\n4. Starting Date Processing...")
        date_data = self._process_dates(
            ehr,
            ner_data.ner_results,
            prev_ehr,
            ner_data.parsed_tags
        )
        print(f"Processed {len(date_data.date_results)} date entries")
        if date_data.basic_results:
            print(
                f"Admission date: {date_data.basic_results.get('admission_date')}")
            print(
                f"Discharge date: {date_data.basic_results.get('discharge_date')}")

        # 5. Aggregate and store results
        print("\n5. Aggregating Results...")
        self._aggregate_results(
            ner_data=ner_data,
            entity_data=entity_data,
            info_data=info_data,
            date_data=date_data
        )
        print("Results aggregation complete")
        print("\n=== Single EHR Processing Complete ===\n")

    def _process_ner(self, ehr: str) -> NERData:
        """Process Named Entity Recognition step."""
        # Get NER results from model
        ner_results = self._process_llm_query(
            self.prompt_ner,
            {'note': ehr},
            parse_json=False
        )
        print("ner_results:", ner_results, "\n####################\n")

        # Parse results and get updated string with sequential tags
        parsed_ner_results, parsed_ner_tags, updated_ner_results = self.parse_ner_result(
            ner_results)

        # Get context for entities
        parsed_ner_context = self.parse_ner_context(
            updated_ner_results, parsed_ner_tags)

        print("parsed_ner_results:", parsed_ner_results,
              len(parsed_ner_results), "\n####################\n")
        print("parsed_ner_tags:", parsed_ner_tags,
              len(parsed_ner_tags), "\n####################\n")

        return NERData(
            ner_results=updated_ner_results,
            parsed_results=parsed_ner_results,
            parsed_tags=parsed_ner_tags,
            parsed_context=parsed_ner_context
        )

    def _process_entities(self, ner_results: str, parsed_ner_tags: List[str]) -> EntityData:
        """Process entity relationships and cleaning."""
        # Process relationships
        relate_results = self._process_llm_query(
            self.prompt_relate,
            {'note': ner_results}
        )
        relate_results = self.deduplication(
            relate_results, 'tag', parsed_ner_tags)
        print("relate_results:", relate_results, "\n####################\n")

        # Process cleaning
        clean_results = self._process_llm_query(
            self.prompt_clean,
            {'note': ner_results}
        )
        clean_results = self.deduplication(
            clean_results, 'TAG', parsed_ner_tags)
        print("clean_results before linking:",
              clean_results, "\n####################\n")

        clean_results = self.entity_linking(clean_results, type='all')
        print("clean_results after linking:",
              clean_results, "\n####################\n")

        return EntityData(
            relate_results=relate_results,
            clean_results=clean_results
        )

    def _process_information(self, ner_results: str, parsed_ner_tags: List[str]) -> InfoData:
        """Process status and additional information extraction."""
        # Process status
        status_results = self._process_llm_query(
            self.prompt_status,
            {'note': ner_results}
        )
        status_results = self.deduplication(
            status_results, 'tag', parsed_ner_tags)
        print("status_results:", status_results, "\n####################\n")

        # Process additional information
        info_results = self._process_llm_query(
            self.prompt_info,
            {'note': ner_results}
        )
        info_results = self.deduplication(info_results, 'tag', parsed_ner_tags)
        print("info_results before linking:",
              info_results, "\n####################\n")

        if len(info_results) > 0:
            info_results = self.entity_linking(info_results, type='bodyloc')
            print("info_results after linking:",
                  info_results, "\n####################\n")
        else:
            print("info_results is empty")

        return InfoData(
            status_results=status_results,
            info_results=info_results
        )

    def _process_dates(self, ehr: str, ner_results: str, prev_ehr: Optional[str], parsed_ner_tags: List[str]) -> DateData:
        """Process date extraction and normalization."""
        if prev_ehr is None:
            date_data = self._process_initial_dates(
                ehr, ner_results, parsed_ner_tags)
        else:
            date_data = self._process_subsequent_dates(
                ner_results, prev_ehr, parsed_ner_tags)

        return date_data

    def _process_initial_dates(self, ehr: str, ner_results: str, parsed_ner_tags: List[str]) -> DateData:
        """Process dates for the first EHR."""
        # Extract basic information
        basic_results = self._process_llm_query(
            self.prompt_basic_info,
            {'note': ehr}
        )
        self.admission_date = basic_results['admission_date']
        self.discharge_date = basic_results['discharge_date']
        self.pipeline_result.update(basic_results)
        print("basic result:", basic_results, "\n####################\n")

        # Extract dates for each entity
        date_results = self._process_llm_query(
            self.prompt_date_single,
            {'note': ner_results}
        )
        print("Initial date_results:", date_results, "\n####################\n")
        date_results = self.deduplication(date_results, 'tag', parsed_ner_tags)
        date_results = self.normalize_date(date_results)

        return DateData(
            basic_results=basic_results,
            date_results=date_results
        )

    def _process_subsequent_dates(self, ner_results: str, prev_ehr: str, parsed_ner_tags: List[str]) -> DateData:
        """Process dates for subsequent EHRs."""
        date_results = self._process_llm_query(
            self.prompt_date_multi,
            {
                'note': ner_results,
                'prev_note': prev_ehr,
                'adm_date': self.admission_date,
                'dis_date': self.discharge_date
            }
        )
        print("Middle date_results:", date_results, "\n####################\n")
        date_results = self.deduplication(date_results, 'tag', parsed_ner_tags)
        date_results = self.normalize_date(date_results)

        return DateData(
            basic_results=None,
            date_results=date_results
        )

    def _aggregate_results(self, ner_data: NERData, entity_data: EntityData,
                           info_data: InfoData, date_data: DateData) -> None:
        """Aggregate all results into pipeline_result."""
        # Add clean results
        self.pipeline_result['clean_results'] += entity_data.clean_results

        # Process and align all results
        info_results, status_results, date_results, relate_results = process_lists_based_on_list1(
            entity_data.clean_results,
            info_data.info_results,
            info_data.status_results,
            date_data.date_results,
            entity_data.relate_results,
        )

        # Update pipeline results
        self.pipeline_result['info_results'] += info_results
        self.pipeline_result['status_results'] += status_results
        self.pipeline_result['date_results'] += date_results

        # Update relate results with offset
        offset = len(self.pipeline_result['relate_results'])
        for result in relate_results:
            result['related'] = list(
                map(lambda x: x + offset, result['related']))
        self.pipeline_result['relate_results'] += relate_results

        # Filter and add parsed results
        filtered_ner_results, filtered_ner_context = self.filter_parsed_results(
            ner_data.parsed_results,
            ner_data.parsed_context,
            ner_data.parsed_tags,
            entity_data.clean_results
        )
        self.pipeline_result['parsed_ner_result'] += filtered_ner_results
        self.pipeline_result['parsed_ner_context'] += filtered_ner_context

    def normalize_date(self, date_result):
        """
        Normalize date results by querying the model for each date.
        """
        for item in date_result:
            if item['date'][0] is not None and item['date'][1] is not None and len(re.findall(r'[0-9]+-[0-9]+-[0-9]+', item['date'][0])) == 0:
                print(f"\nNormalizing date: {item['date'][0]}")
                print(f"Admission date anchor: {self.admission_date}")

                query = self.norm_date.apply_template(
                    {'date': item['date'][0], 'anchor': self.admission_date})
                print(f"Generated query for normalization:\n{query}")

                normalized_date = self.safe_json_decode(
                    self.parse_result(self.model(query)))
                item['date'] = normalized_date
                print(f"Normalized result: {normalized_date}\n")

        return date_result

    def __call__(self, ehr, key):
        """
        Process an entire EHR through the pipeline.

        Args:
            ehr (str): The full EHR to process.

        Returns:
            dict: A dictionary containing the aggregated results and admission/discharge dates.
        """
        self.reinitialize()
        print(f"\n====== Starting EHR chunking process... ======")
        chunked_ehr = [""]
        for item in self.model.chunker(ehr):
            if len(chunked_ehr[-1]) < 200 or len(item) < 300:
                chunked_ehr[-1] += item
            else:
                chunked_ehr.append(item)

        print(f"Chunking complete. Split into {len(chunked_ehr)} chunks:")
        for i, chunk in enumerate(chunked_ehr):
            print(f"Chunk {i+1}: {len(chunk)} characters")

        if len(chunked_ehr) == 1:
            print("\nProcessing single chunk...")
            self.call_single(ehr)
        else:
            print("\nProcessing multiple chunks sequentially...")
            for i in range(len(chunked_ehr)):
                print(f"\nProcessing chunk {i+1}/{len(chunked_ehr)}")
                if i == 0:
                    print("Processing first chunk (no previous context)")
                    self.call_single(chunked_ehr[i])
                else:
                    print(f"Processing with previous chunk as context")
                    self.call_single(chunked_ehr[i], chunked_ehr[i-1])
        print("\n====== Chunk processing complete. ======")
        print("\n====== Starting result aggregation... ======")
        self.result_aggregation(key)
        print("\n====== Aggregation processing complete. ======")


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
    import json
    import pandas as pd
    from tqdm import tqdm
    import torch
    import traceback
    from datetime import datetime

    parser = argparse.ArgumentParser(description='Process some EHR notes.')
    parser.add_argument('--model_name', type=str,
                        default='llama-3-405b', help='Name of the model to use')
    parser.add_argument('--results_file', type=str,
                        default='./results_0927_3.json', help='File to save the results')
    parser.add_argument('--max_retries', type=int, default=1,
                        help='Maximum number of retries for processing each note')
    parser.add_argument('--debug', type=bool, default=False, help='Debug mode')
    parser.add_argument('--notes_dir', type=str,
                        default='./mimic-data-processing/cleaned_mimiciii_notes.csv', help='CSV file containing the notes')
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

    args = parser.parse_args()

    # Add timestamp to results and error log filenames
    base_results_file = args.results_file.rsplit('.', 1)[0]
    args.results_file = f"{base_results_file}.json"

    if not args.error_log_file:
        args.error_log_file = f"{base_results_file}_errors.log"

    print("Start initializing model")
    model = LLM(args.model_name)
    print("Model initialized")
    print("Start initializing pipeline")
    if args.model_name in ['llama-3-405b', 'deepseek']:
        use_faiss_gpu = False
    else:
        use_faiss_gpu = None
    pipeline = PIPELINE(model, args.schema, args.output_type,
                        args.marker, args.output_dir, use_faiss_gpu=use_faiss_gpu, output_dir=args.output_dir)
    print("Pipeline initialized")

    # Load existing results if start_index > 0
    if args.start_index > 0 and os.path.exists(args.results_file):
        try:
            with open(args.results_file, 'r') as f:
                all_results = json.load(f)
            all_results = [result for result in all_results if int(
                result.get('result_index', float('inf'))) < args.start_index]
        except Exception as e:
            print("error:", e)
            all_results = []
        try:
            with open(args.error_log_file, 'r') as f:
                error_log = json.load(f)
            error_log = [error for error in error_log if int(
                error.get('result_index', float('inf'))) < args.start_index]
        except Exception as e:
            print("error:", e)
            error_log = []
    else:
        all_results = []
        error_log = []

    # Save the updated results file
    with open(args.results_file, 'w') as f:
        json.dump(all_results, f, indent=4)

    # Save the updated error log file
    with open(args.error_log_file, 'w') as f:
        json.dump(error_log, f, indent=4)

    notes = [item for item in os.listdir(
        args.notes_dir) if item.endswith('.txt')]

    # Add variables to track total time and count
    total_processing_time = 0
    processed_notes_count = 0

    for i in tqdm(range(args.start_index, len(notes)), desc="Processing notes"):
        start_time = time.time()
        key = args.marker + '_' + notes[i].rstrip('.txt')
        print(
            f"\n========= Processing note {i+1}/{len(notes)}: {key} ==========")
        # Check if output file already exists
        output_file = f"{args.output_dir}/{key}_{args.schema}.csv"

        if os.path.exists(output_file):
            print(f"Skipping {key} - output file already exists")
            continue

        try:
            # First try UTF-8
            with open(os.path.join(args.notes_dir, notes[i]), 'r', encoding='utf-8') as f:
                ehr = ''.join(f.readlines())
        except UnicodeDecodeError:
            # If UTF-8 fails, try latin-1 (which can read any byte sequence)
            with open(os.path.join(args.notes_dir, notes[i]), 'r', encoding='latin-1') as f:
                ehr = ''.join(f.readlines())

        if args.debug:
            print("Debug mode")
            result = pipeline(ehr, key)
        else:
            print("Not debug mode")
            for attempt in range(args.max_retries):
                try:
                    result = pipeline(ehr, key)
                    break
                except Exception as e:
                    if attempt < args.max_retries - 1:
                        print(
                            f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    else:
                        # Get traceback string
                        traceback_str = traceback.format_exc()
                        # Append new error
                        error_log.append(
                            {"index": i, "key": key, "error": str(e), "traceback": traceback_str})
                        print("error:", str(e))
                        print("traceback:", traceback_str)
                        # Save updated error log
                        with open(args.error_log_file, 'w') as f:
                            json.dump(error_log, f, indent=4)

        print(f"========= Processing of {key} complete. ==========")
        # Calculate and track timing information
        elapsed_time = time.time() - start_time
        total_processing_time += elapsed_time
        processed_notes_count += 1
        avg_time = total_processing_time / processed_notes_count

        print(
            f"Time taken: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
        print(
            f"Average processing time so far: {avg_time:.2f} seconds ({avg_time/60:.2f} minutes)")

        # Release GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
