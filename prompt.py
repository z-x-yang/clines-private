from platform import node


class PROMPT():

    def __init__(self, prompt_name):

        self.prompt_name = prompt_name
        self.get_prompt_template()

    def get_prompt_template(self):

        if self.prompt_name in ['findentity']:
            self.template = '''
Extract biomedical entities from the electronic health record below. Include tests, procedures, symptoms, diseases, allergies, medications, etc. Mark each entity with <KEY> tags (e.g., <1>entity</1>, <2>entity</2>).

Rules:
- Generally DO NOT mark values/units/routes/frequencies associated with primary entities
- EXCEPTION: For panel tests (Chem-7, CMP, CBC), mark each value as separate entity
- Include the main entity name even with abbreviations
- For overlapping entities, prioritize the most specific concept
- Mark negated findings (e.g., "no fever" → mark "fever")

Examples:

Input:
```
The patient was taken to the Operating Room for wound exploration directly from the Trauma Room. TUMOR SIZE: 4 x 3.2 x 3 cm, Chem-7: 127, 3.6, 88, 29, 16.5, 0.6, 143.
```

Output:
```
The patient was taken to the <1>Operating Room</1> for <2>wound exploration</2> directly from the <3>Trauma Room</3>. <4>TUMOR SIZE</4>: 4 x 3.2 x 3 cm, <5>Chem-7</5>: <6>127</6>, <7>3.6</7>, <8>88</8>, <9>29</9>, <10>16.5</10>, <11>0.6</11>, <12>143</12>.
```

Input:
```
Hydrocodone 7.5mg + Apap 325mg 7.5-325MG take 1 PO PRN arthritis; Pt c/o SOB and CP. EKG showed NSR. CBC with WNL RBC but WBC 12.4.
```

Output:
```
<1>Hydrocodone</1> 7.5mg + <2>Apap</2> 325mg 7.5-325MG take 1 PO PRN <3>arthritis</3>; <4>Pt</4> <5>c/o</5> <6>SOB</6> and <7>CP</7>. <8>EKG</8> showed <9>NSR</9>. <10>CBC</10> with <11>WNL</11> <12>RBC</12> but <13>WBC</13> 12.4.
```

Input:
```
{note}
```

Please respond with only the annotated record. Do not include any additional text. Output:
'''
        elif self.prompt_name in ['recoverentity']:
            self.template = '''
Recover standard names/synonyms for marked entities in this health record. For abbreviations, provide full forms. For values (numbers/units), infer the biomedical concept.

Output a JSON list of dictionaries with:
- TAG: the order number of the entity (from KEY tags)
- CLEAN: standardized name/synonym for the entity

Handling ambiguity:
- Use context to disambiguate abbreviations
- For unclear abbreviations, provide most common medical expansion
- For values, infer relevant biomedical concepts
- Standardize vague symptoms to specific medical terms

Example:
Input:
```
The patient reported <1>HTN</1> history and underwent <2>BP Measurement</2>, which showed <3>150/90 mmHg</3>. Labs revealed <4>Elevated A1C</4> at <5>7.5%</5>. Follow-up tests ruled out <6>CAD</6>, but a <7>1.5 cm Mass</7> was detected.
```

Output:
```
[
  {{"TAG": "1", "CLEAN": "Hypertension"}},
  {{"TAG": "2", "CLEAN": "Blood Pressure Measurement"}},
  {{"TAG": "3", "CLEAN": "Hypertensive Blood Pressure"}},
  {{"TAG": "4", "CLEAN": "Increased Hemoglobin A1C Level"}},
  {{"TAG": "5", "CLEAN": "Glycated Hemoglobin Measurement"}},
  {{"TAG": "6", "CLEAN": "Coronary Artery Disease"}},
  {{"TAG": "7", "CLEAN": "Mass"}}
]
```

Input:
```
{note}
```

Please respond with valid JSON only, no additional text. Output:
'''

        elif self.prompt_name in ['findrelated']:
            # pass
            self.template = '''
Identify relationships between marked entities in this health record. Find which entities are clinically related to each other and determine their relationship type.

Output a JSON list of dictionaries with:
- tag: entity order number (from KEY tags)
- related: a dictionary where the keys are the tags of related entities and the values are the relationship types

Relationship types include:
1. Treatment relationships:
   - "treats": medication/procedure treats condition
   - "manages": intervention manages but doesn't cure condition
   - "alleviates": relieves symptoms without treating cause

2. Causal relationships:
   - "causes": directly causes another entity
   - "exacerbates": worsens condition
   - "indicates": suggests or points to
   - "risk_factor": increases risk
   - "complication_of": is a complication
   
3. Measurement relationships:
   - "measures": test measures parameter
   - "evaluates": assesses condition
   - "diagnoses": used to diagnose
   - "monitors": tracks over time
   - "has_value": entity has numerical value
   - "has_unit": measurement has unit
   
4. Anatomical relationships:
   - "located_in": anatomical location
   - "part_of": component of larger system
   - "administered_at": administration site
   
5. Temporal relationships:
   - "precedes": occurs before
   - "follows": occurs after
   - "concurrent_with": happens simultaneously
   
6. Clinical relationships:
   - "symptom_of": symptom of condition
   - "finding_of": clinical finding
   - "manifestation_of": visible manifestation
   - "has_dosage": medication and dose
   - "has_frequency": med frequency
   - "has_route": administration route
   - "component_of": part of procedure/panel
   
7. Default relationship:
   - "related_to": general association when specific type unclear

Example:
Input:
```
Patient with <1>hypertension</1> takes <2>lisinopril</2> 20mg daily. <3>Blood pressure</3> was <4>142/88</4> <5>mmHg</5>.
```

Output:
```
[
  {{"tag": "1", "related": {{"2": "treated_by", "3": "measured_by"}}}},
  {{"tag": "2", "related": {{"1": "treats"}}}},
  {{"tag": "3", "related": {{"1": "measures", "4": "has_value", "5": "has_unit"}}}},
  {{"tag": "4", "related": {{"3": "value_of", "5": "measured_in"}}}},
  {{"tag": "5", "related": {{"3": "unit_of", "4": "unit_for"}}}}
]
```

Input:
```
{note}
```

Please respond with valid JSON only, no additional text. Output:
'''

        elif self.prompt_name in ['findstatus']:
            self.template = '''
Determine the assertion status for every entity marked by <KEY> and </KEY> in this health record.

Output a JSON list of dictionaries with:
- tag: entity order number (from KEY tags)
- assertion_status: one of these categories:
  * Present: problem currently exists. Example: "History of chest pain"; "The patient has had increasing weight gain."
  * Absent: problem definitely does not exist. Example: "Patient denies pain"; "Elevated enzymes have resolved."
  * Historical: problem existed in past but not currently. Example: "Patient was previously on medication X but has since discontinued it"; "Past history of asthma that is currently in remission."
  * Possible: problem may exist (uncertain, suspected). Example: "We suspect this is pneumonia"; "Pneumonia unlikely."
  * Conditional: problem occurs only under certain conditions. Example: "Penicillin causes a rash"; "Ativan 0.5 mg IV q4-6 hours as needed for anxiety."
  * Hypothetical: problem mentioned theoretically. Example: "If the patient were to experience chest pain, it could indicate a myocardial infarction."
  * Notassociated: problem relates to someone other than patient. Example: "Family history of prostate cancer."

Ambiguity guidelines:
- Prioritize most severe/current mention
- For medications, consider Present unless explicitly discontinued
- "Patient at risk for X" = Hypothetical
- "No evidence of X" = Absent
- "Cannot rule out X" = Possible
- For family history, classify conditions as Notassociated

IMPORTANT CLARIFICATION:
- "Presenting with a history of X" or "X-day history of Y" typically means the symptom/problem Y is PRESENT and has been occurring for X time period
- Only classify symptoms as Historical when there is clear indication the problem has resolved
- Key phrases indicating PRESENT status despite "history" wording:
  * "presenting with history of..." = Present
  * "recent history of..." = Present
  * "with X day/week history of..." = Present
  * "comes with history of..." = Present
- Key phrases indicating HISTORICAL status:
  * "past medical history significant for..." = Historical
  * "previous history of... now resolved" = Historical
  * "history of... that has since improved" = Historical

Example:
Input:
```
CT showed <1>lesions</1> most likely secondary to <2>metastatic disease</2>. <3>Ativan</3> 0.5 mg IV q 4 to 6 hours prn <4>anxiety</4>. Patient presenting with a 7 day history of <5>headaches</5> and <6>fever</6>.
```

Output:
```
[
  {{"tag": "1", "assertion_status": "Present"}},
  {{"tag": "2", "assertion_status": "Possible"}},
  {{"tag": "3", "assertion_status": "Present"}},
  {{"tag": "4", "assertion_status": "Conditional"}},
  {{"tag": "5", "assertion_status": "Present"}},
  {{"tag": "6", "assertion_status": "Present"}}
]
```

Input:
```
{note}
```

Please respond with valid JSON only, no additional text. Output:
'''

        elif self.prompt_name in ['findinfo']:
            self.template = '''
Extract detailed information for each marked entity in this health record.

The final answer should be provided in JSON format which is a list of python dictionary. For each entry dictionary, the value will be the related information which have to be a dictionary of keys:
 - tag: the order in which the entities appear. It is the same as the number of **KEY** value in the record.
 - body_location: this should be the body location related to the entity. This should be a short and clean phrase associated with a human body part, extracted from the origianl record. If this is not a suitable key for the entities, ignore this key in the dictionary.
 - value: this should be the value or values associated with the entity in the text, even if they are not explicitly marked. For entities with multiple values, use an array. This should also contain the possible text-based short phrase value such as negative x2, positive, or decreasing. If this is not a suitable key for the entities, ignore this key in the dictionary.
 - note: if there is a numerical value, you should put 'greater', 'lower', or 'equal' to this key. To indicate whether the actual value is greater, lower or equals to the recorded value. For multiple values, use an array that corresponds to each value.
 - unit: this should be the unit corresponding to the value. If there is a value but no unit, you can infer the unit for the value. For multiple values, use an array that corresponds to each value. If this is not a suitable key for the entities, ignore this key in the dictionary.
 - infer: this relates to the unit key. If the value under "unit" key is inferred, put true under this key, otherwise false. For multiple units, use an array of booleans that corresponds to each unit. This key has to co-occur with the unit key.
 - route: this key only presents when the entity is a medication, this should contain the information about how the medication should be taken, for example, p.o. or IV.
 - freq: this key only presents when the entity is a medication, this should contain the information about how frequent the medication should be taken, for example, p.i.d or prn or once every two days.
 - other: this key captures descriptive information about the entity that doesn't fit into other fields (like value or note). Examples include severity descriptions, duration, characteristics, or contextual details about the entity.

Special handling:
- For panel tests, individual values are marked as separate entities
- For entities with multiple values, use arrays for value/unit/note/infer
- Infer units only when clear from context
- For qualitative terms (e.g., "elevated"), use exact term as value

Example 1:
Input:
```
<1>Metoprolol</1> 50 mg PO BID for <2>hypertension</2>. <3>Chem-7</3>: <4>127</4>, <5>3.6</5>, <6>88</6>.
```

Output:
```
[
  {{"tag": "1", "value": "50", "unit": "mg", "route": "PO", "freq": "BID", "infer": false}},
  {{"tag": "2", "body_location": null, "other": "being treated with Metoprolol"}},
  {{"tag": "3", "value": null}},
  {{"tag": "4", "value": "127", "unit": "mEq/L", "note": "equal", "infer": true}},
  {{"tag": "5", "value": "3.6", "unit": "mEq/L", "note": "equal", "infer": true}},
  {{"tag": "6", "value": "88", "unit": "mEq/L", "note": "equal", "infer": true}}
]
```

Example 2:
Input:
```
<1>Glucose</1> readings: 112 mg/dL (fasting), 145 mg/dL (after meal). <2>Pain</2> in <3>lower back</3> rated 8/10 in morning, 6/10 in evening.
```

Output:
```
[
  {{"tag": "1", "value": ["112", "145"], "unit": ["mg/dL", "mg/dL"], "note": ["equal", "equal"], "infer": [false, false], "other": "first reading was fasting, second was after meal"}},
  {{"tag": "2", "value": ["8/10", "6/10"], "body_location": "lower back", "infer": [false, false], "other": "worse in morning, improves in evening"}},
  {{"tag": "3", "body_location": "lower back"}}
]
```

Input:
```
{note}
```

Please respond with valid JSON only, no additional text. Output:
'''

