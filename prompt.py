

class PROMPT():

    def __init__(self, prompt_name):

        self.prompt_name = prompt_name
        self.get_prompt_template()

    def get_prompt_template(self):

        if self.prompt_name in ['findentity']:
            self.template = '''
You will receive an electronic health record for a patient. Your task is to thoroughly identify and extract all biomedical entities or concepts mentioned in the record. These entities include, but are not limited to, lab tests, procedures, symptoms, diseases, allergies, medications, and more that relates to the patient, ignore the general terms. Be aware that some entities might be abbreviated or referred to by acronyms, and you should extract these as well. 

For your final output, annotate the original record by marking each extracted entity with <KEY> tags on both sides. Assign an integer to the value of KEY to indicate the order in which the entities appear, such as <1>...</1>, <2>...</2>, <3>...</3>, etc.

Example 1:
The patient was taken to the <1>Operating Room</1>
for <2>wound exploration</2> directly from the <3>Trauma Room</3>.  The
patient was taken to the <4>Operating Room</4> for <5>chest CT</5>, as mentioned above,
for an <6>exploratory laparotomy</6>, <7>extensive lysis of adhesions</7>,
and control of <8>rectus and omental bleeding</8>._____s/p <9>radical resection</9> of right posterior shoulder <10>leiomyosarcoma</10>, negative margins.
<11>TUMOR SIZE</11>: 4 x 3.2 x 3 cm

Example 2:
<1>Hydrocodone</1> 7.5mg + <2>Apap</2> 325mg 7.5-325MG TABLETS take 1 PO as directed PRN <3>arthritis</3>; No Change  
<4>Lisinopril</4> 20 mg (20 MG TABLET Take 1) PO QD; No Change  
<5>Multivitamins</5> 1 TAB (TABLET) PO QD; No Change 

Here is the record:

{note}

Your annotated record:
'''
        elif self.prompt_name in ['recoverentity']:
            self.template = '''
You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to extract the marked entities in the record and recover the standard name or synonyms of the entities. You should select the standard name as similar to the marked entities as possible. For example, if the marked entities is a medication brand name, just keep the brand name.

If the marked entity is a number or unit, you should infer based on the context what is the biomedical concept it indicates. 

Your final outputs should be in the JSON format which is a list and the element in it should be a dictionary containing the keys of 

TAG: the order in which the entities appear. It is the same as the number of KEY value in the record;
CLEAN: the standard names or synonyms of the entities. 

Here is the record:

{note}

Your json output without comment:
'''


        elif self.prompt_name in ['findrelated']:
            # pass
            self.template = '''
You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to find the relatedness between entities based on the contexts. 

Your final outputs should be in the JSON format which is a list and the element in it should be a dictionary containing the keys of 

tag: the order in which the entities appear. It is the same as the number of KEY value in the record;
related: the list of KEY values of entities related to this entity.

For example:
[
  {{"tag": "1", "related": ["2", "3"]}},
  {{"tag": "2", "related": ["1"]}},
  {{"tag": "3", "related": ["1"]}},
]

Here is the record:

{note}

Your json output without comment:
'''
            
            # ORIGIN: the original name form of the entity in the record;

        elif self.prompt_name in ['findstatus']:
            self.template = '''
You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to find the information related to the entities extracted, such as modifiers, dosage, results, units, etc. 

The final answer should be provided in JSON format, a list of Python dictionaries. 
For each entry dictionary, the keys and values will be as follows: 
 - tag: the order in which the entities appear. It is the same as the number of **KEY** values in the record.
 - assertion_status: this should be one of the following 6 categories: Present; Absent; Possible; Conditional; Hypothetical; Not associated. 
   The definitions of each category are: 
   Present: problems associated with the patient can be present. Example: history of chest pain; the patient has had increasing weight gain.
   Absent: the note asserts that the problem does not exist in the patient. Example: patient denies pain; elevated enzymes resolved.
   Possible: the note asserts that the patient may have a problem, but there is uncertainty expressed in the note. Possible takes precedence over absent, so terms like “probably not” or “unlikely” categorize problems as being possible just as “probably” and “likely” do.  Example: We suspect this is pneumonia; pneumonia unlikely.
   Conditional: the mention of the medical problem asserts that the patient  experiences the problem only under certain conditions. Allergies can fall into this category. Example: Penicillin causes a rash; Ativan 0.5 mg IV q 4 to 6 hours prn anxiety.
   Not associated: the mention of the medical problem is associated  with someone who is not the patient. Example: Family history of prostate cancer.

Example:
CT showed <1>lesions</1> most likely secondary to <2>metastatic disease</2>. <3>Ativan</3> 0.5 mg IV q 4 to 6 hours prn <4>anxiety</4>.
```
[
  {{"tag": "1", "assertion_status": "Present"}},
  {{"tag": "2", "assertion_status": "Possible"}},
  {{"tag": "3", "assertion_status": "Present"}},
  {{"tag": "4", "assertion_status": "Conditional"}}
]
```

Here is the record:

{note}

Your json output without comment:
'''
            
        elif self.prompt_name in ['findinfo']:
            self.template = '''
You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to find the information related to the entities extracted, such as modifiers, dosage, results, units, etc. 

The final answer should be provided in JSON format which is a list of python dictionary. For each entry dictionary, the value will be the related information which have to be a dictionary of keys: 
 - tag: the order in which the entities appear. It is the same as the number of **KEY** value in the record.
 - body_location: this should be the body location related to the entity. This should be a short and clean phrase associated with a human body part, extracted from the origianl record. If this is not a suitable key for the entities, ignore this key in the dictionary.
 - value: this should be the value of the number corresponding to the marked entity, even though the marked entity is a number. If this is not a suitable key for the entities, ignore this key in the dictionary.
 - unit: this should be the unit corresponding to the value. If there is a value but no unit, you can infer the unit for the value. If this is not a suitable key for the entities, ignore this key in the dictionary.
 - infer: this relates to the unit key. If the unit key value is inferred, put True under this key, otherwise False. This key has to co-occur with the unit key.
 - note: this is a complementary key that should contain the additional necessary information as concisely as possible related to the entities. For example, the detailed condition of a disease or symptom or detailed medication instructions (e.g., frequency, timeline).
 
Example:
```
[
  {{"tag": "1", "value": "600", "unit": "mg", "note": "once every two days", 'infer': "False"}},
  {{"tag": "2", "value": "5.7", "unit": null, "body_location": "blood", 'infer': "False"}},
  {{"tag": "3", "body_location": "heart"}},
  {{"tag": "4", "value": "28", "unit": 'mmol/L', 'infer': "True"}},
  {{"tag": "5", "note": "severe"}}
]
```

Here is the record:

{note}

Your json output without comment:
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

Your output:
'''
        elif self.prompt_name in ['norm_date']:
            self.template = '''
Given an anchor time in the form of YYYY-MM-DD, what is the date range of "{date}" when the anchor time is {anchor}?
Your answer should be given in the form of [YYYY-MM-DD, YYYY-MM-DD] representing the start and end time.
Your final answer should be in JSON format.
Example:
```
["2118-06-02", "2118-06-14"]
```

Your json output without comment:
'''
            
        elif self.prompt_name in ['finddate_multi']:
            self.template = '''
You will be provided with a piece of texts from a electronic health record of a patient with the entities extracted (marked by <KEY> and </KEY>), and the previous piece from the same note, the admission date, and the discharge date are also provided as contexts. Your task is to find the happening time for each entity and you can refer to the context information if necessary. 

The final answer should be provided in JSON format which is a list of python dictionary.
Each entry dictionary should contain two keys:
 - tag: the order in which the entities appear. It is the same as the number of KEY value in the record.
 - date: the value will be a list containing two pieces of date information in the format of [YYYY-MM-DD, YYYY-MM-DD], in which the first one is the possible starting time and the second is the end time. If there is only one date information for the entity put the same date to both entries. If there is no corresponding time information, use [null, null] as the value (such as {{"tag": "1", "date": [null, null]}}).

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

Your json output without comment:
'''
# - entity: this is the corresponding extracted entity.
    def apply_template(self, inputs):
        
        return self.template.format(**inputs)







    

            