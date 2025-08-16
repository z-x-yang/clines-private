# i2b2 Format Data Schema Documentation

## Overview

This document provides a comprehensive guide to the i2b2 (Informatics for Integrating Biology and the Bedside) format implementation used in this the CLINES (Clinical LLM‐based Information Extraction and Structuring Agent) project. The implementation extends the standard i2b2 OBSERVATION_FACT table structure with additional modifiers and fields specifically designed for clinical natural language processing (NLP) tasks.

## Table of Contents

1. [Standard i2b2 Fields](#standard-i2b2-fields)
2. [Project-Specific Extensions](#project-specific-extensions)
3. [Temporal Date Extraction](#temporal-date-extraction)
4. [Code System Conversion](#code-system-conversion)
5. [Modifier Types](#modifier-types)
6. [ASSERTION_STATUS Modifier](#assertion_status-modifier)
7. [RELATED Modifier](#related-modifier)
8. [Data Structure Examples](#data-structure-examples)
9. [Dataset Information](#dataset-information)
10. [Usage Guidelines](#usage-guidelines)

## Standard i2b2 Fields

Based on the official i2b2 OBSERVATION_FACT table structure, the following fields are used in this project:

| Column Name | Column Definition | Nullable | Usage in Project |
|-------------|-------------------|----------|------------------|
| **patient_num** | Encoded i2b2 patient number | NO | Patient identifier |
| **birth_date** | Patient's birth date | YES | Demographics |
| **death_date** | Patient's death date | YES | Demographics |
| **sex_cd** | Gender code | YES | Demographics |
| **race_cd** | Race code | YES | Demographics |
| **ethnicity_cd** | Ethnicity code | YES | Demographics |
| **zip_cd** | ZIP code | YES | Demographics |
| **encounter_num** | Encoded i2b2 patient visit number | NO | Visit identifier |
| **start_date** | Starting date-time of the observation (yyyy-mm-dd) | YES | Temporal information |
| **end_date** | The end date-time for the observation | YES | Temporal information |
| **concept_cd** | Code for the observation of interest (diagnoses, procedures, medications, lab tests) | NO | Primary concept identifier |
| **name_char** | Human-readable name/mention of the concept | YES | Concept text representation |
| **observation_blob** | Holds raw or miscellaneous data, often the surrounding text context | YES | Context information |
| **modifier_cd** | Code for modifier of interest (ROUTE, DOSE, etc.) | YES | Modifier type identifier |
| **instance_num** | Instance number that allows multiple modifiers for each concept | YES | Modifier instance counter |
| **valtype_cd** | Format of the concept: N=Numeric, T=Text, B=Raw Text | YES | Value type indicator |
| **tval_char** | Text value when VALTYPE_CD = "T" or comparison operator when "N" | YES | Text-based values |
| **nval_num** | Numerical value when VALTYPE_CD = "N" | YES | Numeric values |
| **valueflag_cd** | Flag for outlying or abnormal values (H=High, L=Low, A=Abnormal) | YES | Value status indicator |
| **units_cd** | Units of measurement for the value in NVAL_NUM column | YES | Measurement units |
| **unitflag_cd** | Boolean flag indicating if units were inferred | YES | Unit inference indicator |

## Project-Specific Extensions

This implementation includes additional fields beyond the standard i2b2 schema:

| Column Name | Definition | Purpose |
|-------------|------------|---------|
| **entity_index** | Index position of the entity in the source text | Entity tracking and reference |
| **code_type** | Type of coding system used (ICD10CM, LNC, CUI, RXNORM, etc.) | Code system identification |

## Temporal Date Extraction

The system automatically extracts start and end dates for all clinical entities using an LLM-based temporal reasoning approach. The `start_date` and `end_date` fields in the i2b2 format are populated based on contextual analysis of clinical text.

### Date Extraction Rules

The temporal extraction follows a comprehensive LLM-based approach following the below strategy:

| Temporal Expression | Start Date | End Date | Inferred Status |
|---------------------|------------|----------|-----------------|
| **Explicit dates** | Exact date | Same exact date | [false, false] |
| **"X days/weeks/months/years ago"** | Reference date - X | Reference date | [true, true] |
| **Current symptoms/findings** | Reference date | Reference date | [false, false] |
| **New treatments/prescriptions** | Reference date | null | [false, true] |
| **Chronic conditions (no timeframe)** | null | null | [false, false] |
| **Unknown/unclear timing** | null | null | [false, false] |

### Reference Date Priority

1. **Multi-note records**: Admission date serves as the primary temporal reference
2. **Single records**: Visit date extracted from the clinical note
3. **Related events**: Share timeframes with main associated events

### Examples

**Scenario 1 - Historical symptoms:**
- Text: "Patient presenting with a 7-day history of headaches"
- Admission: 2023-07-05
- Result: start_date="2023-06-28", end_date="2023-07-05", inferred=[true, true]

**Scenario 2 - Current findings:**
- Text: "Blood tests were done today"
- Visit: 2023-07-05
- Result: start_date="2023-07-05", end_date="2023-07-05", inferred=[false, false]

**Scenario 3 - New prescriptions:**
- Text: "Starting sertraline"
- Visit: 2023-07-05
- Result: start_date="2023-07-05", end_date=null, inferred=[false, true]

The system maintains high accuracy by considering contextual cues, temporal modifiers, and clinical workflow patterns to ensure meaningful temporal annotations for downstream analysis.

## Code System Conversion

### UMLS CUI Code Processing

The original CLINES system extracts entity codes using UMLS CUI (Concept Unique Identifier) codes. To enhance interoperability and clinical utility, this implementation includes a post-processing step that converts CUI codes to standard medical coding systems.

### Conversion Process

The conversion process utilizes the official UMLS concept mapping files as documented in the [UMLS Reference Manual](https://www.ncbi.nlm.nih.gov/books/NBK9685/table/ch03.T.concept_names_and_sources_file_mr/). The conversion follows a priority-based approach:

**Priority Order:**
1. **ICD10CM** - International Classification of Diseases, 10th Revision, Clinical Modification
2. **LNC (LOINC)** - Logical Observation Identifiers Names and Codes
3. **RXNORM** - Normalized naming system for clinical drugs
4. **ICD10PCS** - International Classification of Diseases, 10th Revision, Procedure Coding System
5. **ICD9CM** - International Classification of Diseases, 9th Revision, Clinical Modification
6. **HCPCS**
7. **CPT**
8. **SNOMEDCT_US**
6. **CUI** - Original UMLS CUI code (fallback)

### Conversion Performance

- **Overall Conversion Rate:** 42% of CUI codes were successfully converted to standard coding systems
- **Detailed Statistics:** Complete conversion statistics and analysis are available in `transformation_report.txt`
- **Fallback Handling:** CUI codes that cannot be mapped to any standard system remain as CUI codes in the `code_type` field

### Technical Implementation

The conversion process:
1. Extracts CUI codes from the original entity annotations
2. Queries the UMLS mapping tables for each priority coding system
3. Selects the first successful mapping based on priority order
4. Updates both the `concept_cd` and `code_type` fields accordingly
5. Maintains traceability through detailed logging and reporting

## Modifier Types

The project uses both standard and custom modifier types to capture comprehensive clinical information:

### Standard Modifiers

| Modifier Code | Description | Value Type | Usage |
|---------------|-------------|------------|-------|
| **@** | Default/base modifier | - | Primary entity record |
| **DOSE** | Medication dosage | N or T | Numeric values with units or text descriptions |
| **ROUTE** | Administration route | T | "PO", "IV", "IM", etc. |
| **FREQ** | Frequency of administration | T | "BID", "TID", "PRN", etc. |

### Custom Modifiers

| Modifier Code | Description | Value Type | Usage |
|---------------|-------------|------------|-------|
| **ASSERTION_STATUS** | Clinical assertion status | T | Present, Absent, Historical, etc. |
| **BODY_LOCATION** | Anatomical location | T | Specific body part or region |
| **OTHER_INFO** | Additional descriptive information | T | Adjectives and modifying terms |
| **RELATED** | Relationships to other entities | T | JSON-formatted relationship data |

## ASSERTION_STATUS Modifier

The ASSERTION_STATUS modifier captures the clinical assertion status of entities, derived from clinical NLP analysis. This modifier uses the following categories:

### Status Categories

| Status | Definition | Examples |
|--------|------------|----------|
| **Present** | Problem currently exists | "History of chest pain", "The patient has had increasing weight gain" |
| **Absent** | Problem definitely does not exist | "Patient denies pain", "Elevated enzymes have resolved" |
| **Historical** | Problem existed in past but not currently | "Patient was previously on medication X but has since discontinued it", "Past history of asthma that is currently in remission" |
| **Possible** | Problem may exist (uncertain, suspected) | "We suspect this is pneumonia", "Pneumonia unlikely" |
| **Conditional** | Problem occurs only under certain conditions | "Penicillin causes a rash", "Ativan 0.5 mg IV q4-6 hours as needed for anxiety" |
| **Hypothetical** | Problem mentioned theoretically | "If the patient were to experience chest pain, it could indicate a myocardial infarction" |
| **Notassociated** | Problem relates to someone other than patient | "Family history of prostate cancer" |

### Special Guidelines for Medications

- **Present**: Currently prescribed/taking or active prescription
- **Historical**: Previously prescribed but discontinued/completed
- **Conditional**: PRN (as needed) medications or conditional prescriptions
- **Absent**: Explicitly refused, contraindicated, or allergic
- **Possible**: Under consideration or trial basis

### Important Notes

- "Presenting with a history of X" typically means the symptom/problem is **Present**
- "X-day history of Y" usually indicates the problem Y is **Present** and has been occurring for X time period
- Only classify symptoms as **Historical** when there is clear indication the problem has resolved

## RELATED Modifier

The RELATED modifier captures clinical relationships between entities using a JSON format. Relationships are directional and follow the pattern: Entity A has relationship type X to Entity B.

### Relationship Categories

#### 1. Treatment Relationships
- **treats/treated_by**: Medication treats condition / condition is treated by medication
- **manages/managed_by**: Intervention manages condition / condition is managed by intervention
- **alleviates/alleviated_by**: Relieves symptoms / symptom is alleviated by intervention

#### 2. Causal Relationships
- **causes/caused_by**: Directly causes / is directly caused by
- **exacerbates/exacerbated_by**: Worsens condition / is worsened by
- **indicates/indicated_by**: Suggests or points to / is suggested by
- **risk_factor/at_risk_from**: Increases risk / has increased risk due to
- **complication_of/has_complication**: Is a complication / has as a complication

#### 3. Measurement Relationships
- **measures/measured_by**: Test measures parameter / parameter measured by test
- **evaluates/evaluated_by**: Assesses condition / condition assessed by
- **diagnoses/diagnosed_by**: Used to diagnose / is diagnosed using
- **monitors/monitored_by**: Tracks over time / is tracked using
- **has_value/value_of**: Entity has numerical value / is a value of entity
- **has_unit/unit_for**: Measurement has unit / is unit for measurement

#### 4. Anatomical Relationships
- **located_in/location_of**: Anatomical location / is the location for
- **part_of/has_part**: Component of larger system / has as a component
- **administered_at/site_for**: Administration site / is site for administration

#### 5. Temporal Relationships
- **precedes**: Occurs before
- **follows**: Occurs after
- **concurrent_with**: Happens simultaneously

#### 6. Clinical Relationships
- **symptom_of/has_symptom**: Symptom of condition / condition has symptom
- **finding_of/has_finding**: Clinical finding / has clinical finding
- **manifestation_of/has_manifestation**: Visible manifestation / has visible manifestation
- **has_dosage/dosage_for**: Medication and dose / is dosage for medication
- **has_frequency/frequency_for**: Medication frequency / is frequency for
- **has_route/route_for**: Administration route / is route for
- **component_of/has_component**: Part of procedure/panel / procedure/panel has component

#### 7. Default Relationship
- **related_to**: General association when specific type unclear

### JSON Format

The RELATED modifier stores relationships as JSON objects where:
- Keys are entity tags (numbers as strings)
- Values are relationship types

Example:
```json
{"2": "treated_by", "3": "concurrent_with", "5": "diagnosed_by"}
```

## Data Structure Examples

### Basic Entity Record
```csv
patient_num,encounter_num,start_date,concept_cd,name_char,observation_blob,modifier_cd,instance_num,valtype_cd,tval_char,nval_num,units_cd,unitflag_cd,entity_index,code_type
653625,6201560,,R10.9,abdominal discomfort,"Patient has abdominal discomfort...",@,1,,,,,,False,1,ICD10CM
```

### Entity with Modifiers
```csv
patient_num,encounter_num,start_date,concept_cd,name_char,observation_blob,modifier_cd,instance_num,valtype_cd,tval_char,nval_num,units_cd,unitflag_cd,entity_index,code_type
653625,6201560,,R10.9,abdominal discomfort,"Patient has abdominal discomfort...",@,1,,,,,,False,1,ICD10CM
653625,6201560,,R10.9,abdominal discomfort,"Patient has abdominal discomfort...",ASSERTION_STATUS,1,T,Present,,,,False,1,ICD10CM
653625,6201560,,R10.9,abdominal discomfort,"Patient has abdominal discomfort...",BODY_LOCATION,2,T,mid/LUQ,,,,False,1,ICD10CM
653625,6201560,,R10.9,abdominal discomfort,"Patient has abdominal discomfort...",OTHER_INFO,3,T,intermittent,,,,False,1,ICD10CM
653625,6201560,,R10.9,abdominal discomfort,"Patient has abdominal discomfort...",RELATED,4,T,"{""2"": ""concurrent_with"", ""9"": ""treated_by""}",,,False,1,ICD10CM
```

### Medication with Dosage
```csv
patient_num,encounter_num,start_date,concept_cd,name_char,observation_blob,modifier_cd,instance_num,valtype_cd,tval_char,nval_num,units_cd,unitflag_cd,entity_index,code_type
653625,6201560,,LP36596-2,oxyCODONE-acetaminophen,"Patient prescribed Percocet...",@,1,,,,,,False,46,LNC
653625,6201560,,LP36596-2,oxyCODONE-acetaminophen,"Patient prescribed Percocet...",DOSE,1,T,"[""5"", ""325""]",,"[""mg"", ""mg""]",False,46,LNC
653625,6201560,,LP36596-2,oxyCODONE-acetaminophen,"Patient prescribed Percocet...",ROUTE,2,T,PO,,,,False,46,LNC
653625,6201560,,LP36596-2,oxyCODONE-acetaminophen,"Patient prescribed Percocet...",FREQ,3,T,every 6 hours if needed,,,,False,46,LNC
653625,6201560,,LP36596-2,oxyCODONE-acetaminophen,"Patient prescribed Percocet...",ASSERTION_STATUS,4,T,Present,,,,False,46,LNC
```

## Dataset Information

### CORAL Dataset Source

The i2b2 format examples and results in this project are derived from the **CORAL (expert-Curated medical Oncology Reports to Advance Language model inference)** dataset, available at [PhysioNet](https://physionet.org/content/curated-oncology-reports/1.0/).

### Dataset Composition

- **Total Notes Processed:** 40 clinical notes from the CORAL dataset
- **File Structure:** Each CSV file corresponds to one clinical note
- **Patient Distribution:** Each note represents a different patient
- **Cancer Type Distribution:**
  - **20 Breast Cancer notes** - Files prefixed with `coral_annotated_breastca_`
  - **20 PDAC (Pancreatic Ductal Adenocarcinoma) notes** - Files prefixed with `coral_annotated_pdac_`
