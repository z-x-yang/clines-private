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

    def __init__(self, model, save_mode = 'sqlite'):
        """
        Initialize the PIPELINE with a language model and set up necessary components.

        Args:
            model (LLM): An instance of the language model.
        """
        self.model = model
        self.save_mode = save_mode

        if self.save_mode == 'sqlite':
            self.connection = sqlite3.connect('outputs/sqlite_database.db')
            self.cursor = self.connection.cursor()
            
        self.retriever = Retriever('cambridgeltl/SapBERT-from-PubMedBERT-fulltext')
        self.retriever.load_dictionary_all('./umls_dictionary.txt')
        self.retriever.load_dictionary_bodyloc('./umls_body_loc_dictionary.txt')
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
        result = re.findall('```[^`]+```', string)
        if len(result) == 0:
            return string
        result = result[0].strip('```').lstrip('json')
        result = result.replace('None', 'null')
        result = result.replace('"null"', 'null')
        # result = result.replace('""', 'null')
        result = result.replace('"NA"', 'null')
        return result

    def parse_ner_result(self, string):
        """
        Extract named entities from the NER result string.

        Args:
            string (str): The NER result string.

        Returns:
            list: List of extracted named entities.
        """

        result = re.findall(r'<([^<>]+)>(.*?)</\1>', string, re.DOTALL)
        result = [item[-1] for item in result]
        # print(len(result), result)

        return result

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
            linking_result = self.retriever.embedding_retrieval_all(term_for_test, 256)
            for i in range(len(results)):
                results[i]['CODE'] = linking_result[i]
        elif type == 'bodyloc':
            term_for_test = []
            for item in results:
                if 'body_location' in item:
                    term_for_test.append(item['body_location'])
                else:
                    term_for_test.append(None)
            linking_result = self.retriever.embedding_retrieval_bodyloc(term_for_test, 256)
            for i in range(len(linking_result)):
                if linking_result[i] is not None:
                    results[i]['body_code'] = linking_result[i]

        return results

    def write_sqlit(self, aggregated_result, key):
        
        tables = {'"ehr_id"': "TEXT", 
                  '"admission_date"': "TEXT",
                  '"discharge_date"': "TEXT"}
        for key in aggregated_result[0]:
            tables[f'"{key}"'] =  "TEXT"
        create_table_query = [f'{k}'+' '+v for k, v in tables.items()]
        create_table_query = f"CREATE TABLE IF NOT EXISTS data ({', '.join(create_table_query)});"
        print(create_table_query)
        self.cursor.execute(create_table_query)
        self.connection.commit()

        insert_query = f"INSERT INTO data ({', '.join(tables)}) VALUES ({', '.join(['?' for _ in tables])})"
        print(insert_query)
        data_batch = []
        for item in aggregated_result:
            row = [key, self.admission_date, self.discharge_date]
            for key in item:
                row.append(item[key] if key != 'related' else json.dumps(item[key]))
            print(row)
            data_batch.append(row)
        
            
        self.cursor.executemany(insert_query, data_batch)
        self.connection.commit()  # Commit in batches
        data_batch.clear()

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
                    'term_index': i + 1, # self.pipeline_result['clean_results'][i]['TAG'],
                    'mention': self.pipeline_result['parsed_ner_result'][i],
                    'context': self.pipeline_result['parsed_ner_context'][i],
                }
                mapped_code = json.loads(self.pipeline_result['clean_results'][i]['CODE'])
                tmp['code'] = list(mapped_code.keys())[0]
                tmp['type'] = mapped_code[tmp['code']][1]
                tmp['code'] = tmp['code'] + '||' + mapped_code[tmp['code']][0]
                tmp['assertion_status'] = self.pipeline_result['status_results'][i].get('assertion_status', None)
                tmp['body_location'] = self.pipeline_result['info_results'][i].get('body_location', None)

                mapped_code = self.pipeline_result['info_results'][i].get('body_code', None)
                if mapped_code is not None:
                    mapped_code = json.loads(mapped_code)
                    tmp['body_location_code'] = list(mapped_code.keys())[0]
                    tmp['body_location_code'] = tmp['body_location_code'] + '||' + mapped_code[tmp['body_location_code']][0]
                else:
                    tmp['body_location_code'] = None
        
                tmp['value'] = self.pipeline_result['info_results'][i].get('value', None)
                tmp['unit'] = self.pipeline_result['info_results'][i].get('unit', None)
                tmp['infer'] = self.pipeline_result['info_results'][i].get('infer', None)
                tmp['note'] = self.pipeline_result['info_results'][i].get('note', None)
                tmp['related'] = self.pipeline_result['relate_results'][i].get('related', None)
                # tmp['related'] = [json.dumps(item) if item is not None else None for item in tmp['related']]
                
                tmp['begin_date'] = self.pipeline_result['date_results'][i]['date'][0]
                tmp['end_date'] = self.pipeline_result['date_results'][i]['date'][1]
            except Exception as e:
                print("tmp:", tmp)
                print("error:", e)
                raise e
            
            aggregated_result.append(tmp)

        if self.save_mode == 'csv':
            
            aggregated_result = pd.DataFrame(aggregated_result)
            aggregated_result = aggregated_result.replace('(?i)none', pd.NA, regex = True)
            aggregated_result.to_csv(f"outputs/{key}_{self.admission_date}_{self.discharge_date}.csv")
            
        elif self.save_mode == 'sqlite':

            self.write_sqlit(aggregated_result, key)

        elif self.save_mode == 'json':

            with open(f"outputs/{key}_{self.admission_date}_{self.discharge_date}.json", 'w'):
                json.dump(aggregated_result, f)
                
        return aggregated_result
    
    def deduplication(self, list_of_dict, key):
        """
        Remove duplicates from a list of dictionaries based on a specific key.

        Args:
            list_of_dict (list): List of dictionaries.
            key (str): Key to use for deduplication.

        Returns:
            list: Deduplicated list of dictionaries.
        """
        unique_list = []
        seen = set()
        for d in list_of_dict[::-1]:
            if d[key] not in seen:
                if 'related' in d:
                    d['related'] = list(map(int, d['related']))
                unique_list.append(d)
                seen.add(d[key])
        return unique_list[::-1]

    def call_single(self, ehr, prev_ehr = None):
        """
        Process a single EHR note through the pipeline.

        Args:
            ehr (str): The EHR note to process.
            prev_ehr (str, optional): The previous EHR note for context. Defaults to None.
        """
        # Named Entity Recognition
        print(ehr)
        query_ner = self.prompt_ner.apply_template({'note': ehr})
        ner_results = self.model(query_ner)
        print("ner_results:", ner_results, "\n####################\n")
        self.pipeline_result['ner_result'].append(ner_results)
        self.pipeline_result['parsed_ner_result'] += self.parse_ner_result(ner_results)
        self.pipeline_result['parsed_ner_context'] += self.parse_ner_context(ner_results)
        print(self.parse_ner_result(ner_results),len(self.parse_ner_result(ner_results)))
        # Entity Cleaning and Linking
        self.model.new_chat()
        query_relate = self.prompt_relate.apply_template({'note': ner_results})
        relate_results = self.model(query_relate)
        relate_results = demjson3.decode(self.parse_result(relate_results))
        relate_results = self.deduplication(relate_results, 'tag')
        print("relate_results:", relate_results, "\n####################\n")
        # raise
        self.model.new_chat()
        query_clean = self.prompt_clean.apply_template({'note': ner_results})
        clean_results = self.model(query_clean)
        clean_results = demjson3.decode(self.parse_result(clean_results))
        clean_results = self.deduplication(clean_results, 'TAG')
        clean_results = self.entity_linking(clean_results, type='all')
        print("clean_results:", clean_results, "\n####################\n")
        # Information Extraction

        self.model.new_chat()
        query_info = self.prompt_status.apply_template({'note': ner_results})
        status_results = self.model(query_info)
        status_results = demjson3.decode(self.parse_result(status_results))
        status_results = self.deduplication(status_results, 'tag')
        print("status_results:", status_results, "\n####################\n")
        # raise
        
        self.model.new_chat()
        query_info = self.prompt_info.apply_template({'note': ner_results})
        info_results = self.model(query_info)
        # print("info_results:", self.parse_result(info_results), "\n####################\n")
        info_results = demjson3.decode(self.parse_result(info_results))
        info_results = self.deduplication(info_results, 'tag')
        info_results = self.entity_linking(info_results, type='bodyloc')
        print("info_results:", info_results, "\n####################\n")

        # Date Extraction
        if prev_ehr is None:
            # Extract admission and discharge dates
            self.model.new_chat()
            query_date = self.prompt_date_range.apply_template({'note': ehr})
            date_results = self.model(query_date)
            print("date_results 1:", date_results, "\n####################\n")
            date_results = demjson3.decode(self.parse_result(date_results))
            self.admission_date = date_results[0]
            self.discharge_date = date_results[1]

            # Extract dates for each entity
            self.model.new_chat()
            query_date = self.prompt_date_single.apply_template({'note': ner_results})
            date_results = self.model(query_date)
            print("date_results 2:", date_results, "\n####################\n")
            date_results = demjson3.decode(self.parse_result(date_results))
            date_results = self.deduplication(date_results, 'tag')

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
            date_results = self.deduplication(date_results, 'tag')
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
            relate_results[i]['related'] = list(map(lambda x: x + offset, relate_results[i]['related']))
        self.pipeline_result['relate_results'] += relate_results
        

    def normalize_date(self, date_result):

        for item in date_result:
            if item['date'][0] is not None and item['date'][1] is not None and len(re.findall(r'[0-9]+-[0-9]+-[0-9]+', item['date'][0])) == 0:
                query = self.norm_date.apply_template({'date': item['date'][0], 'anchor': self.admission_date})
                print(query)
                item['date'] = demjson3.decode(self.parse_result(self.model(query)))
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
        # result_dict = {
        #     "result_aggregation": self.result_aggregation(), #.to_dict(orient='records'),
        #     "admission_date": self.admission_date,
        #     "discharge_date": self.discharge_date
        # }
        # print(result_dict)
        print("End processing.\n\n")
        input()
        # return result_dict

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
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