#         elif self.prompt_name in ['findinfo_i2b2']:
#             self.template = '''
# You will receive an electronic health record with named entities marked by <KEY> and </KEY>. Your task is to find the information related to the entities extracted, such as modifiers, dosage, results, units, etc.

# The final answer should be provided in JSON format which is a list of python dictionary. For each entry dictionary, the value will be the related information which have to be a dictionary of keys:
#  - tag: the order in which the entities appear. It is the same as the number of **KEY** value in the record.
#  - value: this should be the value of the number corresponding to the marked entity, even though the marked entity is a number. If this is not a suitable key for the entities, ignore this key in the dictionary.
#  - unit: this should be the unit corresponding to the value. If there is a value but no unit, you can infer the unit for the value. If this is not a suitable key for the entities, ignore this key in the dictionary.
#  - infer: this relates to the unit key. If the unit key value is inferred, put True under this key, otherwise False. This key has to co-occur with the unit key.
#  - note: this is a complementary key that should contain the additional necessary information as concisely as possible related to the entities. For example, the detailed condition of a disease or symptom or detailed medication instructions (e.g., frequency, timeline).

# Example:
# ```
# [
#   {{"tag": "1", "value": "600", "unit": "mg", "note": "once every two days", 'infer': false}},
#   {{"tag": "2", "value": "5.7", "unit": null, "body_location": "blood", 'infer': false}},
#   {{"tag": "3", "body_location": "heart"}},
#   {{"tag": "4", "value": "28", "unit": 'mmol/L', 'infer': true}},
#   {{"tag": "5", "note": "severe"}}
# ]
# ```

