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
- **Judge (fabricated_entity, conf=1.0)**: The predicted entity '[REDACTED]' is a template placeholder and does not refer to an actual clinical concept present in the note excerpt.


#### 4CE / note `report06` / span (11854, 11857)

- **Note excerpt** (chars 11654–12057):
  > anterior of body was examined). Dignicare in place; contents appear dark brown. Urinary catheter in place; contents appear dark yellow. PERTINENT LAB RESULTS ABG (Brief) Results from last 7 days Lab [REDACTED] 1749 [REDACTED] 1623 [REDACTED] 1220 [REDACTED] 1043 [REDACTED] 0534 PHABG 7.08* 7.04* 7.10* 7.10* 7.17* PCO2ABG 57* 49* 49* 60* 54* PO2ABG 61* 61* 75* 57* 63* HCO3ABG 16.1* 12.6* 14.8* 18.1* 18.6* LACTATEABG
- **Predicted**: mention=`Lab`, code=`C0022877||laboratory`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=0.99)**: The predicted entity 'Lab' is not a clinical concept actually mentioned in the note; it is just a section header or label, not a clinical entity. The model fabricated a concept by extracting a generic label.


#### coral_breastca / note `34` / span (12318, 12320)

- **Note excerpt** (chars 12118–12520):
  > ay language has been sent to the patient. Radiologist [REDACTED] . *****, M.D., Ph.D. <This report was electronically signed by [REDACTED] . *****, M.D., Ph.D. at *****/*****/[REDACTED] :23:13 AM> Exam Date: [DATE] Exam(s): MR breast bilateral en + un Clinical History: 33-year-old woman status post palpation-guided FNA of cervical lymph node demonstrating metastatic adenocarcinoma
- **Predicted**: mention=`AM`, code=`C1567151||antemortem diag`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=0.99)**: The predicted entity 'AM' mapped to 'antemortem diag' is not present as a clinical concept in the note; 'AM' here refers to a timestamp and not a diagnosis or clinical entity.


#### coral_breastca / note `37` / span (1929, 1932)

- **Note excerpt** (chars 1729–2132):
  > there is a 9 mm oval mass with smooth margins and dark internal septation in the upper outer right breast. Findings are classic for fibroadenoma. There was no abnormal areas of enhancement or other MRI features of malignancy on the right. In the LEFT breast, there is a 2.5 cm x 2.2 cm x 2.3 cm oval mass with irregular margins and heterogeneous enhancement in the lower outer left breast. There is
- **Predicted**: mention=`MRI`, code=`C1552358||magnetic resonance imaging`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=0.09)**: mention=`other MRI features of malignancy`, code=`C0006826||malignancy`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `span_boundary_error`
- **Judge (fabricated_entity, conf=0.98)**: The predicted entity 'MRI' as a clinical concept is not actually mentioned as a finding or procedure in the note; 'MRI' appears only as part of the phrase 'other MRI features of malignancy,' which is not a true mention of the imaging itself. The model fabricated a clinical entity.


#### coral_pdac / note `15` / span (8083, 8085)

- **Note excerpt** (chars 7883–8285):
  > 10E9/L Imm Gran, Left Shift 0.02 <0.1 x10E9/L Imaging Ct Abdomen /pelvis With Contrast Result Date: [DATE] CT ABDOMEN/PELVIS WITH CONTRAST *****/*****/***** 9:00 AM CLINICAL HISTORY: pt with pancreatic cancer currently on treatment. needs restaging scan COMPARISON: CT abdomen pelvis [DATE] TECHNIQUE: Following the administration of 150 cc of Omnipaque 350, contiguous 1.25-mm co
- **Predicted**: mention=`pt`, code=`C1292459||specimen from patient (specimen)`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=0.99)**: The predicted entity 'specimen from patient (specimen)' is not present or implied anywhere in the note; 'pt' refers to the patient, not to a specimen. The model fabricated a specimen entity.


#### coral_pdac / note `10` / span (1069, 1077)

