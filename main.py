from model import LLM, Retriever
from prompt import PROMPT
import pandas as pd
import re
import json


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
        self.prompt_date = PROMPT('finddate')

        self.pipeline_result = {}

    def parse_result(self, string):
        result = re.findall('```[^`]+```', string)[0].strip('```').lstrip('json')
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
            tmp = {
                'index': self.pipeline_result['clean_results'][i]['TAG'],
                'mention': self.pipeline_result['clean_results'][i]['ORIGIN'],
                'code': self.pipeline_result['clean_results'][i]['CODE'],
            }
            tmp.update(self.pipeline_result['info_results'][i])
            tmp['begin_date'] = self.pipeline_result['date_results'][i]['date'][0]
            tmp['end_date'] = self.pipeline_result['date_results'][i]['date'][1]
            tmp.pop('tag')
            tmp.pop('entity')
            
            aggregated_result.append(tmp)

        aggregated_result = pd.DataFrame(aggregated_result)
        aggregated_result = aggregated_result.replace('(?i)not applicable', pd.NA, regex = True)
        self.pipeline_result = {}

        return aggregated_result

    def __call__(self, ehr):

        
        query_ner = self.prompt_ner.apply_template(ehr)
        ner_results = self.model(query_ner)
        self.pipeline_result['ner_result'] = ner_results
        print('='*100)
        print(ner_results)
        
        self.model.new_chat()
        query_clean = self.prompt_clean.apply_template(self.pipeline_result['ner_result'])
        clean_results = self.model(query_clean)
        clean_results = json.loads(self.parse_result(clean_results))
        clean_results = self.entity_linking(clean_results)
        self.pipeline_result['clean_results'] = clean_results
        print('='*100)
        print(clean_results)
        
        self.model.new_chat()
        query_info = self.prompt_info.apply_template(self.pipeline_result['ner_result'], self.pipeline_result['clean_results'])
        info_results = self.model(query_info)
        info_results = json.loads(self.parse_result(info_results))
        self.pipeline_result['info_results'] = info_results
        print('='*100)
        print(info_results)

        self.model.new_chat()
        query_date = self.prompt_date.apply_template(self.pipeline_result['ner_result'], self.pipeline_result['clean_results'])
        date_results = self.model(query_date)
        date_results = json.loads(self.parse_result(date_results))
        self.pipeline_result['date_results'] = date_results
        print('='*100)
        print(date_results)

        
        print(self.result_aggregation())

if __name__ == '__main__':
    
    model = LLM('gpt4o')
    pipeline = PIPELINE(model)

    
    notes = pd.read_csv('./mimic-data-processing/cleaned_mimiciii_notes.csv')
    for i in range(len(notes)):
        ehr = notes.iloc[i]['TEXT']
        print(ehr)
        # input()
        break
# break

    
    pipeline(ehr)
    
    
        
        
        
        
    
    