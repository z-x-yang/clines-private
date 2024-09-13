

class PROMPT():

    def __init__(self, prompt_name):

        self.prompt_name = prompt_name
        self.get_prompt_template()

    def get_prompt_template(self):

        if self.prompt_name in ['findentity']:
            self.template = '''
You will receive an electronic health record for a patient. Your task is to thoroughly identify and extract all biomedical entities or concepts mentioned in the record. These entities include, but are not limited to, lab tests, procedures, symptoms, diseases, allergies, medications, and more. Be aware that some entities might be abbreviated or referred to by acronyms, and you should extract these as well.

For your final output, annotate the original record by marking each extracted entity with <KEY> tags on both sides. Assign an integer to the value of KEY to indicate the order in which the entities appear.

Here is the record:

{note}

'''
        elif self.prompt_name in ['recoverentity']:
            self.template = '''
You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to extract the marked entities in the record and recover the standard name or synonyms of the entities.

Your final outputs should be in the JSON format which is a list and the element in it should be a dictionary containing the keys of 

TAG: the order in which the entities appear. It is the same as the number of KEY value in the record;
ORIGIN: the original name form of the entity in the record;
CLEAN: the standard names or synonyms of the entities. 

Here is the record:

{note}

'''
        elif self.prompt_name in ['findinfo']:
            self.template = '''
You will be provided with an electronic health record from a patient with the entities extracted (marked by <KEY> and </KEY>) in this record. Your task is to find the information related to the entities extracted, such as modifiers, dosage, results, units, etc. 

The final answer should be provided in JSON format which is a list of python dictionary. For each entry dictionary, the value will be the related information which have to be a dictionary of keys: 
 - tag: this is the KEY value for each extracted entity.
 - entity: this is the corresponding extracted entity.
 - assertion_status: this should be one of the following categories: Present (the patient currently has the entities), Absent (the patient currently doesn't have or no longer has the entities), and Speculative (the patient will possibly have the entities). If this is not a suitable key for the entities, use 'Not Applicable'.
 - body_location: this should be the body location related to the entity. If this is not a suitable key for the entities, use 'Not Applicable'.
 - modifier: this should be the short phrase or adjectives that modify the entities, this should be an extraction from the record. If this is not a suitable key for the entities, use 'Not Applicable'.
 - value: this should be the value of the lab test or medication dosage, etc. If this is not a suitable key for the entities, use 'Not Applicable'.
 - unit: this should be the unit corresponding to the value. If this is not a suitable key for the entities, use 'Not Applicable'.
 - purpose: this should be a general phrase extracted from the record, describing the purpose of the entity. If this is not a suitable key for the entities, use 'Not Applicable'.

Here is the record:

{note}

'''
        elif self.prompt_name in ['finddate']:
            self.template = '''
You will be provided with an electronic health record from a patient with the entities extracted (marked by <KEY> and </KEY>) in this record, and the date the record was taken. Your task is to find the happening time for each entity. 

The final answer should be provided in JSON format which is a list of python dictionary.
Each entry dictionary should contain the keys of 
 - tag: this is the KEY value for each extracted entity.
 - entity: this is the corresponding extracted entity.
 - date: the value will be a list containing two pieces of date information in the format of [YYYY-MM-DD, YYYY-MM-DD], in which the first one is the possible starting time and the second is the end time. If there is only one date information for the entity put the same date to both entries. If there is no corresponding time information, use 'not applicable' as the value.

Here is the record:

{note}

'''
    def apply_template(self, ehr, entity=None):
        
        return self.template.format(**{'note': ehr, 'entity': entity})







    

            