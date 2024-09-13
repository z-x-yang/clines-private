from model import LLM
from prompt import PROMPT
import pandas as pd


class PIPELINE():

    def __init__(self, model):

        self.model = model
        self.prompt_ner = PROMPT('findentity')
        self.prompt_clean = PROMPT('recoverentity')
        self.prompt_info = PROMPT('findinfo')
        self.prompt_date = PROMPT('finddate')

        self.pipeline_result = {}
        
    def __call__(self, ehr):
            
        query_ner = self.prompt_ner.apply_template(ehr)
        ner_results = self.model(query_ner)
        self.pipeline_result['ner_result'] = ner_results
        print('='*100)
        print(ner_results)
        
        self.model.new_chat()
        query_clean = self.prompt_clean.apply_template(self.pipeline_result['ner_result'])
        clean_results = self.model(query_clean)
        self.pipeline_result['clean_results'] = clean_results
        print('='*100)
        print(clean_results)

        self.model.new_chat()
        query_info = self.prompt_info.apply_template(self.pipeline_result['ner_result'], self.pipeline_result['clean_results'])
        info_results = self.model(query_info)
        self.pipeline_result['info_results'] = info_results
        print('='*100)
        print(info_results)

        self.model.new_chat()
        query_date = self.prompt_date.apply_template(self.pipeline_result['ner_result'], self.pipeline_result['clean_results'])
        date_results = self.model(query_date)
        self.pipeline_result['date_results'] = date_results
        print('='*100)
        print(date_results)

        
        

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
    
    
        
        
        
        
    
    