# EXP-E: GPT-4o Hallucination — Case Studies

Selected representative examples per FP category, for paper Discussion §3.5.
Excerpts are PHI-redacted by a conservative regex sweep (dates/MRN/IDs); **Zongxin must manually review before public release**.

Source: `fp_judged.csv` (judge_col=`judge_category`).

## Category: `fabricated_entity`

#### 4CE / note `UPMC_Note7` / span (8990, 8999)

- **Note excerpt** (chars 8790–9040):
  > DRESS]:[REDACTED]) [REDACTED] - Completed by [REDACTED] (on ) Modify - Completed by [REDACTED] (on [REDACTED]:[REDACTED]) [REDACTED] - Refused by [REDACTED] (on [REDACTED]:[REDACTED]) [REDACTED] - Completed by [REDACTED] MD (on )"
- **Predicted**: mention=`[REDACTED]`, code=`C0376649||address`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=1.0)**: The predicted entity '[REDACTED]' is a placeholder and does not refer to an actual clinical concept present in the note excerpt. There is no real-world mention of a patient's address or related concept; the model hallucinated an entity from a redacted token.


#### 4CE / note `BCH_1` / span (4312, 4314)

- **Note excerpt** (chars 4112–4514):
  > ab, PO, daily EPINEPHrine (EpiPen 2-Pak), 0.3 mg, IM, 1time ethinyl estradiol-norethindrone (Junel Fe 1/20 oral tablet), PO, daily famotidine (Pepcid 20 mg oral tablet), 20 mg = 1 tab, PO, BID famotidine (Pepcid 20 mg oral tablet), 20 mg = 1 tab, PO, BID montelukast (Singulair 10 mg oral tablet), 10 mg = 1 tab, PO, daily spironolactone, PO Family His
- **Predicted**: mention=`PO`, code=`C1272919||oral`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=1.0)**: The predicted entity 'PO' (oral) was extracted as a standalone entity, but in the note it is only present as a route of administration for several medications and does not constitute a clinical entity on its own in this context.


#### coral_breastca / note `34` / span (12318, 12320)

- **Note excerpt** (chars 12118–12520):
  > ay language has been sent to the patient. Radiologist [REDACTED] . *****, M.D., Ph.D. <This report was electronically signed by [REDACTED] . *****, M.D., Ph.D. at *****/*****/[REDACTED] :23:13 AM> Exam Date: [DATE] Exam(s): MR breast bilateral en + un Clinical History: 33-year-old woman status post palpation-guided FNA of cervical lymph node demonstrating metastatic adenocarcinoma
- **Predicted**: mention=`AM`, code=`C1567151||antemortem diag`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=1.0)**: The predicted entity 'AM' refers to a time of day (as in '*****:23:13 AM'), not to a clinical concept such as 'antemortem diag.' There is no mention of the clinical concept in the note.


#### coral_breastca / note `36` / span (2886, 2888)

- **Note excerpt** (chars 2686–3088):
  > cancer Paternal Grandmother 35  Breast cancer Paternal Aunt diagnosed in her late 70s, mother of the 2 sisters below  Breast cancer Other Paternal Cousin x 2, they are sisters, diagnosed at 37 and 42yo G2 P2 Age at first pregnancy: 22 Age at menarche: 14 Age at menopause: 42 Previous hormone replacement therapy: NO Allergies Allergen Reactions  Penicillins Socia
- **Predicted**: mention=`37`, code=`C1856704||average age at death is 37 years`, assertion=`Notassociated`, value=`37`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=1.0)**: The number '37' in the note refers to the age at which a cousin was diagnosed with breast cancer, not to an average age at death. There is no mention or implication of 'average age at death is 37 years' in the excerpt.


#### coral_pdac / note `15` / span (8083, 8085)