- **Note excerpt** (chars 869–1277):
  > management. (#pan3a) Left adrenal nodule versus retroperitoneal lymph node [DATE]: EGD/EUS: 38mm mass in the pancreatic body, lymphadenopathy noted in body region FNA/FNB Path: Strata pending [DATE]: CT Chest: a 3.7cm ill defined low density pancreatic mass and 1.4cm hypoattenuating liver mass in the inferior anterior right lobe. [DATE]: CA 19-9: 13,737 [DATE]: Cs with surgery, *****: Rec
- **Predicted**: mention=`[DATE]`, code=`C2239674||march11 gene`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (fabricated_entity, conf=0.99)**: The predicted entity is 'march11 gene' (C2239674), which is not mentioned or implied anywhere in the note. The date '[DATE]' refers to a CT scan, not a gene. The model fabricated a gene entity out of thin air.


## Category: `span_boundary_error`

#### 4CE / note `d34f60de6187c4ebefd6d31bcaca64630` / span (135, 142)

- **Note excerpt** (chars 0–342):
  > History and Physical - Hospital Medicine Service Patient: Name, 57 year old, Epic#: number HC#: number Chief Complaint: worsening dyspnea and fatigue History of Present Illness: Name is a 57 year old male with pAfib s/p ablation, OSA on CPAP, recent Covid (22) with worsening dyspnea and cough for the past week. Symptoms associated wit
- **Predicted**: mention=`dyspnea`, code=`C0013404||dyspnea`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.41)**: mention=`worsening dyspnea`, code=`C0853326||dyspnea exacerbated`, assertion=`Present`, value=`worsening`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=0.95)**: The predicted entity 'dyspnea' captures the correct clinical concept, but the span misses the 'worsening' modifier present in the gold annotation. The CUI difference is due to this modifier, but since the main concept is correct, this is primarily a span boundary error.


#### 4CE / note `KUMC_2` / span (136, 153)

- **Note excerpt** (chars 0–353):
  > SURGERY ATTENDING ADMISSION NOTE [[DATE]] [PATIENT] [PATIENT] Admission Date : [[DATE]] Assessment / Plan : Principal Problem : Bowel obstruction (HCC) Chief Complaint : Abdominal pain History of Present Illness : [PATIENT] [PATIENT] is a 56 y. o. male who presents to the ED with 1 day history of abdominal pain that started this AM shortly aft
- **Predicted**: mention=`Bowel obstruction`, code=`C0021843||bowel obstruction`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.74)**: mention=`Bowel obstruction (HCC)`, code=`C0021843||bowel obstruction`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (span_boundary_error, conf=0.97)**: The predicted entity 'Bowel obstruction' is correct in concept and assertion, but the span omits the parenthetical '(HCC)' present in the gold annotation. The underlying CUI is correct, so this is a span boundary error.


#### coral_breastca / note `21` / span (85, 98)

- **Note excerpt** (chars 0–298):
  > UCSF [REDACTED] FAMILY COMPREHENSIVE CANCER CENTER [REDACTED] Care Center [REDACTED] Second *****, [REDACTED] , [REDACTED] -
- **Predicted**: mention=`CANCER CENTER`, code=`C1513817||cancer center`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.48)**: mention=`COMPREHENSIVE CANCER CENTER`, code=`C1516764||comprehensive cancer center`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=0.97)**: The predicted entity 'CANCER CENTER' is a substring of 'COMPREHENSIVE CANCER CENTER', which is the correct full mention. The CUI is appropriate for the predicted text, but the span boundaries are too short.


#### coral_breastca / note `32` / span (3479, 3481)

- **Note excerpt** (chars 3279–3681):
  > cy, upper central right breast measuring 2.2 cm with 0.4 cm anterior satellite lesion. Also, findings suspicious for additional ductal disease and disease within the nipple. Prominent right axillary LN. Left breast: Negative [DATE]: US axilla right: There is an enlarged LN measuring 0.7 x 0.7 cm in the right axilla, at approximately 10:00, 14 cm from nipple. Biopsy findings: Metastatic carcinom
- **Predicted**: mention=`LN`, code=`C0024204||lymph node`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=0.18)**: mention=`axillary LN`, code=`C0729594||axillary lymph node`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=0.96)**: The predicted entity 'LN' is part of the correct mention 'axillary LN'; the concept is correct and the difference is only in the span boundaries.


#### coral_pdac / note `7` / span (9485, 9487)

- **Note excerpt** (chars 9285–9687):
  > xamined: 37 PATHOLOGIC STAGE CLASSIFICATION (pTNM, AJCC 8th Edition) TNM Descriptors: Not applicable . Primary Tumor (pT): pT2 Regional Lymph Nodes (pN): pN2 Distant Metastasis (pM): Not applicable - pM cannot be determined from the submitted specimen(s) MMR proteins all intact by IHC. I personally reviewed and interpreted the patient's relevant imaging studies in c
- **Predicted**: mention=`pM`, code=`C1269798||distant metastasis`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.09)**: mention=`Distant Metastasis (pM)`, code=`C1269798||distant metastasis`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=0.97)**: The predicted span 'pM' is a subset of the gold entity 'Distant Metastasis (pM)', referring to the same clinical concept (distant metastasis, pM); only the span is too short.