# Here is the record:

# {note}

# Your json output without comment:
# '''

            # - entity: this is the corresponding extracted entity.
        elif self.prompt_name in ['finddate_single']:
            self.template = '''
Extract event dates for entities marked by <KEY> tags in this health record.

Output JSON list of dictionaries with:
 - tag: entity order number from KEY tags
 - date: [YYYY-MM-DD, YYYY-MM-DD] for start and end dates (use same date for single events, null for unknown)
 - inferred: [true/false, true/false] indicating if each date was inferred rather than explicitly stated

Key Rules:
- "Presenting with X day history of Y" → END = visit date, START = END minus X days, both inferred=true
- "X-day history of", "for past X days" → Calculate precise start date
- "Has been [action] for X years" → END = visit date, START = END minus X years
- Acute events with specific date → Use same date for start/end
- Explicitly recorded dates → inferred=false
- Chronic conditions without specific dates → [null, null]
- When symptoms share time reference → Apply same date range to all

Example 1:
Input:
```
Patient was admitted on <1>2023-05-15</1> with complaints of <2>chest pain</2> that started 3 days prior. <3>CBC</3> was done on admission. Patient has a history of <4>hypertension</4> for many years.
```

Output:
```
[
  {{"tag": "1", "date": ["2023-05-15", "2023-05-15"], "inferred": [false, false]}},
  {{"tag": "2", "date": ["2023-05-12", "2023-05-15"], "inferred": [true, false]}},
  {{"tag": "3", "date": ["2023-05-15", "2023-05-15"], "inferred": [false, false]}},
  {{"tag": "4", "date": [null, null], "inferred": [false, false]}}
]
```

Example 2:
Input:
```
On 2023-07-10, patient presenting with a 7 day history of <1>headaches</1>, <2>sore throat</2>, <3>cough</3>, and <4>fever</4>.
```

Output:
```
[
  {{"tag": "1", "date": ["2023-07-03", "2023-07-10"], "inferred": [true, true]}},
  {{"tag": "2", "date": ["2023-07-03", "2023-07-10"], "inferred": [true, true]}},
  {{"tag": "3", "date": ["2023-07-03", "2023-07-10"], "inferred": [true, true]}},
  {{"tag": "4", "date": ["2023-07-03", "2023-07-10"], "inferred": [true, true]}}
]
```

Example 3:
Input:
```
As of 2023-08-15, patient has been managing <1>hypertension</1> for the past 10 years and started <2>metformin</2> 3 months ago.
```

Output:
```
[
  {{"tag": "1", "date": ["2013-08-15", "2023-08-15"], "inferred": [true, true]}},
  {{"tag": "2", "date": ["2023-05-15", "2023-08-15"], "inferred": [true, true]}}
]
```

Input:
```
{note}
```

Please respond with valid JSON only, no additional text. Output:
'''
            # - entity: this is the corresponding extracted entity.

        elif self.prompt_name in ['basic_info']:
            self.template = '''
You will receive an electronic health record for a patient. Your task is to extract the following basic information from the note:
 - admission_date
 - discharge_date
 - gender
 - death_date
 - birth_date
 - race
 - ethnicity
 - zip_code
 
Your output should be in JSON Dictionary format using the above as keys.
For the dates, they should be in the format "YYYY-MM-DD". If the information is not mentioned in the note, use null as value. 

---

### Example:

```
{{
  "admission_date": "2022-03-15",
  "discharge_date": "2022-03-20",
  "gender": "Male",
  "death_date": null,
  "birth_date": "1965-08-22",
  "race": "Caucasian",
  "ethnicity": "Non-Hispanic",
  "zip_code": "02115"
}}
```

---

Input:
{note}

Please respond with valid JSON only, no additional text. Output:
'''

        elif self.prompt_name in ['date_range']:
            self.template = '''
You will receive an electronic health record for a patient. Your task is extract the admission date and the discharge date of the patient.
Your output should be in JSON Array format: "[admission date, discharge date]". If this does not apply to the record provided, for example, use null to fill up the value (such as [null, null]).

---

### Example:

```
["2022-03-15", "2022-03-20"]
```

---

Input:
{note}

Please respond with valid JSON only, no additional text. Output:
'''

        elif self.prompt_name in ['norm_date']:
            self.template = '''
Given an anchor time in the form of YYYY-MM-DD, what is the date range of "{date}" when the anchor time is {anchor}?
Your answer should be given in the form of [YYYY-MM-DD, YYYY-MM-DD] representing the start and end time.

---

### Example:

```
["2118-06-02", "2118-06-14"]
```

---

Please respond with valid JSON only, no additional text. Output:
'''

        elif self.prompt_name in ['finddate_multi']:
            self.template = '''
Extract event dates for entities marked by <KEY> tags in this health record, using the contexts provided.

Output JSON list of dictionaries with:
 - tag: entity order number from KEY tags
 - date: [YYYY-MM-DD, YYYY-MM-DD] for start and end dates (use same date for single events, null for unknown)
 - inferred: [true/false, true/false] indicating if each date was inferred rather than explicitly stated

Key Rules:
- "Presenting with X day history of Y" → END = admission date, START = END minus X days, both inferred=true
- "X-day history of", "for past X days" → Calculate precise start date
- "Has been [action] for X years" → END = admission date, START = END minus X years
- Use admission date as reference for relative dates
- Consider previous note for context but prioritize current segment
- Explicitly recorded dates → inferred=false
- Chronic conditions without dates → [null, null]
- When symptoms share time reference → Apply same date range to all

Example 1:
Input:
```
Previous note (2023-07-05): Patient initially presented with chest pain.
Admission date: 2023-07-05, Discharge date: 2023-07-12
Current note: Patient presenting with a 7 day history of <1>headaches</1>, <2>sore throat</2>, and <3>cough</3>. <4>Blood tests</4> were done today.
```

Output:
```
[
  {{"tag": "1", "date": ["2023-06-28", "2023-07-05"], "inferred": [true, true]}},
  {{"tag": "2", "date": ["2023-06-28", "2023-07-05"], "inferred": [true, true]}},
  {{"tag": "3", "date": ["2023-06-28", "2023-07-05"], "inferred": [true, true]}},
  {{"tag": "4", "date": ["2023-07-05", "2023-07-05"], "inferred": [false, false]}}
]
```

Example 2:
Input:
```
Previous note (2023-01-10): No mention of hypertension.
Admission date: 2023-01-15, Discharge date: 2023-01-22
Current note: Patient has been managing <1>hypertension</1> for the past 10 years and started <2>metformin</2> 3 months ago.
```

Output:
```
[
  {{"tag": "1", "date": ["2013-01-15", "2023-01-15"], "inferred": [true, true]}},
  {{"tag": "2", "date": ["2022-10-15", "2023-01-15"], "inferred": [true, true]}}
]
```

Input:
```
Previous piece of the record (context):
{prev_note}
Admission date: {adm_date}, Discharge date: {dis_date}
Current note:
{note}
```

Please respond with valid JSON only, no additional text. Output:
'''

        elif self.prompt_name in ['json_debug']:
            self.template = '''
I have a JSON file with errors that cannot be parsed. When I tried to parse it using `demjson3.decode`, I received specific error messages. Please correct the JSON and respond with only the corrected JSON content—do not include any explanations, comments, or additional text.

---

### Examples:

Error: Unexpected character at line 3, column 15  
Input JSON:
```
{{
  "name": "John Doe,
  "age": 30,
  "hobbies": ["reading", "coding", hiking]
}}
```

Corrected JSON:
```
{{
  "name": "John Doe",
  "age": 30,
  "hobbies": ["reading", "coding", "hiking"]
}}
```

---

Error: Unexpected EOF while parsing at line 4  
Input JSON:
```
{{
  "id": 123,
  "details": {{
    "name": "Bob",
    "age": 40
  }}
```

Corrected JSON:
```
{{
  "id": 123,
  "details": {{
    "name": "Bob",
    "age": 40
  }}
}}
```

---

Error: {error_message}  
Input JSON:
{json_content}

Please respond with only the corrected JSON. Output:
'''

    def apply_template(self, inputs):

        return self.template.format(**inputs)
