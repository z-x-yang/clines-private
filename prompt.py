

class PROMPT():

    def __init__(self, prompt_name):

        self.prompt_name = prompt_name
        self.get_prompt_template()

    def get_prompt_template(self):

        if self.prompt_name in ['findentity']:
            self.template = '''
You will receive an electronic health record for a patient. Your task is to thoroughly identify and extract all biomedical entities or concepts mentioned in the record. These entities include, but are not limited to, lab tests, procedures, symptoms, diseases, allergies, medications, and more that relates to the patient, ignore the general terms. Be aware that some entities might be abbreviated or referred to by acronyms, and you should extract these as well. 

For your final output, annotate the original record by marking each extracted entity with <KEY> tags on both sides. Assign an integer to the value of KEY to indicate the order in which the entities appear.

Here is the record:

{note}

Annotated record:
'''
        elif self.prompt_name in ['recoverentity']:
            self.template = '''
You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to extract the marked entities in the record and recover the standard name or synonyms of the entities.

Your final outputs should be in the JSON format which is a list and the element in it should be a dictionary containing the keys of 

TAG: the order in which the entities appear. It is the same as the number of KEY value in the record;
CLEAN: the standard names or synonyms of the entities. 

Here is the record:

{note}

Json output:
'''
            # ORIGIN: the original name form of the entity in the record;
        elif self.prompt_name in ['findinfo']:
            self.template = '''
You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to find the information related to the entities extracted, such as modifiers, dosage, results, units, etc. 

The final answer should be provided in JSON format which is a list of python dictionary. For each entry dictionary, the value will be the related information which have to be a dictionary of keys: 
 - tag: the order in which the entities appear. It is the same as the number of KEY value in the record.
 - assertion_status: this should be one of the following categories: Present (the patient currently has the entities), Absent (the patient currently doesn't have or no longer has the entities), and Speculative (the patient will possibly have the entities). If this is not a suitable key for the entities, ignore this key in the dictionary.
 - body_location: this should be the body location related to the entity. This should be a short and clean phrase associated with a human body part, extracted from the origianl record. If this is not a suitable key for the entities, ignore this key in the dictionary.
 - value: this should be the value of the lab test or medication dosage, etc. If this is not a suitable key for the entities, ignore this key in the dictionary.
 - unit: this should be the unit corresponding to the value. If this is not a suitable key for the entities, ignore this key in the dictionary.

Here is the record:

{note}

Json output:
'''
             # - entity: this is the corresponding extracted entity.
        elif self.prompt_name in ['finddate_single']:
            self.template = '''
You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to find the event date for each entity. 

The final answer should be provided in JSON format which is a list of python dictionary.
Each entry dictionary should contain the keys of 
 - tag: the order in which the entities appear. It is the same as the number of KEY value in the record.
 - date: the value will be a list containing two pieces of date information in the format of [YYYY-MM-DD, YYYY-MM-DD], in which the first one is the possible starting time and the second is the end time. If there is only one date information for the entity put the same date to both entries. If there is no corresponding time information, use null as the value (such as {{"tag": "1", "date": [null, null]}}).

Here is the record:

{note}

Json output:
'''
            # - entity: this is the corresponding extracted entity.
        elif self.prompt_name in ['date_range']:
            self.template = '''
You will receive an electronic health record for a patient. Your task is extract the admission date and the discharge date of the patient.
Your output should be in JSON Array format: "[admission date, discharge date]". If this does not apply to the record provided, for example, use null to fill up the value (such as [null, null]).

Here is the record:

{note}

Output:
'''
            
        elif self.prompt_name in ['finddate_multi']:
            self.template = '''
You will be provided with a piece of texts from a electronic health record of a patient with the entities extracted (marked by <KEY> and </KEY>), and the previous piece from the same note, the admission date and the discharge date are also provided as contexts. Your task is to find the happening time for each entity and you can refer to the context information if necessary. 

The final answer should be provided in JSON format which is a list of python dictionary.
Each entry dictionary should contain the keys of 
 - tag: the order in which the entities appear. It is the same as the number of KEY value in the record.
 - date: the value will be a list containing two pieces of date information in the format of [YYYY-MM-DD, YYYY-MM-DD], in which the first one is the possible starting time and the second is the end time. If there is only one date information for the entity put the same date to both entries. If there is no corresponding time information, use null as the value (such as {{"tag": "1", "date": [null, null]}}).

Example:
```
[
  {{"tag": "1", "date": ["2118-06-02", "2118-06-14"]}},
  {{"tag": "2", "date": [null, null]}},
  {{"tag": "3", "date": ["before 10 years", "before 10 years"]}}
]
```

Here is the previous piece of the record for you to use as contexts.

{prev_note}

Here are the admission date: {adm_date}, the discharge date: {dis_date}.

Here is the piece of the record for you to extract:

{note}

Json output without comment:
'''
# - entity: this is the corresponding extracted entity.
    def apply_template(self, inputs):
        
        return self.template.format(**inputs)







    

            