- **Note excerpt** (chars 7883–8285):
  > 10E9/L Imm Gran, Left Shift 0.02 <0.1 x10E9/L Imaging Ct Abdomen /pelvis With Contrast Result Date: [DATE] CT ABDOMEN/PELVIS WITH CONTRAST *****/*****/***** 9:00 AM CLINICAL HISTORY: pt with pancreatic cancer currently on treatment. needs restaging scan COMPARISON: CT abdomen pelvis [DATE] TECHNIQUE: Following the administration of 150 cc of Omnipaque 350, contiguous 1.25-mm co
- **Predicted**: mention=`pt`, code=`C1292459||specimen from patient (specimen)`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=1.0)**: The predicted entity 'pt' is simply an abbreviation for 'patient' in the context of 'CLINICAL HISTORY: pt with pancreatic cancer', not a mention of a specimen from the patient. There is no reference to a specimen or equivalent concept in this span.


#### coral_pdac / note `5` / span (5102, 5105)

- **Note excerpt** (chars 4902–5305):
  > 699.1 The following accession numbers are related to this dose report [*****]: ***** The dose indicators for CT are the volume Computed Tomography Dose Index (CTDIvol) and the Dose Length Product (DLP), and are measured in units of mGy and mGy-cm, respectively. These indicators are not patient dose, but values generated from the CT scanner acquisition factors. Individual patient doses calculated
- **Predicted**: mention=`DLP`, code=`C3826887||cdisc sdtm device identifier parameter long name terminology`, assertion=`Present`, value=`699.1`, unit=`mGy-cm`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=1.0)**: The predicted entity links the value 699.1 to DLP, but the excerpt merely defines DLP and CTDIvol as dose indicators and does not actually report a DLP value. The number 699.1 is not explicitly associated with DLP or any other entity in this context.


## Category: `span_boundary_error`

#### 4CE / note `KUMC_2` / span (136, 153)

- **Note excerpt** (chars 0–353):
  > SURGERY ATTENDING ADMISSION NOTE [[DATE]] [PATIENT] [PATIENT] Admission Date : [[DATE]] Assessment / Plan : Principal Problem : Bowel obstruction (HCC) Chief Complaint : Abdominal pain History of Present Illness : [PATIENT] [PATIENT] is a 56 y. o. male who presents to the ED with 1 day history of abdominal pain that started this AM shortly aft
- **Predicted**: mention=`Bowel obstruction`, code=`C0021843||bowel obstruction`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.74)**: mention=`Bowel obstruction (HCC)`, code=`C0021843||bowel obstruction`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (span_boundary_error, conf=0.98)**: The predicted entity 'Bowel obstruction' is present in the note, but the gold entity includes additional context '(HCC)' as part of the span. The main error is an incomplete span, not a value or date issue.


#### 4CE / note `KUMC_5` / span (4129, 4131)

- **Note excerpt** (chars 3929–4331):
  > : NEG NEG NEG Ketones , UA Latest Range : NEG NEG 4+ (A) Bilirubin , UA Latest Range : NEG NEG NEG Protein , UA Latest Range : NEG NEG NEG Urobilinogen , UA Latest Range : NORM NORMAL NORMAL Blood , UA Latest Range : NEG NEG NEG Nitrite , UA Latest Range : NEG NEG NEG Leukocytes , UA Latest Range : NEG NEG NEG WB Cs , UA Latest Range : 0 2 / HPF 0 2 RB Cs , UA Latest Range : 0 12 / HPF 2 10 MucousU
- **Predicted**: mention=`UA`, code=`C0373521||urinalysis`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.20)**: mention=`Blood , UA`, code=`C0018965||urine blood`, assertion=`Present`, value=`NEG`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=0.95)**: The model extracted 'UA' as a standalone entity, but it is part of a longer phrase (e.g., 'Blood , UA') corresponding to a specific urinalysis result. The concept is present, but the span is too short and lacks context.


#### coral_breastca / note `21` / span (85, 98)