if __name__ == '__main__':
    import argparse
    import json
    import pandas as pd
    from tqdm import tqdm
    import torch
    import traceback

    parser = argparse.ArgumentParser(description='Process some EHR notes.')
    parser.add_argument('--model_name', type=str, default='llama-3-405b', help='Name of the model to use')
    parser.add_argument('--results_file', type=str, default='./results_0927_3.json', help='File to save the results')
    parser.add_argument('--max_retries', type=int, default=1, help='Maximum number of retries for processing each note')
    parser.add_argument('--debug', type=bool, default=False, help='Debug mode')
    parser.add_argument('--notes_file', type=str, default='./mimic-data-processing/cleaned_mimiciii_notes.csv', help='CSV file containing the notes')
    parser.add_argument('--error_log_file', type=str, help='File to save the error logs')
    parser.add_argument('--start_index', type=int, default=0, help='Index to start processing from')
    
    args = parser.parse_args()
    if not args.error_log_file:
        args.error_log_file = args.results_file.replace('.json', '_error_log.json')
    
    model = LLM(args.model_name)
    pipeline = PIPELINE(model, 'sqlite')

    notes = pd.read_csv(args.notes_file)
    
    # Load existing results if start_index > 0
    if args.start_index > 0 and os.path.exists(args.results_file):
        with open(args.results_file, 'r') as f:
            all_results = json.load(f)
        with open(args.error_log_file, 'r') as f:
            error_log = json.load(f)
        
        # Remove entries with index >= start_index
        all_results = [result for result in all_results if int(result.get('result_index', float('inf'))) < args.start_index]
        error_log = [error for error in error_log if int(error.get('result_index', float('inf'))) < args.start_index]
    else:
        all_results = []
        error_log = []
    
    # Save the updated results file
    with open(args.results_file, 'w') as f:
        json.dump(all_results, f, indent=4)
    
    # Save the updated error log file
    with open(args.error_log_file, 'w') as f:
        json.dump(error_log, f, indent=4)        
                        
    for i in tqdm(range(args.start_index, len(notes)), desc="Processing notes"):
        ehr = notes.iloc[i]['TEXT']
        key = str(notes.iloc[i]['ROW_ID'])
        if args.debug:   
            result = pipeline(ehr, key)
        else:
            for attempt in range(args.max_retries):
                try:
                    result = pipeline(ehr, key)
                    break
                except Exception as e:
                    if attempt < args.max_retries - 1:
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    else:
                        result = {"error": str(e)}
                        # Get traceback string
                        traceback_str = traceback.format_exc()
                        # Append new error
                        error_log.append({"index": i, "error": str(e), "traceback": traceback_str})
                        print("error:", str(e))
                        print("traceback:", traceback_str)
                        # Save updated error log
                        with open(args.error_log_file, 'w') as f:
                            json.dump(error_log, f, indent=4)
        
        # # Add index to result
        # result['result_index'] = str(notes.iloc[i]['ROW_ID'])
        # result["result_aggregation"].to_csv(f"outputs/{notes.iloc[i]['ROW_ID']}_{result['admission_date']}_{result['discharge_date']}.csv")
        # result["result_aggregation"] = result["result_aggregation"].to_dict(orient='records')
        # # Append new result
        # all_results.append(result)
        # print(all_results)
        # # Save updated results
        # with open(args.results_file, 'w') as f:
        #     json.dump(all_results, f, indent=4, default=convert_to_serializable)
        
        # Release GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print("Processing complete.")        