from model import LLM, Retriever
from prompt import PROMPT
import pandas as pd
import re
import json
# from nltk import sent_tokenize

class PIPELINE():

    def __init__(self, model):

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

    def parse_result(self, string):
        result = re.findall('```[^`]+```', string)[0].strip('```').lstrip('json')
        return result

    def parse_ner_result(self, string):
        result = re.findall('<[^>]+>([^<>]+)<[^>]+>', string)
        return result

    def parse_ner_context(self, string):
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
        term_for_test = []
        for item in ner_results:
            term_for_test.append(item['CLEAN'])
        linking_result = self.retriever.embedding_retrieval(term_for_test, 4096)
        for i in range(len(ner_results)):
            ner_results[i]['CODE'] = linking_result[i]
        return ner_results

    def result_aggregation(self):

        aggregated_result = []
        for i in range(len(self.pipeline_result['clean_results'])):
            try:
                tmp = {
                    'index': self.pipeline_result['clean_results'][i]['TAG'],
                    'mention': self.pipeline_result['parsed_ner_result'][i],
                    'modifier': self.pipeline_result['parsed_ner_context'][i],
                    'code': self.pipeline_result['clean_results'][i]['CODE'],
                }
                # tmp.update(self.pipeline_result['info_results'][i])
                tmp['assertion_status'] = self.pipeline_result['info_results'][i].get('assertion_status', pd.NA)
                tmp['body_location'] = self.pipeline_result['info_results'][i].get('body_location', pd.NA)
                # tmp['modifier'] = self.pipeline_result['info_results'][i].get('modifier', None)
                tmp['value'] = self.pipeline_result['info_results'][i].get('value', pd.NA)
                tmp['unit'] = self.pipeline_result['info_results'][i].get('unit', pd.NA)
                # tmp['purpose'] = self.pipeline_result['info_results'][i].get('purpose', None)
                
                tmp['begin_date'] = self.pipeline_result['date_results'][i]['date'][0]
                tmp['end_date'] = self.pipeline_result['date_results'][i]['date'][1]
                # tmp.pop('tag')
            except:
                print(tmp)
                raise
            
            aggregated_result.append(tmp)

        aggregated_result = pd.DataFrame(aggregated_result)
        aggregated_result = aggregated_result.replace('(?i)none', pd.NA, regex = True)
        self.pipeline_result = {}

        return aggregated_result

    def call_single(self, ehr, prev_ehr = None):
        query_ner = self.prompt_ner.apply_template({'note': ehr})
        ner_results = self.model(query_ner)
        print(ner_results)
        self.pipeline_result['ner_result'].append(ner_results)
        self.pipeline_result['parsed_ner_result'] += self.parse_ner_result(ner_results)
        self.pipeline_result['parsed_ner_context'] += self.parse_ner_context(ner_results)

        self.model.new_chat()
        query_clean = self.prompt_clean.apply_template({'note': ner_results})
        clean_results = self.model(query_clean)
        print(clean_results)
        clean_results = json.loads(self.parse_result(clean_results))
        clean_results = self.entity_linking(clean_results)
        self.pipeline_result['clean_results'] += clean_results
        
        self.model.new_chat()
        query_info = self.prompt_info.apply_template({'note': ner_results})
        info_results = self.model(query_info)
        print(info_results)
        info_results = json.loads(self.parse_result(info_results))
        self.pipeline_result['info_results'] += info_results

        if prev_ehr is None:

            self.model.new_chat()
            query_date = self.prompt_date_range.apply_template({'note': ehr})
            date_results = self.model(query_date)
            date_results = json.loads(self.parse_result(date_results))
            self.admission_date = date_results[0]
            self.discharge_date = date_results[1]

            self.model.new_chat()
            query_date = self.prompt_date_single.apply_template({'note': ner_results})
            date_results = self.model(query_date)
            print(date_results)
            date_results = json.loads(self.parse_result(date_results))
            self.pipeline_result['date_results'] += date_results

        else:

            self.model.new_chat()
            query_date = self.prompt_date_multi.apply_template({'note': ner_results,
                                                                'prev_note': prev_ehr,
                                                                'adm_date': self.admission_date, 
                                                                'dis_date': self.discharge_date})
            date_results = self.model(query_date)
            date_results = json.loads(self.parse_result(date_results))
            self.pipeline_result['date_results'] += date_results
            

    def __call__(self, ehr):

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
                    
        print(self.result_aggregation(), self.admission_date, self.discharge_date)

if __name__ == '__main__':
    
    model = LLM('gpt4o')
    pipeline = PIPELINE(model)

    
    notes = pd.read_csv('./mimic-data-processing/cleaned_mimiciii_notes.csv')
    for i in range(0, len(notes)):
        ehr = notes.iloc[i]['TEXT']
        print(ehr)
        # print(model.chunker(ehr))
        # print(len(model.chunker(ehr)))
        # input()
        break
# break

    
    pipeline(ehr)
    
    
        
        
        
        
    
    