- **Note excerpt** (chars 0–298):
  > UCSF [REDACTED] FAMILY COMPREHENSIVE CANCER CENTER [REDACTED] Care Center [REDACTED] Second *****, [REDACTED] , [REDACTED] -
- **Predicted**: mention=`CANCER CENTER`, code=`C1513817||cancer center`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.48)**: mention=`COMPREHENSIVE CANCER CENTER`, code=`C1516764||comprehensive cancer center`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=1.0)**: The model predicted 'CANCER CENTER' (a substring) instead of the full 'COMPREHENSIVE CANCER CENTER' mention in the note. The concept is correct, but the span is too short.


#### coral_breastca / note `23` / span (11505, 11508)

- **Note excerpt** (chars 11305–11708):
  > . Recommend clinical follow up for patient-palpated lump in the lower central/slightly outer right breast, for which there is no mammographic nor sonographic correlate. If indicated, palpation-guided FNA could be pursued. Bilateral MRI of Breasts [DATE] Comparison: Prior examinations dated [DATE] (mammogram), [DATE] and [DATE] were reviewed for comparison. MRI Findings: This
- **Predicted**: mention=`FNA`, code=`C1510483||fna - fine needle aspiration`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.15)**: mention=`palpation-guided FNA`, code=`C1510483||fine-needle aspiration`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=1.0)**: The model predicted 'FNA' alone while the gold standard included 'palpation-guided FNA'. The clinical concept is correct and present, but the predicted span is too short.


#### coral_pdac / note `7` / span (9485, 9487)

- **Note excerpt** (chars 9285–9687):
  > xamined: 37 PATHOLOGIC STAGE CLASSIFICATION (pTNM, AJCC 8th Edition) TNM Descriptors: Not applicable . Primary Tumor (pT): pT2 Regional Lymph Nodes (pN): pN2 Distant Metastasis (pM): Not applicable - pM cannot be determined from the submitted specimen(s) MMR proteins all intact by IHC. I personally reviewed and interpreted the patient's relevant imaging studies in c
- **Predicted**: mention=`pM`, code=`C1269798||distant metastasis`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.09)**: mention=`Distant Metastasis (pM)`, code=`C1269798||distant metastasis`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=0.98)**: The predicted entity 'pM' is a substring of the gold entity 'Distant Metastasis (pM)' and refers to the same clinical concept, but the span is too short compared to the gold annotation.


#### coral_pdac / note `13` / span (11429, 11432)

- **Note excerpt** (chars 11229–11632):
  > ranslating into significant prolongation of life, but that treatment was not expected to be curative. As such, it would be important to carefully weigh the risks/benefits of therapy and to prioritize QoL considerations in the process. In terms of standard of care options, there are several possible chemotherapy regimens to select from for metastatic pancreatic cancer, with the choice of therapy d
- **Predicted**: mention=`QoL`, code=`C0518214||quality of life`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.17)**: mention=`quality of life (QoL) considerations`, code=`C0518214||qol`, assertion=`Present`, value=`QoL considerations`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=0.98)**: The predicted entity 'QoL' captures only the abbreviation, while the gold entity includes the full phrase 'quality of life (QoL) considerations.' The concept is correct, but the predicted span is too short.


## Category: `wrong_code`

#### 4CE / note `d34f60de6187c4ebefd6d31bcaca64630` / span (135, 142)

- **Note excerpt** (chars 0–342):
  > History and Physical - Hospital Medicine Service Patient: Name, 57 year old, Epic#: number HC#: number Chief Complaint: worsening dyspnea and fatigue History of Present Illness: Name is a 57 year old male with pAfib s/p ablation, OSA on CPAP, recent Covid (22) with worsening dyspnea and cough for the past week. Symptoms associated wit
- **Predicted**: mention=`dyspnea`, code=`C0013404||dyspnea`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.41)**: mention=`worsening dyspnea`, code=`C0853326||dyspnea exacerbated`, assertion=`Present`, value=`worsening`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (wrong_code, conf=0.95)**: The predicted entity 'dyspnea' (C0013404) overlaps with the gold entity 'worsening dyspnea' (C0853326), but the model failed to capture the exacerbation aspect, resulting in a less specific and incorrect code.