#### coral_pdac / note `13` / span (11429, 11432)

- **Note excerpt** (chars 11229–11632):
  > ranslating into significant prolongation of life, but that treatment was not expected to be curative. As such, it would be important to carefully weigh the risks/benefits of therapy and to prioritize QoL considerations in the process. In terms of standard of care options, there are several possible chemotherapy regimens to select from for metastatic pancreatic cancer, with the choice of therapy d
- **Predicted**: mention=`QoL`, code=`C0518214||quality of life`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.17)**: mention=`quality of life (QoL) considerations`, code=`C0518214||qol`, assertion=`Present`, value=`QoL considerations`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `span_boundary_error`
- **Judge (span_boundary_error, conf=0.97)**: The model correctly identified the concept 'quality of life' (QoL) and its CUI, but the predicted span is too short, only capturing 'QoL' instead of the full phrase 'quality of life (QoL) considerations'. The underlying concept is correct, so this is a span boundary error.


## Category: `wrong_code`

#### 4CE / note `UPMC_Note3` / span (769, 771)

- **Note excerpt** (chars 569–971):
  > s of worsening dyspnea and desaturation. Of note, he was hospitalized here at UPMC [REDACTED] from for persistent hypoxemic respiratory failure 2/2 [ALPHANUMERICID] and was discharged home on 6L o2 at rest and 9L with activity. Per Ed provider note, pt reports that upon discharge he has remained short of breath even at rest and would quickly desat upon ambulation. He reports a dry nonproductive
- **Predicted**: mention=`o2`, code=`C0030054||oxygen`, assertion=`Present`, value=`6`, unit=`L`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.40)**: mention=`oxygenator therapy (6L o2)`, code=`C0418994||oxygenator therapy`, assertion=`Present`, value=`6`, unit=`L`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (wrong_code, conf=0.97)**: The predicted span 'o2' refers to oxygen (C0030054), but the gold entity is 'oxygenator therapy' (C0418994). The mention text is overlapping but the CUIs are not equivalent; this is a concept coding error.


#### 4CE / note `d30982c684512d4f0b6fd79836539d9ac` / span (9428, 9430)

- **Note excerpt** (chars 9228–9630):
  > , and zetia. - HTN: BP stable, continue HCTZ, losartan and propranolol - GERD: H2 and PPI per home regimen - OSA: CPAP Additional Conditions Present: - CKD3: stable at baseline, follow daily - Low mg: replaced, recheck in AM - Nutrition: Diabetic diet - PT/OT: consulted Code Status: FULL CODE, discussed with patient on admission. VTE Prophylaxis: SQH Disposition: Admit patient with weakness
- **Predicted**: mention=`mg`, code=`C0373675||magnesium`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.33)**: mention=`Low mg`, code=`C0151723||hypomagnesemia`, assertion=`Present`, value=`Low mg`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (wrong_code, conf=0.97)**: The predicted span 'mg' refers to magnesium (C0373675), but the note states 'Low mg', which refers to hypomagnesemia (C0151723). The model extracted only the chemical element, not the clinical condition, and mapped to the wrong CUI.


#### coral_breastca / note `31` / span (97, 110)

- **Note excerpt** (chars 0–310):
  > ID: [REDACTED] is a 67 y.o. postmenopausal patient with a recent diagnosis of early stage breast cancer, who presents in consultation to discuss treatment options and to establish care. Date of Service: [DATE] HPI: The patient underwent a right breast partial mastectomy on [DATE] to remove a
- **Predicted**: mention=`breast cancer`, code=`C0006142||breast cancer`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.52)**: mention=`early stage breast cancer`, code=`C2986665||early-stage breast carcinoma`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_code`
- **Judge (wrong_code, conf=0.97)**: The predicted span ('breast cancer') correctly identifies the presence of cancer, but the gold standard is 'early stage breast cancer' with a more specific CUI (early-stage breast carcinoma). The model mapped to a less specific code, which is a wrong_code error.


#### coral_breastca / note `36` / span (2886, 2888)

- **Note excerpt** (chars 2686–3088):
  > cancer Paternal Grandmother 35  Breast cancer Paternal Aunt diagnosed in her late 70s, mother of the 2 sisters below  Breast cancer Other Paternal Cousin x 2, they are sisters, diagnosed at 37 and 42yo G2 P2 Age at first pregnancy: 22 Age at menarche: 14 Age at menopause: 42 Previous hormone replacement therapy: NO Allergies Allergen Reactions  Penicillins Socia
- **Predicted**: mention=`37`, code=`C1856704||average age at death is 37 years`, assertion=`Notassociated`, value=`37`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`
- **Judge (wrong_code, conf=0.98)**: The number '37' in the note refers to the age at breast cancer diagnosis of a cousin, not to 'average age at death is 37 years.' The model mapped the correct span but to a completely wrong CUI.


