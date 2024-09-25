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

    def __init__(self, model):
        """
        Initialize the PIPELINE with a language model and set up necessary components.

        Args:
            model (LLM): An instance of the language model.
        """
        self.model = model
        self.retriever = Retriever('cambridgeltl/SapBERT-from-PubMedBERT-fulltext')
        self.retriever.load_dictionary('./umls_dictionary.txt')
        self.retriever.embed_dictionary(4096)
        self.retriever.faiss_setup()
        self.prompt_ner = PROMPT('findentity')
        self.prompt_clean = PROMPT('recoverentity')
        self.prompt_info = PROMPT('findinfo')
        self.prompt_date_single = PROMPT('finddate_single')
        self.prompt_date_multi = PROMPT('finddate_multi')
        self.prompt_date_range = PROMPT('date_range')

        self.pipeline_result = {'ner_result': [],
                                'clean_results': [],
                                'info_results': [],
                                'date_results': [],
                                'parsed_ner_result': [],
                                'parsed_ner_context': []}
        self.admission_date = None
        self.discharge_date = None
        
    def reinitialize(self):
        """Reset the pipeline results and dates."""
        self.pipeline_result = {'ner_result': [],
                                'clean_results': [],
                                'info_results': [],
                                'date_results': [],
                                'parsed_ner_result': [],
                                'parsed_ner_context': []}
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
        result = result.replace('""', 'null')
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
        result = re.findall('<[^>]+>([^<>]+)<[^>]+>', string)
        return result

    def parse_ner_context(self, string):
        """
        Extract context around named entities from the NER result string.

        Args:
            string (str): The NER result string.

        Returns:
            list: List of context strings for each named entity.
        """
        matches = re.finditer('<[^>]+>([^<>]+)<[^>]+>', string)
        result = []
        for match in matches:
            start, end = match.span()
            before_start = max(0, start - 50)
            after_end = min(len(string), end + 50)
            context = string[before_start:after_end]
            context = re.sub(r'<[^>]+>', '', context).replace('\n', ' ')
            context = re.sub(r'[^\s]*>', '', context, 1)
            context = re.sub(r'<[^\s]*', '', context, 1)
            result.append(context)

        return result

    def entity_linking(self, ner_results):
        """
        Perform entity linking on the NER results.

        Args:
            ner_results (list): List of dictionaries containing NER results.

        Returns:
            list: NER results with added entity codes.
        """
        term_for_test = []
        for item in ner_results:
            term_for_test.append(item['CLEAN'])
        linking_result = self.retriever.embedding_retrieval(term_for_test, 256)
        for i in range(len(ner_results)):
            ner_results[i]['CODE'] = linking_result[i]
        return ner_results

    def result_aggregation(self):
        """
        Aggregate results from various pipeline steps into a single DataFrame.

        Returns:
            pd.DataFrame: Aggregated results.
        """
        aggregated_result = []
        for i in range(len(self.pipeline_result['clean_results'])):
            try:
                tmp = {
                    'index': i + 1, # self.pipeline_result['clean_results'][i]['TAG'],
                    'mention': self.pipeline_result['parsed_ner_result'][i],
                    'modifier': self.pipeline_result['parsed_ner_context'][i],
                    'code': self.pipeline_result['clean_results'][i]['CODE'],
                }
                tmp['assertion_status'] = self.pipeline_result['info_results'][i].get('assertion_status', pd.NA)
                tmp['body_location'] = self.pipeline_result['info_results'][i].get('body_location', pd.NA)
                tmp['value'] = self.pipeline_result['info_results'][i].get('value', pd.NA)
                tmp['unit'] = self.pipeline_result['info_results'][i].get('unit', pd.NA)
                
                tmp['begin_date'] = self.pipeline_result['date_results'][i]['date'][0]
                tmp['end_date'] = self.pipeline_result['date_results'][i]['date'][1]
            except:
                print(tmp)
                raise
            
            aggregated_result.append(tmp)

        aggregated_result = pd.DataFrame(aggregated_result)
        aggregated_result = aggregated_result.replace('(?i)none', pd.NA, regex = True)
        self.pipeline_result = {}

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
        query_ner = self.prompt_ner.apply_template({'note': ehr})
        ner_results = self.model(query_ner)
        print("ner_results:", ner_results, "\n####################\n")
        self.pipeline_result['ner_result'].append(ner_results)
        self.pipeline_result['parsed_ner_result'] += self.parse_ner_result(ner_results)
        self.pipeline_result['parsed_ner_context'] += self.parse_ner_context(ner_results)

        # Entity Cleaning and Linking
        self.model.new_chat()
        query_clean = self.prompt_clean.apply_template({'note': ner_results})
        clean_results = self.model(query_clean)
        print("clean_results:", clean_results, "\n####################\n")
        clean_results = demjson3.decode(self.parse_result(clean_results))
        clean_results = self.deduplication(clean_results, 'TAG')
        clean_results = self.entity_linking(clean_results)
        
        # Information Extraction
        self.model.new_chat()
        query_info = self.prompt_info.apply_template({'note': ner_results})
        info_results = self.model(query_info)
        print("info_results:", info_results, "\n####################\n")
        info_results = demjson3.decode(self.parse_result(info_results))
        info_results = self.deduplication(info_results, 'tag')
        
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
            
        # Aggregate results
        self.pipeline_result['clean_results'] += clean_results
        info_results, date_results = process_lists_based_on_list1(clean_results, info_results, date_results)
        self.pipeline_result['info_results'] += info_results
        self.pipeline_result['date_results'] += date_results
            
    def __call__(self, ehr):
        """
        Process an entire EHR through the pipeline.

        Args:
            ehr (str): The full EHR to process.

        Returns:
            dict: A dictionary containing the aggregated results and admission/discharge dates.
        """
        chunked_ehr = []
        for item in self.model.chunker(ehr):
            if len(item) < 300:
                chunked_ehr[-1] += item
            else:
                chunked_ehr.append(item)
        chunked_ehr = chunked_ehr[:3]
        if len(chunked_ehr) == 1:
            self.call_single(ehr)
        else:
            for i in range(len(chunked_ehr)):
                if i == 0:
                    self.call_single(chunked_ehr[i])
                else:
                    self.call_single(chunked_ehr[i], chunked_ehr[i-1])
                    
        result_dict = {
            "result_aggregation": self.result_aggregation().to_dict(orient='records'),
            "admission_date": self.admission_date,
            "discharge_date": self.discharge_date
        }
        print(result_dict)
        return result_dict

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

    parser = argparse.ArgumentParser(description='Process some EHR notes.')
    parser.add_argument('--model_name', type=str, default='llama-3-405b', help='Name of the model to use')
    parser.add_argument('--results_file', type=str, default='./results_0925.json', help='File to save the results')
    parser.add_argument('--max_retries', type=int, default=1, help='Maximum number of retries for processing each note')
    parser.add_argument('--debug', type=bool, default=False, help='Debug mode')
    parser.add_argument('--notes_file', type=str, default='./mimic-data-processing/cleaned_mimiciii_notes.csv', help='CSV file containing the notes')
    parser.add_argument('--error_log_file', type=str, help='File to save the error logs')
    
    args = parser.parse_args()
    if not args.error_log_file:
        args.error_log_file = args.results_file.replace('.json', '_error_log.json')
    
    model = LLM(args.model_name)
    pipeline = PIPELINE(model)

    notes = pd.read_csv(args.notes_file)
    
    # Initialize the results file
    with open(args.results_file, 'w') as f:
            json.dump([], f)
    
    # Initialize the error log file
    with open(args.error_log_file, 'w') as f:
            json.dump([], f)
            
    for i in tqdm(range(0, len(notes)), desc="Processing notes"):
        ehr = notes.iloc[i]['TEXT']
        
        if args.debug:   
            result = pipeline(ehr)
        else:
            for attempt in range(args.max_retries):
                try:
                    result = pipeline(ehr)
                    break
                except Exception as e:
                    if attempt < args.max_retries - 1:
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    else:
                        result = {"error": str(e)}
                        # Load existing error log
                        with open(args.error_log_file, 'r') as f:
                            error_log = json.load(f)
                        # Append new error
                        error_log.append({"index": i, "error": str(e)})
                        # Save updated error log
                        with open(args.error_log_file, 'w') as f:
                            json.dump(error_log, f, indent=4)
        
        # Load existing results
        with open(args.results_file, 'r') as f:
            all_results = json.load(f)
        
        # Append new result
        all_results.append(result)
        
        # Save updated results
        with open(args.results_file, 'w') as f:
            json.dump(all_results, f, indent=4, default=convert_to_serializable)
        
        # Release GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        pipeline.reinitialize()

    print("Processing complete.")        