

class PROMPT():

    def __init__(self, prompt_name):

        self.prompt_name = prompt_name

    def get_prompt_template(self):

        if self.prompt_name in ['findentity']:
            self.template = '''
You will be provided an electronic health record from a patient. Your task is to extract all the biomedical entities or concepts mentioned in the record. The biomedical entities include but are not limited to symptoms, diseases, allegies, medications, lab test, procedures, etc. Some entities are mentioned in the record using their abbreviations or acronyms, and you should also extract them. 

The final answer should be provided in JSON format including the orginal form of entity mentions in the record, the standard name, and the location where the entity is extracted.

Here is the record:

{note}
                            '''
        elif self.prompt_name in ['findinfo']:
            self.template = '''
You will be provided with an electronic health record from a patient and the entities extracted in this record. Your task is to find the information related to the entities extracted, such as modifiers, dosage, results, units, etc. 

The final answer should be provided in JSON format using the entities as the key of some dictionary formats, and the value will be the related information. 

Here is the record:

{note}

Here are the entities:

{entity}
                            '''
        elif self.prompt_name in ['finddate']:
            self.template = '''
You will be provided with an electronic health record from a patient, the entities extracted in this record, and the date the record was taken. Your task is to find the happening time for each entities. 

The final answer should be provided in JSON format using the entities as the key of some dictionary formats, and the value will be the date time information in the format of YYYY-MM-DD Hour:Minite:Second. If there is no corresponding time information, use 'not applicable' as the value.

Here is the record:

{note}

Here are the entities:

{entity}
                            '''
    def apply_template(self, ehr, entity=None):
        
        return self.template.format({'note': ehr, 'entity': entity})







    

            