#### 4CE / note `UPMC_Note3` / span (769, 771)

- **Note excerpt** (chars 569–971):
  > s of worsening dyspnea and desaturation. Of note, he was hospitalized here at UPMC [REDACTED] from for persistent hypoxemic respiratory failure 2/2 [ALPHANUMERICID] and was discharged home on 6L o2 at rest and 9L with activity. Per Ed provider note, pt reports that upon discharge he has remained short of breath even at rest and would quickly desat upon ambulation. He reports a dry nonproductive
- **Predicted**: mention=`o2`, code=`C0030054||oxygen`, assertion=`Present`, value=`6`, unit=`L`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.40)**: mention=`oxygenator therapy (6L o2)`, code=`C0418994||oxygenator therapy`, assertion=`Present`, value=`6`, unit=`L`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (wrong_code, conf=0.95)**: The model identified the correct span for 'o2', but assigned the code for 'oxygen' (C0030054) rather than 'oxygenator therapy' (C0418994), which is the gold standard in this context.


#### coral_breastca / note `24` / span (74, 87)

- **Note excerpt** (chars 0–287):
  > ID: [REDACTED] is a 55 y.o. ***** with a recent diagnosis of early stage breast cancer, who presents in consultation to discuss treatment options and to establish care. Date of Service: [DATE] HPI: The patient has not had screening mammograms. She felt a lump in her left breas
- **Predicted**: mention=`breast cancer`, code=`C0006142||breast cancer`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.52)**: mention=`early stage breast cancer`, code=`C2986665||early-stage breast carcinoma`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_code`
- **Judge (wrong_code, conf=1.0)**: The predicted entity 'breast cancer' matches the text span and concept location, but the code is for general breast cancer (C0006142) instead of the more specific early-stage breast carcinoma (C2986665) present in the gold annotation.


#### coral_breastca / note `31` / span (97, 110)

- **Note excerpt** (chars 0–310):
  > ID: [REDACTED] is a 67 y.o. postmenopausal patient with a recent diagnosis of early stage breast cancer, who presents in consultation to discuss treatment options and to establish care. Date of Service: [DATE] HPI: The patient underwent a right breast partial mastectomy on [DATE] to remove a
- **Predicted**: mention=`breast cancer`, code=`C0006142||breast cancer`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.52)**: mention=`early stage breast cancer`, code=`C2986665||early-stage breast carcinoma`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_code`
- **Judge (wrong_code, conf=1.0)**: The predicted entity 'breast cancer' refers to the correct text span but maps it to a more general CUI (C0006142) instead of the specific 'early-stage breast carcinoma' (C2986665) mentioned in the note.


#### coral_pdac / note `5` / span (10753, 10759)

- **Note excerpt** (chars 10553–10901):
  > Plan: I'm very concerned about her imaging studies. The lesions are too small to evaluate further at this point. We will repeat her scans in 2 months. If indicated, we will seek a confirmatory biopsy. I spent 20 minutes in face-to-face consultation with the patient and her husband today going over all aspects of her care and management.
- **Predicted**: mention=`biopsy`, code=`C0005558||biopsy`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.32)**: mention=`confirmatory biopsy`, code=`C5203961||biopsy with histologic confirmation`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (wrong_code, conf=0.95)**: The predicted entity 'biopsy' (C0005558) overlaps with the gold entity 'confirmatory biopsy' (C5203961) and refers to the same event, but the predicted code is less specific than the gold standard. The mention and assertion are otherwise correct.


#### coral_pdac / note `7` / span (9257, 9259)

