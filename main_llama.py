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

    def __init__(self, model, schema='i2b2', format_type='csv', marker="", use_gpu=True):
        """
        Initialize the PIPELINE with a language model and set up necessary components.

        Args:
            model (LLM): An instance of the language model.
        """
        self.model = model
        self.output_schema = Schema(schema, format_type, marker)

        # if self.save_mode == 'sqlite':
        #     self.connection = sqlite3.connect('outputs/sqlite_database.db')
        #     self.cursor = self.connection.cursor()

        self.retriever = Retriever(
            'cambridgeltl/SapBERT-from-PubMedBERT-fulltext', use_gpu=use_gpu)
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
        for result in results[::-1]:
            result = result.strip('```').lstrip('json')
            result = result.replace('None', 'null')
            result = result.replace('"null"', 'null')
            # result = result.replace('""', 'null')
            result = result.replace('"NA"', 'null')

            # Remove inline comments
            result = re.sub(r'\s*#.*$', '', result, flags=re.MULTILINE)
            # Remove C-style comments (both single-line and multi-line)
            result = re.sub(r'//.*?$|/\*.*?\*/', '', result,
                            flags=re.MULTILINE | re.DOTALL)

            try:
                _ = demjson3.decode(result)
                return result
            except:
                continue
        return string

    def parse_ner_result(self, string):
        """
        Extract named entities and their tags from the NER result string.
        Converts tags to sequential numbers and updates the original string.

        Args:
            string (str): The NER result string.

        Returns:
            tuple: (entities_list, tags_list, updated_string) containing:
                - entities_list: List of extracted named entities
                - tags_list: List of corresponding sequential tags
                - updated_string: NER string with updated sequential tags
        """
        result = re.findall(r'<([^<>]+)>(.*?)</\1>', string, re.DOTALL)
        entities = [item[1] for item in result]
        old_tags = [item[0] for item in result]

        # Create sequential tags
        new_tags = [str(i+1) for i in range(len(old_tags))]

        # Create mapping from old tags to new tags
        tag_mapping = dict(zip(old_tags, new_tags))

        # Print tag mapping if any tags were changed
        changes_made = any(old != new for old, new in tag_mapping.items())
        if changes_made:
            print("Tag corrections made:")
            for old_tag, new_tag in tag_mapping.items():
                if old_tag != new_tag:
                    print(f"  Tag {old_tag} -> {new_tag}")

        # Update the original string with new tags
        updated_string = string
        for old_tag, new_tag in tag_mapping.items():
            updated_string = updated_string.replace(
                f'<{old_tag}>', f'<{new_tag}>')
            updated_string = updated_string.replace(
                f'</{old_tag}>', f'</{new_tag}>')

        return entities, new_tags, updated_string

    def parse_ner_context(self, string):
        """
        Extract context around named entities from the NER result string.

        Args:
            string (str): The NER result string.

        Returns:
            list: List of context strings for each named entity.
        """
        matches = re.finditer(r'<([^<>]+)>(.*?)</\1>', string, re.DOTALL)
        result = []
        for match in matches:
            # print(match)
            # input()
            start, end = match.span()
            before_start = max(0, start - 50)
            after_end = min(len(string), end + 50)
            context = string[before_start:after_end]
            context = re.sub(r'<[^>]+>', '', context).replace('\n', ' ')
            context = re.sub(r'[^\s]*>', '', context, 1)
            context = re.sub(r'<[^\s]*', '', context, 1)
            result.append(context)

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

    # def write_sqlit(self, aggregated_result, key):

    #     tables = {'"ehr_id"': "TEXT",
    #               '"admission_date"': "TEXT",
    #               '"discharge_date"': "TEXT"}
    #     for key in aggregated_result[0]:
    #         tables[f'"{key}"'] =  "TEXT"
    #     create_table_query = [f'{k}'+' '+v for k, v in tables.items()]
    #     create_table_query = f"CREATE TABLE IF NOT EXISTS data ({', '.join(create_table_query)});"
    #     print(create_table_query)
    #     self.cursor.execute(create_table_query)
    #     self.connection.commit()

    #     insert_query = f"INSERT INTO data ({', '.join(tables)}) VALUES ({', '.join(['?' for _ in tables])})"
    #     print(insert_query)
    #     data_batch = []
    #     for item in aggregated_result:
    #         row = [key, self.admission_date, self.discharge_date]
    #         for key in item:
    #             row.append(item[key] if key != 'related' else json.dumps(item[key]))
    #         print(row)
    #         data_batch.append(row)

    #     self.cursor.executemany(insert_query, data_batch)
    #     self.connection.commit()  # Commit in batches
    #     data_batch.clear()

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
                    'gender': self.pipeline_result['gender'],
                    'death_date': self.pipeline_result['death_date'],
                    'birth_date': self.pipeline_result['birth_date'],
                    'race': self.pipeline_result['race'],

                    'ethnicity': self.pipeline_result['ethnicity'],
                    'zip_code': self.pipeline_result['zip_code'],
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

        # if self.save_mode == 'csv':

        #     aggregated_result = pd.DataFrame(aggregated_result)
        #     aggregated_result = aggregated_result.replace('(?i)none', pd.NA, regex = True)
        #     aggregated_result.to_csv(f"outputs/{key}_{self.admission_date}_{self.discharge_date}.csv")

        # elif self.save_mode == 'sqlite':

        #     self.write_sqlit(aggregated_result, key)

        # elif self.save_mode == 'json':

        #     with open(f"outputs/{key}_{self.admission_date}_{self.discharge_date}.json", 'w'):
        #         json.dump(aggregated_result, f)

        # return aggregated_result

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

    def call_single(self, ehr, prev_ehr=None):
        """
        Process a single EHR note through the pipeline.
        """
        # Named Entity Recognition
        query_ner = self.prompt_ner.apply_template({'note': ehr})
        ner_results = self.model(query_ner)
        print("ner_results:", ner_results, "\n####################\n")

        # Parse results and get updated string with sequential tags
        parsed_ner_results, parsed_ner_tags, updated_ner_results = self.parse_ner_result(
            ner_results)

        # Store the updated string instead of the original
        self.pipeline_result['ner_result'].append(updated_ner_results)
        parsed_ner_context = self.parse_ner_context(updated_ner_results)

        print("parsed_ner_results:", parsed_ner_results,
              len(parsed_ner_results), "\n####################\n")
        print("parsed_ner_tags:", parsed_ner_tags,
              len(parsed_ner_tags), "\n####################\n")

        ner_results = updated_ner_results

        # Entity Cleaning and Linking
        self.model.new_chat()
        query_relate = self.prompt_relate.apply_template({'note': ner_results})
        relate_results = self.model(query_relate)
        relate_results = demjson3.decode(self.parse_result(relate_results))
        relate_results = self.deduplication(
            relate_results, 'tag', parsed_ner_tags)
        print("relate_results:", relate_results, "\n####################\n")
        # raise
        self.model.new_chat()
        query_clean = self.prompt_clean.apply_template({'note': ner_results})
        clean_results = self.model(query_clean)
        clean_results = demjson3.decode(self.parse_result(clean_results))
        clean_results = self.deduplication(
            clean_results, 'TAG', parsed_ner_tags)
        print("clean_results 1:", clean_results, "\n####################\n")
        clean_results = self.entity_linking(clean_results, type='all')
        print("clean_results 2:", clean_results, "\n####################\n")
        # Information Extraction

        self.model.new_chat()
        query_info = self.prompt_status.apply_template({'note': ner_results})
        status_results = self.model(query_info)
        status_results = demjson3.decode(self.parse_result(status_results))
        status_results = self.deduplication(
            status_results, 'tag', parsed_ner_tags)
        print("status_results:", status_results, "\n####################\n")
        # raise

        self.model.new_chat()
        query_info = self.prompt_info.apply_template({'note': ner_results})
        info_results = self.model(query_info)
        info_results = demjson3.decode(self.parse_result(info_results))
        info_results = self.deduplication(info_results, 'tag', parsed_ner_tags)
        print("info_results 1:", info_results, "\n####################\n")
        if len(info_results) > 0:
            info_results = self.entity_linking(info_results, type='bodyloc')
            print("info_results 2:", info_results, "\n####################\n")

        # Date Extraction
        if prev_ehr is None:
            # Extract basic information
            self.model.new_chat()
            query_basic = self.prompt_basic_info.apply_template({'note': ehr})
            basic_results = self.model(query_basic)
            basic_results = demjson3.decode(self.parse_result(basic_results))
            self.admission_date = basic_results['admission_date']
            self.discharge_date = basic_results['discharge_date']
            self.pipeline_result.update(basic_results)
            print("basic result:", basic_results, "\n####################\n")

            # Extract dates for each entity
            self.model.new_chat()
            query_date = self.prompt_date_single.apply_template(
                {'note': ner_results})
            date_results = self.model(query_date)
            print("date_results 2:", date_results, "\n####################\n")
            date_results = demjson3.decode(self.parse_result(date_results))
            date_results = self.deduplication(
                date_results, 'tag', parsed_ner_tags)

            date_results = self.normalize_date(date_results)

        else:
            # Extract dates considering previous EHR context
            self.model.new_chat()
            query_date = self.prompt_date_multi.apply_template({'note': ner_results,
                                                                'prev_note': prev_ehr,
                                                                'adm_date': self.admission_date,
                                                                'dis_date': self.discharge_date})
            date_results = self.model(query_date)
            print("date_results 3:", date_results, "\n####################\n")
            date_results = demjson3.decode(self.parse_result(date_results))
            date_results = self.deduplication(
                date_results, 'tag', parsed_ner_tags)
            date_results = self.normalize_date(date_results)

        print(date_results)

        # Aggregate results
        self.pipeline_result['clean_results'] += clean_results
        info_results, status_results, date_results, relate_results = process_lists_based_on_list1(clean_results,
                                                                                                  info_results,
                                                                                                  status_results,
                                                                                                  date_results,
                                                                                                  relate_results,
                                                                                                  )
        self.pipeline_result['info_results'] += info_results
        self.pipeline_result['status_results'] += status_results
        self.pipeline_result['date_results'] += date_results
        offset = len(self.pipeline_result['relate_results'])
        for i in range(len(relate_results)):
            relate_results[i]['related'] = list(
                map(lambda x: x + offset, relate_results[i]['related']))
        self.pipeline_result['relate_results'] += relate_results

        # Filter parsed results and add to pipeline result
        filtered_ner_results, filtered_ner_context = self.filter_parsed_results(
            parsed_ner_results,
            parsed_ner_context,
            parsed_ner_tags,
            clean_results
        )
        self.pipeline_result['parsed_ner_result'] += filtered_ner_results
        self.pipeline_result['parsed_ner_context'] += filtered_ner_context

    def normalize_date(self, date_result):

        for item in date_result:
            if item['date'][0] is not None and item['date'][1] is not None and len(re.findall(r'[0-9]+-[0-9]+-[0-9]+', item['date'][0])) == 0:
                query = self.norm_date.apply_template(
                    {'date': item['date'][0], 'anchor': self.admission_date})
                print(query)
                item['date'] = demjson3.decode(
                    self.parse_result(self.model(query)))
                print(item['date'])

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
        print("Start processing:\n\n")
        chunked_ehr = [""]
        for item in self.model.chunker(ehr):
            if len(chunked_ehr[-1]) < 200 or len(item) < 300:
                chunked_ehr[-1] += item
            else:
                chunked_ehr.append(item)
        if len(chunked_ehr) == 1:
            self.call_single(ehr)
        else:
            for i in range(len(chunked_ehr)):
                if i == 0:
                    self.call_single(chunked_ehr[i])
                else:
                    self.call_single(chunked_ehr[i], chunked_ehr[i-1])

        self.result_aggregation(key)

        print("End processing.\n\n")


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
    parser.add_argument('--marker', type=str, default="xx",
                        help='markerfortheoutput')

    args = parser.parse_args()

    # Add timestamp to results and error log filenames
    base_results_file = args.results_file.rsplit('.', 1)[0]
    args.results_file = f"{base_results_file}.json"

    if not args.error_log_file:
        args.error_log_file = f"{base_results_file}_errors.log"

    model = LLM(args.model_name)
    pipeline = PIPELINE(model, args.schema, 'csv', use_gpu=False if args.model_name ==
                        'llama-3-405b' else True)

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

    for i in tqdm(range(args.start_index, len(notes)), desc="Processing notes"):
        key = args.marker + '_' + notes[i].rstrip('.txt')

        # Check if output file already exists
        output_file = f"outputs/{key}_{args.schema}.csv"
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
            print("debug mode")
            result = pipeline(ehr, key)
        else:
            print("not debug mode")
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

        print(f"Processing of {key} complete.")

        # Release GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