#### coral_pdac / note `5` / span (10753, 10759)

- **Note excerpt** (chars 10553–10901):
  > Plan: I'm very concerned about her imaging studies. The lesions are too small to evaluate further at this point. We will repeat her scans in 2 months. If indicated, we will seek a confirmatory biopsy. I spent 20 minutes in face-to-face consultation with the patient and her husband today going over all aspects of her care and management.
- **Predicted**: mention=`biopsy`, code=`C0005558||biopsy`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.32)**: mention=`confirmatory biopsy`, code=`C5203961||biopsy with histologic confirmation`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`
- **Judge (wrong_code, conf=0.92)**: The predicted span 'biopsy' is a substring of the gold 'confirmatory biopsy', but the predicted code is for generic biopsy (C0005558) while the gold specifies 'biopsy with histologic confirmation' (C5203961). The code mismatch is more material than the span error.


#### coral_pdac / note `9` / span (18400, 18402)

- **Note excerpt** (chars 18200–18602):
  > -1L NS, 12mg PO dexamethasone, prn Zofran, ativan on D3 -omit D3 Fulphila given ANC >20 today -Note that pt's CA 19-9 jumped in the setting of colitis. Improving now -Plan for scans again after C8, monthly CA 19-9 # Diarrhea: Resolved though exacerbated by certain foods, bl June 14 soft bm. CT [DATE] with evidence of colitis. --stopped irinotecan with C3. --couseled regarding BRAT
- **Predicted**: mention=`C8`, code=`C0429468||anovular cycle`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`C8`, code=`C0429468||anovular cycle`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`after [DATE]`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_code, conf=0.99)**: In this context, 'C8' refers to cycle 8 of chemotherapy, not 'anovular cycle'; the code is incorrect, as the mention is correctly identified but mapped to the wrong clinical concept.


## Category: `wrong_assertion`

#### 4CE / note `d30982c684512d4f0b6fd79836539d9ac` / span (664, 666)

- **Note excerpt** (chars 464–866):
  > eck pain and feels "fuzzy" and he has been having increasing difficulty getting himself up. Today he had a fall, struck his head and was not able to get up, prompting him to call EMS and come to the ED today. Name says he was in his usual state of health last week. He and wife visited her family up in city for event, came back to town the Tuesday after event and he felt fine. Then 3-4 days ago he
- **Predicted**: mention=`ED`, code=`C0562508||emergency department`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`ED`, code=`C0562508||emergency department`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=0.99)**: The mention, code, and span are correct, but the assertion status is incorrect: the note clearly indicates the patient came to the ED today, so 'Present' is correct, not 'Notassociated'.


#### 4CE / note `UPMC_Note7` / span (2709, 2712)

- **Note excerpt** (chars 2509–2912):
  > crine: Negative. Immunologic: Negative. Musculoskeletal: Negative. Integumentary: Negative. Neurologic: Negative. All other systems are negative Allergies Allergies NKA Home/Transfer/Inpatient Medications Home Medications (from 'Document Medication by Hx') albuterol (Ventolin HFA 90 mcg/inh inhalation aerosol) 2 Puff(s) Every 6 Hours PRN Inhalati
- **Predicted**: mention=`NKA`, code=`C0262580||no known allergies`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`NKA`, code=`C0262580||no known allergies`, assertion=`Present`, value=`NKA`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=0.99)**: The note states 'NKA' (no known allergies), which should be marked as Present, but the prediction labeled it Absent. Mention and code are correct, but the assertion status is wrong.


#### coral_breastca / note `37` / span (3688, 3690)

- **Note excerpt** (chars 3488–3890):
  > History Smoking Status  Former Smoker  Packs/day: 0.20  Years: 10.00  Start date: [DATE]  Quit date: [DATE] Smokeless Tobacco  Never Used History Alcohol Use No Comment: Previously drank 4 a week Family History Problem Relation Name Age of Onset  Breast cancer Mother  Breast cancer Other  Breast cancer Other Review of Sys
- **Predicted**: mention=`No`, code=`C0457801||does not drink alcohol`, assertion=`Absent`, value=`No`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`No`, code=`C0457801||does not drink alcohol`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=0.99)**: The note says 'Alcohol Use No', which is interpreted as the patient does not drink alcohol (assertion should be Present for 'does not drink alcohol'). The model marked assertion as Absent, which is incorrect.


#### coral_breastca / note `23` / span (5162, 5164)

- **Note excerpt** (chars 4962–5364):
  > re-meds for future scans  Contrast [Gadolinium-Containing Contrast Media] Itching Patient not sure if she is allergic to GAD. Will add to allergy list: She is allergic to NON-Ionic Contrast (CT,etc.) She takes pre - meds for this.  Hydrocodone-Acetaminophen Nausea Only  Penicillins Unknown  Pollen Extracts Runny nose and dizziness PAST, FAMILY, and SOCIAL HISTORY P
- **Predicted**: mention=`CT`, code=`C0009778||ct`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`CT`, code=`C0009778||ct`, assertion=`Hypothetical`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=0.98)**: The note discusses adding 'NON-Ionic Contrast (CT, etc.)' to the allergy list, which is a hypothetical/planned context rather than a present assertion. The model labeled 'CT' as Present instead of Hypothetical.


#### coral_pdac / note `16` / span (270, 272)

- **Note excerpt** (chars 70–472):
  > male with locally advanced pancreatic adenocarcinoma. ATTENDING: [REDACTED] , MD Primary Care Provider: [REDACTED] , MD HISTORY OF PRESENT ILLNESS: October 2017: abd pain. Seen in ED sent home. A first endoscopy showed no abnormalities in the stomach or duodenum. Ultrasound showed pancreatic tail lesion. 6//18: CT scan performed in December 2017 showed locally advanced
- **Predicted**: mention=`ED`, code=`C0562508||emergency department`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`ED`, code=`C0562508||emergency department`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=0.99)**: The mention, code, and span for 'ED' (emergency department) are correct, but the assertion status is misclassified as 'Notassociated' instead of 'Present' as the note states the patient was seen in the ED.


#### coral_pdac / note `15` / span (4251, 4255)

- **Note excerpt** (chars 4051–4455):
  > Current Medications Current Outpatient Medications Medication Sig Dispense Refill  acetaminophen (TYLENOL EXTRA STRENGTH) 500 mg tablet Take 500 mg by mouth every 6 (six) hours as needed for Pain.  bimatoprost (LUMIGAN) 0.01 % DROPSOLN Place 1 drop into both eyes Daily.  calcium-vitamin D 500-125 mg-unit tablet Take 1 tablet (500 mg total) by mouth Daily.  cholecalciferol, vi
- **Predicted**: mention=`Pain`, code=`C0518090||pain`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`Pain`, code=`C0518090||pain`, assertion=`Possible`, value=`Pain`, unit=`nan`, begin_date=`[DATE]`, end_date=`nan`
- **Rule category**: `wrong_assertion`
- **Judge (wrong_assertion, conf=0.95)**: The mention and code are correct, but the assertion status is Conditional in the prediction and Possible in the gold standard. The note describes the medication as 'as needed for Pain', which is more aligned with Possible than Conditional.


## Category: `wrong_value`

#### 4CE / note `UPMC_Note1` / span (5579, 5581)

- **Note excerpt** (chars 5379–5781):
  > e Labs (ED Visit) AST |-- pH |-- 7.49 \ 13.2 / 133 | 97 | 13 / Ca |-- 9.2 ALT |-- INR |-- 1.1 pCO2 |-- 30 8.9 |--------| 119 ------- |------- |--------| 115 Mg |-- 1.5 TBili |-- PTT |-- 37.9 pO2 |-- 54 / 39.0 \ 3.5 | 25 | 0.9 \ Phos |-- AlkP |-- Anti-Xa |-- HCO3 |-- 23 gGTP |-- Additional Labs (Labs mor
- **Predicted**: mention=`Mg`, code=`C0373675||magnesium`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`Mg`, code=`C0373675||magnesium`, assertion=`Present`, value=`1.5`, unit=`mg/dL`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value, conf=0.98)**: The note clearly shows 'Mg |-- 1.5', so the correct value is 1.5. The model failed to extract this value, leaving it as nan, which is a genuine value extraction error.


#### 4CE / note `KUMC_6` / span (2198, 2201)

- **Note excerpt** (chars 1998–2401):
  > n regards to his • Hypertension [[DATE]] Follows with [xxxxx]. Goal SBP <130. • CAD (coronary artery disease) [[DATE]] • Hemodialysis status [[DATE]] • Mixed hyperlipidemia [[DATE]] Last FLP ( [[DATE]] ) : 116 / 103 / 37 / 63 (improved from [[DATE]] ) • S / P gastric bypass [[DATE]] [[DATE]] at Heartland Hospital ( [XXXXX] ) Patient ordered to receive monthly Vitamin B 12 inje
- **Predicted**: mention=`FLP`, code=`C0430044||fasting lipid profile`, assertion=`Present`, value=`FLP`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`FLP`, code=`C0430044||fasting lipid profile`, assertion=`Present`, value=`116 / 103 / 37 / 63`, unit=`mg/dL`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value, conf=0.99)**: The note provides the actual fasting lipid profile values as '116 / 103 / 37 / 63', but the model filled 'FLP' as the value, which is incorrect and a clear value extraction error.


#### coral_breastca / note `36` / span (3642, 3644)

- **Note excerpt** (chars 3442–3844):
  > ystems - All other systems were reviewed and are negative except that outlined above. BP 132/85 | Pulse 69 | Temp 36.5 C (97.7 F) (Oral) | Resp 16 | Ht 160 cm (5' 3") Comment: June 2017 @ ***** | Wt 57.9 kg (127 lb 9.6 oz) | SpO2 98% | BMI 22.6 kg/m2 Physical Examination: General appearance - alert, well appearing, and in no distress Mental status - alert, oriented to person, place, and time
- **Predicted**: mention=`Wt`, code=`C1305866||weight`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`Wt`, code=`C1305866||weight`, assertion=`Present`, value=`57.9`, unit=`kg`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value, conf=0.97)**: The note clearly specifies 'Wt 57.9 kg', but the predicted entity leaves value and unit blank. Since the value is present in the note and should have been extracted, this is a wrong_value error.


#### coral_breastca / note `36` / span (3682, 3685)

- **Note excerpt** (chars 3482–3885):
  > and are negative except that outlined above. BP 132/85 | Pulse 69 | Temp 36.5 C (97.7 F) (Oral) | Resp 16 | Ht 160 cm (5' 3") Comment: June 2017 @ ***** | Wt 57.9 kg (127 lb 9.6 oz) | SpO2 98% | BMI 22.6 kg/m2 Physical Examination: General appearance - alert, well appearing, and in no distress Mental status - alert, oriented to person, place, and time Eyes - pupils equal and reactive, extra
- **Predicted**: mention=`BMI`, code=`C1305855||body mass index`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`BMI`, code=`C1305855||body mass index`, assertion=`Present`, value=`22.6`, unit=`kg/m²`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value, conf=0.98)**: The note provides a BMI value of 22.6 kg/m2, but the prediction leaves the value and unit fields blank. This is a value omission error when a value is clearly present in the note.


#### coral_pdac / note `10` / span (5821, 5823)

- **Note excerpt** (chars 5621–6023):
  > normal. Judgment and thought content normal. Relevant Diagnostic Studies: Lab results: I personally reviewed and interpreted each of the patient's relevant lab tests as outlined [DATE] Na 130 K 3.8 Cl 92 Cr 0.92 AST 28 ALT 29 Tbili 1.0 Alk phos 67 WBC 8.8 Hgb 14.4 Plt 286 [DATE]: CA 19-9: 13737 Radiology: I personally reviewed and interpreted each of the patient
- **Predicted**: mention=`Na`, code=`C0337443||sodium`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`sodium (Na)`, code=`C0337443||sodium`, assertion=`Present`, value=`130`, unit=`mmol/L`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value, conf=0.98)**: The note clearly lists sodium (Na) as 130, but the model failed to extract the value (left as nan), which is a materially wrong value extraction.


#### coral_pdac / note `14` / span (6451, 6457)

- **Note excerpt** (chars 6251–6657):
  > sugar >100mg/dL insulin aspart U-100 (NOVOLOG) 100 unit/mL injection Inject under the skin three times daily with meals and at bedtime according to your insulin sliding scale insulin glargine (LANTUS) 100 unit/mL injection Inject 14 Units under the skin Daily. Or as directed. Note that your dose may change. insulin syringe-needle U-100 (BD INSULIN SYRINGE ULTRA-FINE) 0.3 mL 31 gauge x August 0
- **Predicted**: mention=`LANTUS`, code=`C0876064||lantus`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`LANTUS`, code=`C0876064||lantus`, assertion=`Present`, value=`14`, unit=`unit/mL`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_value, conf=0.98)**: The predicted entity for LANTUS omits the associated value (14) and unit (unit/mL) clearly present in the note ('Inject 14 Units ...'). This is a genuine omission of value/unit.


## Category: `wrong_date`

#### coral_breastca / note `38` / span (8148, 8155)

- **Note excerpt** (chars 7948–8355):
  > mps left breast. No nipple discharge. Some discomfort left breast  Neck pain [DATE] Last Assessment & Plan: Had a MVA last *****. Went to [REDACTED] for workup. She recalls imaging as negative. She continues to have neck pain radiating to left shoulder. Underwent PT, this made it worse. She is undergoing rolfing and would like to try some muscle relaxers to take prior to the
- **Predicted**: mention=`imaging`, code=`C0011923||medical imaging`, assertion=`Absent`, value=`negative`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`imaging`, code=`C0011923||medical imaging`, assertion=`Absent`, value=`negative`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_date, conf=0.97)**: The predicted entity omits the date ([DATE]) that is present in the gold annotation and clearly stated in the note. This is a material omission of a specific date mentioned in the text.


#### coral_breastca / note `35` / span (2651, 2673)

- **Note excerpt** (chars 2451–2873):
  > entimeter left axillary and left subpectoral nodes; the largest left axillary node measured 0.6 cm and the largest subpectoral node measured 0.7 cm. In addition to these findings there was a 7 mm hypoattenuating nodule on the right lobe of the thyroid gland that was hypermetabolic with an SUV of 2.4. Because of this thyroid nodule, an ultrasound and fine needle aspiration of this lesion was performed on July 08
- **Predicted**: mention=`hypoattenuating nodule`, code=`C4720860||hypoechoic nodule`, assertion=`Present`, value=`7`, unit=`mm`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`hypoattenuating nodule`, code=`C4720860||hypoechoic nodule`, assertion=`Present`, value=`7,2.4,hypermetabolic`, unit=`mm,SUV`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_date, conf=0.97)**: The predicted entity's begin_date and end_date are [DATE], while the gold entity has [DATE]. This is a one-year discrepancy in date, which is a materially significant error.


#### coral_pdac / note `18` / span (5857, 5867)

- **Note excerpt** (chars 5657–6067):
  > L Complete Blood Count with 5-part Differential Result Value Ref Range WBC Count 15.3 (H) 3.4 - 10 x10E9/L RBC Count 3.29 (L) 4.0 - 5.2 x10E12/L Hemoglobin 10.4 (L) 12.0 - 15.5 g/dL Hematocrit 30.8 (L) 36 - 46 % MCV 94 80 - 100 fL MCH 31.6 26 - 34 pg MCHC 33.8 31 - 36 g/dL Platelet Count 203 140 - 450 x10E9/L Neutrophil Absolute Count 12.04 (H) 1.8 - 6.8 x10E9/L Lymphocyt
- **Predicted**: mention=`Hematocrit`, code=`C0018935||hematocrit measurement`, assertion=`Present`, value=`30.8`, unit=`%`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`Hematocrit`, code=`C0018935||hematocrit measurement`, assertion=`Present`, value=`30.8,low`, unit=`%`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_date, conf=0.97)**: The predicted entity omits the begin_date and end_date, which are present in the gold as [DATE]. The value and unit are correct, but the missing date is a material error.


#### coral_pdac / note `18` / span (1039, 1049)

- **Note excerpt** (chars 839–1249):
  > reatment with gemcitabine and Abraxane but had demonstrated radiographic progression on [DATE]. At that point, she was started on dose modified FOLFIRINOX (C1D1 on [DATE]). [DATE]: C2D1 FOLFIRINOX Interim History: Patient reports increase fatigue over the past 3 weeks. She is sitting most of the day but can perform all of her ADLs. She most recently moved in with her daughter and is livin
- **Predicted**: mention=`FOLFIRINOX`, code=`C4742253||folfirinox`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`FOLFIRINOX`, code=`C4742253||folfirinox`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (wrong_date, conf=0.97)**: The note lists two dates for FOLFIRINOX: [DATE] (C1D1, start) and [DATE] (C2D1). Gold uses the start date ([DATE]) as begin_date, while pred uses [DATE]. The model picked the wrong date when multiple were mentioned.


## Category: `not_an_error`

#### 4CE / note `KUMC_2` / span (178, 192)

- **Note excerpt** (chars 0–392):
  > SURGERY ATTENDING ADMISSION NOTE [[DATE]] [PATIENT] [PATIENT] Admission Date : [[DATE]] Assessment / Plan : Principal Problem : Bowel obstruction (HCC) Chief Complaint : Abdominal pain History of Present Illness : [PATIENT] [PATIENT] is a 56 y. o. male who presents to the ED with 1 day history of abdominal pain that started this AM shortly after breakfast. Pain is sharp , in the mi
- **Predicted**: mention=`Abdominal pain`, code=`C0000737||abdominal pain`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`Abdominal pain`, code=`C0000737||abdominal pain`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (not_an_error, conf=0.98)**: The predicted entity is correct; the note mentions 'abdominal pain' and the only difference is that the prediction left begin_date and end_date blank, which is acceptable since the date is not explicitly stated in the mention span. This reflects a missing-but-not-required scenario.


#### 4CE / note `d54bcf6fe1fa225b13277b3b115fdcc3d` / span (7040, 7042)

- **Note excerpt** (chars 6840–7242):
  > igarettes Quit date: 1999 Years since quitting: 23.9 • Smokeless tobacco: Former Substance Use Topics • Alcohol use: Yes • Drug use: Not on file Lives in city w/ husband and children Objective BP 147/85 | Pulse 74 | Temp 36.5 °C (97.7 °F) (Oral) | Resp 22 | SpO2 99% Physical Exam: Constitutional: Does not appear to be in distress. Vital Signs reviewed. HEENT: Normocephalic, atraumatic,
- **Predicted**: mention=`BP`, code=`C1271104||blood pressure`, assertion=`Present`, value=`147/85`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`BP`, code=`C1271104||blood pressure`, assertion=`Present`, value=`147/85`, unit=`mmHg`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (not_an_error, conf=0.99)**: The predicted value '147/85' matches the note, and the absence of 'mmHg' as a unit is not a material error. The meaning is clear and equivalent; this is a format difference, not a substantive error.


#### coral_breastca / note `24` / span (74, 87)

- **Note excerpt** (chars 0–287):
  > ID: [REDACTED] is a 55 y.o. ***** with a recent diagnosis of early stage breast cancer, who presents in consultation to discuss treatment options and to establish care. Date of Service: [DATE] HPI: The patient has not had screening mammograms. She felt a lump in her left breas
- **Predicted**: mention=`breast cancer`, code=`C0006142||breast cancer`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.52)**: mention=`early stage breast cancer`, code=`C2986665||early-stage breast carcinoma`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_code`
- **Judge (not_an_error, conf=0.92)**: The predicted entity 'breast cancer' and the gold entity 'early stage breast cancer' refer to the same underlying clinical concept, with the gold having a more specific CUI. This is a synonym/granularity difference, not a substantive error.