- **Note excerpt** (chars 9057–9459):
  > : 0.7cm Closest Margin: Uncinate (retroperitoneal / superior mesenteric artery) LYMPH NODES Regional Lymph Nodes: Lymph nodes submitted or found Number of Lymph Nodes Involved: 11 Number of Lymph Nodes Examined: 37 PATHOLOGIC STAGE CLASSIFICATION (pTNM, AJCC 8th Edition) TNM Descriptors: Not applicable . Primary Tumor (pT): pT2 Regional Lymph Nodes (pN):
- **Predicted**: mention=`11`, code=`C1302557||number of non-regional lymph nodes involved`, assertion=`Present`, value=`11`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (wrong_code, conf=1.0)**: The note explicitly states 'Number of Lymph Nodes Involved: 11', but the predicted code is for 'number of non-regional lymph nodes involved'. The excerpt is referring to regional lymph nodes, so the code is incorrect.


## Category: `wrong_assertion`

#### 4CE / note `d30982c684512d4f0b6fd79836539d9ac` / span (664, 666)

- **Note excerpt** (chars 464–866):
  > eck pain and feels "fuzzy" and he has been having increasing difficulty getting himself up. Today he had a fall, struck his head and was not able to get up, prompting him to call EMS and come to the ED today. Name says he was in his usual state of health last week. He and wife visited her family up in city for event, came back to town the Tuesday after event and he felt fine. Then 3-4 days ago he
- **Predicted**: mention=`ED`, code=`C0562508||emergency department`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`ED`, code=`C0562508||emergency department`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=1.0)**: The mention, code, and span are all correct, but the model assigned 'Notassociated' assertion when the context clearly indicates the patient came to the emergency department (ED) due to a fall, so 'Present' is correct.


#### 4CE / note `UPMC_Note7` / span (2709, 2712)

- **Note excerpt** (chars 2509–2912):
  > crine: Negative. Immunologic: Negative. Musculoskeletal: Negative. Integumentary: Negative. Neurologic: Negative. All other systems are negative Allergies Allergies NKA Home/Transfer/Inpatient Medications Home Medications (from 'Document Medication by Hx') albuterol (Ventolin HFA 90 mcg/inh inhalation aerosol) 2 Puff(s) Every 6 Hours PRN Inhalati
- **Predicted**: mention=`NKA`, code=`C0262580||no known allergies`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`NKA`, code=`C0262580||no known allergies`, assertion=`Present`, value=`NKA`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=1.0)**: The mention 'NKA' (No Known Allergies) is correctly identified with the right CUI, but its assertion status is marked as 'Absent' instead of 'Present', which is incorrect given the context.


#### coral_breastca / note `23` / span (5162, 5164)

- **Note excerpt** (chars 4962–5364):
  > re-meds for future scans  Contrast [Gadolinium-Containing Contrast Media] Itching Patient not sure if she is allergic to GAD. Will add to allergy list: She is allergic to NON-Ionic Contrast (CT,etc.) She takes pre - meds for this.  Hydrocodone-Acetaminophen Nausea Only  Penicillins Unknown  Pollen Extracts Runny nose and dizziness PAST, FAMILY, and SOCIAL HISTORY P
- **Predicted**: mention=`CT`, code=`C0009778||ct`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`CT`, code=`C0009778||ct`, assertion=`Hypothetical`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=1.0)**: The mention and code for 'CT' are correct, but the assertion status is marked as 'Present' when the context indicates it should be 'Hypothetical' (allergy list context: 'She is allergic to NON-Ionic Contrast (CT,etc.)').


#### coral_breastca / note `37` / span (3688, 3690)

- **Note excerpt** (chars 3488–3890):
  > History Smoking Status  Former Smoker  Packs/day: 0.20  Years: 10.00  Start date: [DATE]  Quit date: [DATE] Smokeless Tobacco  Never Used History Alcohol Use No Comment: Previously drank 4 a week Family History Problem Relation Name Age of Onset  Breast cancer Mother  Breast cancer Other  Breast cancer Other Review of Sys