#### coral_breastca / note `38` / span (8241, 8243)

- **Note excerpt** (chars 8041–8443):
  > 5 Last Assessment & Plan: Had a MVA last *****. Went to [REDACTED] for workup. She recalls imaging as negative. She continues to have neck pain radiating to left shoulder. Underwent PT, this made it worse. She is undergoing rolfing and would like to try some muscle relaxers to take prior to the sessions. Numbness and tingling in left arm. Her hand will shake with weight. Her ar
- **Predicted**: mention=`PT`, code=`C0949766||physical therapy`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`physical therapy (PT)`, code=`C0949766||physical therapy`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`
- **Judge (not_an_error, conf=0.98)**: The prediction correctly identifies PT as physical therapy and all other fields are either left blank or match the note; the only difference is the absence of a begin/end date, which is not specified in the note and thus not required.


#### coral_pdac / note `18` / span (8464, 8468)

- **Note excerpt** (chars 8264–8492):
  > rtial obstruction. An urgent referral to GI for an ERCP was placed. Pt was also called and informed of these findings. ED precautions were reviewed. Lower extremity US did not identify any DVTs. [REDACTED] , NP
- **Predicted**: mention=`DVTs`, code=`C0149871||deep vein thromboses`, assertion=`Absent`, value=`negative`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`DVTs`, code=`C0149871||deep vein thromboses`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (not_an_error, conf=0.98)**: The prediction 'negative' for value is semantically equivalent to the note stating that the lower extremity US did not identify any DVTs; this is a valid and medically defensible fill. The gold annotation leaves value blank, but the model's value is acceptable.


#### coral_pdac / note `2` / span (2397, 2399)

- **Note excerpt** (chars 2197–2599):
  > C tx x 2 units and underwent EGD ([DATE]) notable for partial gastric outlet obstruction, through which a 25 mm by 8 cm enteric stent was placed. - Resumed chemotherapy (cycle #5 of nal-IRI/5-FU/LV) on [DATE]. Interval history/review of systems - Tolerating POs adequately since stent placement, w/o postprandial vomiting; however, appetite generally poor - Occasional bilateral abdominal
- **Predicted**: mention=`LV`, code=`C0023413||leucovorin`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`LV`, code=`C0023413||leucovorin`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`
- **Judge (not_an_error, conf=0.99)**: The only difference is that the predicted entity includes an end_date equal to the begin_date, while the gold leaves end_date blank. The note only specifies a single date ([DATE]), so including it as both begin and end is not a material error and is medically defensible.