- **Predicted**: mention=`No`, code=`C0457801||does not drink alcohol`, assertion=`Absent`, value=`No`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`No`, code=`C0457801||does not drink alcohol`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=1.0)**: The note states 'Alcohol Use No', which indicates the patient does not currently drink alcohol. The model assigned assertion 'Absent', but the gold label is 'Present', showing a mismatch in assertion classification.


#### coral_pdac / note `16` / span (270, 272)

- **Note excerpt** (chars 70–472):
  > male with locally advanced pancreatic adenocarcinoma. ATTENDING: [REDACTED] , MD Primary Care Provider: [REDACTED] , MD HISTORY OF PRESENT ILLNESS: October 2017: abd pain. Seen in ED sent home. A first endoscopy showed no abnormalities in the stomach or duodenum. Ultrasound showed pancreatic tail lesion. 6//18: CT scan performed in December 2017 showed locally advanced
- **Predicted**: mention=`ED`, code=`C0562508||emergency department`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`ED`, code=`C0562508||emergency department`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=1.0)**: The mention, code, and span are correct, but the assertion status should be 'Present' as the patient was seen in the ED, not 'Notassociated.'


#### coral_pdac / note `15` / span (4251, 4255)

- **Note excerpt** (chars 4051–4455):
  > Current Medications Current Outpatient Medications Medication Sig Dispense Refill  acetaminophen (TYLENOL EXTRA STRENGTH) 500 mg tablet Take 500 mg by mouth every 6 (six) hours as needed for Pain.  bimatoprost (LUMIGAN) 0.01 % DROPSOLN Place 1 drop into both eyes Daily.  calcium-vitamin D 500-125 mg-unit tablet Take 1 tablet (500 mg total) by mouth Daily.  cholecalciferol, vi
- **Predicted**: mention=`Pain`, code=`C0518090||pain`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`Pain`, code=`C0518090||pain`, assertion=`Possible`, value=`Pain`, unit=`nan`, begin_date=`[DATE]`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=1.0)**: The model labeled the assertion status as 'Conditional' when the gold standard marked it as 'Possible.' The mention, code, and span are all correct; only the assertion is mismatched.


## Category: `wrong_value_or_date`

#### 4CE / note `d54bcf6fe1fa225b13277b3b115fdcc3d` / span (7040, 7042)

- **Note excerpt** (chars 6840–7242):
  > igarettes Quit date: 1999 Years since quitting: 23.9 • Smokeless tobacco: Former Substance Use Topics • Alcohol use: Yes • Drug use: Not on file Lives in city w/ husband and children Objective BP 147/85 | Pulse 74 | Temp 36.5 °C (97.7 °F) (Oral) | Resp 22 | SpO2 99% Physical Exam: Constitutional: Does not appear to be in distress. Vital Signs reviewed. HEENT: Normocephalic, atraumatic,
- **Predicted**: mention=`BP`, code=`C1271104||blood pressure`, assertion=`Present`, value=`147/85`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`BP`, code=`C1271104||blood pressure`, assertion=`Present`, value=`147/85`, unit=`mmHg`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value_or_date, conf=0.98)**: The model correctly identified blood pressure and its value, but failed to extract the unit 'mmHg' which is standard for blood pressure and present in the gold annotation.


#### 4CE / note `report04` / span (1766, 1768)

- **Note excerpt** (chars 1566–1968):
  > r) have exhibited similar symptoms. He is not vaccinated against COVID-19. He denies abdominal pain, nausea, vomiting, constipation, diarrhea and pain with urination. In the ED, Temp: 38.0, HR: 98, RR: 20, BP: 123/70, and SpO2: 94% on 6 L. COVID-19 PCR was (+), indicating active infection. VBG 7.45/33. WBC 6.2. CMP unremarkable. BMP within normal limits and Trops 14, <6. CRP elevated at 10.2. D-di
- **Predicted**: mention=`RR`, code=`C0231832||respiratory rate`, assertion=`Present`, value=`20`, unit=`breaths/min`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`RR`, code=`C0231832||respiratory rate`, assertion=`Present`, value=`20`, unit=`breaths/min`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value_or_date, conf=0.95)**: The predicted entity matches the mention, code, and assertion, but the model supplied specific dates ([DATE]) that are not present in the note excerpt, while the gold entity left begin_date and end_date blank.


#### coral_breastca / note `36` / span (3237, 3240)

- **Note excerpt** (chars 3037–3440):
  > s Allergen Reactions  Penicillins Social History Social History Narrative Divorced, lives alone G2P2, 36 and 25 year old sons Works as a [REDACTED] in the [REDACTED] LMP age 42 at the time of her divorce No HRT Current Outpatient Prescriptions:  cholecalciferol, vitamin D3, (VITAMIN D3) 2,000 unit CAP capsule, Take by mouth., Disp: , Rfl: Review of
- **Predicted**: mention=`LMP`, code=`C0425932||last menstrual period`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`LMP`, code=`C0425932||last menstrual period`, assertion=`Present`, value=`at age 42`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value_or_date, conf=1.0)**: The predicted entity fails to capture the value 'at age 42', which is present in the gold annotation. The mention, code, and assertion are otherwise correct.


#### coral_breastca / note `35` / span (6349, 6355)

- **Note excerpt** (chars 6149–6555):
  > left breast reveals a 5 x 5.5 cm mass that extends to underneath the nipple, but originates at 12 o'clock. She has a 1 cm palpable left axillary lymph node. CARDIAC: Her cardiac exam is without murmur or gallops. ABDOMEN: Her abdomen is soft and nontender, without hepatosplenomegaly. EXTREMITIES: Her extremities reveal no edema. In summary, [REDACTED] is a 59-year-old woman with a new dia
- **Predicted**: mention=`murmur`, code=`C0018808||heart murmur`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`murmur`, code=`C0018808||heart murmur`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value_or_date, conf=1.0)**: The predicted entity matches the mention, code, and assertion status, but the date fields are missing in the prediction whereas the gold annotation specifies a date. This is a value/date mismatch.


#### coral_pdac / note `10` / span (5821, 5823)

- **Note excerpt** (chars 5621–6023):
  > normal. Judgment and thought content normal. Relevant Diagnostic Studies: Lab results: I personally reviewed and interpreted each of the patient's relevant lab tests as outlined [DATE] Na 130 K 3.8 Cl 92 Cr 0.92 AST 28 ALT 29 Tbili 1.0 Alk phos 67 WBC 8.8 Hgb 14.4 Plt 286 [DATE]: CA 19-9: 13737 Radiology: I personally reviewed and interpreted each of the patient
- **Predicted**: mention=`Na`, code=`C0337443||sodium`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`sodium (Na)`, code=`C0337443||sodium`, assertion=`Present`, value=`130`, unit=`mmol/L`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value_or_date, conf=1.0)**: The predicted entity correctly identifies sodium (Na) and its dates, but omits the associated value (130) and unit (mmol/L), which are present in the note and gold annotation.


#### coral_pdac / note `13` / span (7287, 7293)

- **Note excerpt** (chars 7087–7493):
  > .9 cm. Peritoneum: No ascites Bladder: Distended Reproductive organs: Unremarkable Bones: Similar multilevel spondylosis. Similar degenerative changes of the hips, sacroiliac joints, and pelvis. Extraperitoneal soft tissues: Unremarkable Lines/drains/medical devices: None IMPRESSION: 1. Compared to [DATE], increased size of the primary malignancy centered at the pancreaticodu
- **Predicted**: mention=`pelvis`, code=`C0153663||pelvis`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`pelvis`, code=`C0153663||pelvis`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value_or_date, conf=1.0)**: The predicted entity correctly identifies the mention, code, and assertion, but omits the date present in the gold annotation. This is an error of missing value/date information.

