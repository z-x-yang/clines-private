# EXP-E: GPT-4o Hallucination — Case Studies

Selected representative examples per FP category, for paper Discussion §3.5.
Excerpts are PHI-redacted by a conservative regex sweep (dates/MRN/IDs); **Zongxin must manually review before public release**.

Source: `fp_categorized.csv` (judge_col=`category_rule`).

## Category: `fabricated_entity`

#### 4CE / note `KUMC_2` / span (12042, 12043)

- **Note excerpt** (chars 11842–12054):
  > d recommendations as appropriate. I have reviewed evaluations / recommendations from other providers involved in the patient's care and have implemented as necessary. [REDACTED] [REDACTED] [REDACTED] , MD [[DATE]]
- **Predicted**: mention=`1`, code=`C0030695||patient monitoring`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`


#### 4CE / note `UPMC_Note3` / span (9999, 10013)

- **Note excerpt** (chars 9799–10021):
  > ify - Completed by [REDACTED] (on [REDACTED]:[REDACTED]) [REDACTED] - Completed by [REDACTED] (on ) VERIFY - Completed by [REDACTED] (on [REDACTED]:[REDACTED]) [REDACTED] - Canceled by [REDACTED] (on )"
- **Predicted**: mention=`[REDACTED]`, code=`C1547383||person name`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`


#### coral_breastca / note `38` / span (12970, 12978)

- **Note excerpt** (chars 12770–12985):
  > [REDACTED] , MD on *****/*****/***** 11:46 AM The above scribed documentation as annotated by me accurately reflects the services I have provided. [REDACTED] , MD *****/*****/***** 11:51 AM
- **Predicted**: mention=`11:51 AM`, code=`C4289593||eleven to twenty active hours`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`


#### coral_breastca / note `24` / span (9671, 9690)

- **Note excerpt** (chars 9471–9694):
  > utes face-to-face with the patient and 115 minutes of that time was spent counseling regarding the diagnosis, the treatment plan, the prognosis, medication risks, lifestyle modification, symptoms and therapeutic options.
- **Predicted**: mention=`therapeutic options`, code=`C0683525||treatment options`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`


#### coral_pdac / note `13` / span (0, 11)

- **Note excerpt** (chars 0–211):
  > VIDEO VISIT I performed this consultation using real-time Telehealth tools, including a live video connection between my location and the patient's location. Prior to initiating the consultation, I obtained inf
- **Predicted**: mention=`VIDEO VISIT`, code=`C3463807||video`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`


#### coral_pdac / note `14` / span (17243, 17251)

- **Note excerpt** (chars 17043–17257):
  > sit should any concerning symptoms arise in the interim. I spent a total of 25 minutes face-to-face with the patient and 25 minutes of that time was spent counseling regarding the treatment plan and symptoms'
- **Predicted**: mention=`symptoms`, code=`C1457887||symptoms`, assertion=`Hypothetical`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold**: no overlapping gold entity
- **Rule category**: `fabricated_entity`


## Category: `span_boundary_error`

#### 4CE / note `KUMC_7` / span (6670, 6677)

- **Note excerpt** (chars 6470–6781):
  > rched : Yes Belongings Searched : Yes Head Lice Check : Yes Program Orientation Program Orientation : Patient's Rights Written Patient's Rights Given / Reviewed : Yes Do you have access to firearms / weapons? no If yes , who will secure them prior to discharge? n / a [REDACTED] [REDACTED] [REDACTED] , RN [[DATE]]
- **Predicted**: mention=`weapons`, code=`C0860099||physical assault with weapon`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.39)**: mention=`firearms / weapons`, code=`C4759359||has access to firearm`, assertion=`Absent`, value=`no`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`


#### 4CE / note `d34f60de6187c4ebefd6d31bcaca64630` / span (7282, 7289)

- **Note excerpt** (chars 7082–7402):
  > tolic/diastolic function; may be worth repeating here or as outpatient Code Status: FULL CODE, discussed with patient on admission. VTE Prophylaxis: Lovenox Disposition: Patient with non-hypoxic dyspnea in need of scheduled nebulized treatments likely requiring <2 midnights. Name MD Hospital Medicine Service
- **Predicted**: mention=`dyspnea`, code=`C0013404||dyspnea`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.37)**: mention=`non-hypoxic dyspnea`, code=`C0344357||nocturnal dyspnea`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`


#### coral_breastca / note `34` / span (19399, 19406)

- **Note excerpt** (chars 19199–19446):
  > -face with the patient and 95 minutes of that time was spent counseling regarding the diagnosis, the treatment plan, the prognosis, medication risks, lifestyle modification, the risks and benefits of surgery, symptoms and therapeutic options.
- **Predicted**: mention=`surgery`, code=`C0524785||risk-benefit assessment`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.24)**: mention=`risks and benefits of surgery`, code=`C0524785||risk-benefit assessment`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`


#### coral_breastca / note `25` / span (53, 64)

- **Note excerpt** (chars 0–264):
  > [REDACTED] is a 53 y.o. female with newly diagnosed HR-negative HER2+ breast cancer here to discuss systemic therapy and management HISTORY OF PRESENT ILLNESS: [DATE] right diagnostic mammo with 3D Tomo- spiculated mass measuring 2.2 cm at 10-11:00 i
- **Predicted**: mention=`HR-negative`, code=`C2584453||hormone receptor negative neoplasm (disorder)`, assertion=`Present`, value=`negative`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.35)**: mention=`HR-negative HER2+ breast cancer`, code=`C1960398||her2 positive breast cancer`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`nan`
- **Rule category**: `span_boundary_error`


#### coral_pdac / note `18` / span (8440, 8442)

- **Note excerpt** (chars 8240–8492):
  > ing for developing or partial obstruction. An urgent referral to GI for an ERCP was placed. Pt was also called and informed of these findings. ED precautions were reviewed. Lower extremity US did not identify any DVTs. [REDACTED] , NP
- **Predicted**: mention=`US`, code=`C0041618||ultrasound`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.11)**: mention=`Lower extremity US`, code=`C3266183||ultrasonography of lower limb`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `span_boundary_error`


#### coral_pdac / note `6` / span (11650, 11664)

- **Note excerpt** (chars 11450–11730):
  > including reviewing records and tests, obtaining history and exam, placing orders, communicating with other healthcare professionals, counseling the patient, family or caregiver, documenting in the medical record, and/or care coordination for the diagnoses above.
- **Predicted**: mention=`medical record`, code=`C0025102||medical record`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=0.40)**: mention=`documenting in the medical record`, code=`C0175636||documenting patient information`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `span_boundary_error`


## Category: `wrong_code`

#### 4CE / note `d34f60de6187c4ebefd6d31bcaca64630` / span (7350, 7361)

- **Note excerpt** (chars 7150–7402):
  > nt Code Status: FULL CODE, discussed with patient on admission. VTE Prophylaxis: Lovenox Disposition: Patient with non-hypoxic dyspnea in need of scheduled nebulized treatments likely requiring <2 midnights. Name MD Hospital Medicine Service
- **Predicted**: mention=`2 midnights`, code=`C0184699||hospital admission, short-term, 24 hours`, assertion=`Present`, value=`2 midnights`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.82)**: mention=`midnights`, code=`C1698490||short stay`, assertion=`Present`, value=`2`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_code`


#### 4CE / note `KUMC_5` / span (3980, 3982)

- **Note excerpt** (chars 3780–4182):
  > Range : CLEAR CLEAR CLEAR Specific Gravity Urine Latest Range : 1. 003 1. 035 1. 035 pH , UA Latest Range : 4. 6 8. 0 7. 5 Glucose , UA Latest Range : NEG NEG NEG Ketones , UA Latest Range : NEG NEG 4+ (A) Bilirubin , UA Latest Range : NEG NEG NEG Protein , UA Latest Range : NEG NEG NEG Urobilinogen , UA Latest Range : NORM NORMAL NORMAL Blood , UA Latest Range : NEG NEG NEG Nitrite , UA Latest Ran
- **Predicted**: mention=`4+`, code=`C0022634||ketone`, assertion=`Present`, value=`4+`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`4+`, code=`C0162275||urine ketones`, assertion=`Present`, value=`4+,abnormal`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_code`


#### coral_breastca / note `22` / span (60, 73)

- **Note excerpt** (chars 0–273):
  > ***** 60 yo F Chief complaint: Patient with early stage breast cancer here to discuss neoadjuvant therapy History of Present Illness: [REDACTED] is a 60 y.o. female with a recently diagnosed right sided invasive spindle cell metaplastic carcinoma breast cancer.
- **Predicted**: mention=`breast cancer`, code=`C0006142||breast cancer`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.52)**: mention=`early stage breast cancer`, code=`C2986665||early-stage breast carcinoma`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_code`


#### coral_breastca / note `24` / span (74, 87)

- **Note excerpt** (chars 0–287):
  > ID: [REDACTED] is a 55 y.o. ***** with a recent diagnosis of early stage breast cancer, who presents in consultation to discuss treatment options and to establish care. Date of Service: [DATE] HPI: The patient has not had screening mammograms. She felt a lump in her left breas
- **Predicted**: mention=`breast cancer`, code=`C0006142||breast cancer`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.52)**: mention=`early stage breast cancer`, code=`C2986665||early-stage breast carcinoma`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_code`


#### coral_pdac / note `10` / span (8, 33)

- **Note excerpt** (chars 0–233):
  > INITIAL GI MEDICAL ONCOLOGY VISIT Patient name [REDACTED] DOB [DATE] Medical record number ***** Date of service [DATE] Referring Provider: Dr. [REDACTED] Mr. ***** is a 52 y.o. male whom
- **Predicted**: mention=`GI MEDICAL ONCOLOGY VISIT`, code=`C0559997||seen in oncology clinic`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=0.76)**: mention=`INITIAL GI MEDICAL ONCOLOGY VISIT`, code=`C0419842||initial gastrointestinal tract assessment`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_code`


#### coral_pdac / note `16` / span (98, 123)

- **Note excerpt** (chars 0–323):
  > This is an independent visit Patient ID: [REDACTED] is a 58 y.o. male with locally advanced pancreatic adenocarcinoma. ATTENDING: [REDACTED] , MD Primary Care Provider: [REDACTED] , MD HISTORY OF PRESENT ILLNESS: October 2017: abd pain. Seen in ED sent home. A first endoscopy showed no abnorma
- **Predicted**: mention=`pancreatic adenocarcinoma`, code=`C0281361||pancreatic adenocarcinoma`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=0.60)**: mention=`locally advanced pancreatic adenocarcinoma`, code=`C4744700||locally advanced pancreatic adenocarcinoma`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_code`


## Category: `wrong_assertion`

#### 4CE / note `d34f60de6187c4ebefd6d31bcaca64630` / span (7218, 7233)

- **Note excerpt** (chars 7018–7402):
  > fect on BLE edema - echo around time of ablation with normal systolic/diastolic function; may be worth repeating here or as outpatient Code Status: FULL CODE, discussed with patient on admission. VTE Prophylaxis: Lovenox Disposition: Patient with non-hypoxic dyspnea in need of scheduled nebulized treatments likely requiring <2 midnights. Name MD Hospital Medicine Service
- **Predicted**: mention=`VTE Prophylaxis`, code=`C0199242||venous thromboembolism prophylaxis`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`VTE Prophylaxis`, code=`C0199242||venous thromboembolism prophylaxis`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`


#### 4CE / note `KUMC_6` / span (12190, 12191)

- **Note excerpt** (chars 11990–12391):
  > . Possible SIADH. At risk for neurologic sequela. Monitor closely. If persistent will check urine lytes , osmo and serum uric acid. Avoid hypotonic fluids. Infusions to be mixed in saline in place of D [xxxxx x. xxxxx] water restriction. Continue serial CHEM 7. Anemia Hb low but no clinical signs of overt bleeding. Possibly premorbid hemodilution from fluid administration. Continue to trend seriall
- **Predicted**: mention=`D`, code=`C0017725||dextrose`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`D`, code=`C0017725||dextrose`, assertion=`Hypothetical`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_assertion`


#### coral_breastca / note `23` / span (5162, 5164)

- **Note excerpt** (chars 4962–5364):
  > re-meds for future scans  Contrast [Gadolinium-Containing Contrast Media] Itching Patient not sure if she is allergic to GAD. Will add to allergy list: She is allergic to NON-Ionic Contrast (CT,etc.) She takes pre - meds for this.  Hydrocodone-Acetaminophen Nausea Only  Penicillins Unknown  Pollen Extracts Runny nose and dizziness PAST, FAMILY, and SOCIAL HISTORY P
- **Predicted**: mention=`CT`, code=`C0009778||ct`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`CT`, code=`C0009778||ct`, assertion=`Hypothetical`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`


#### coral_breastca / note `24` / span (2898, 2900)

- **Note excerpt** (chars 2698–3100):
  > stiffness, in particular in her knees. ***** has met with Dr. [REDACTED] and Dr. [REDACTED] who have both recommended adjuvant chemotherapy (she states that they have specifically recommended TC). She states that when she saw Dr. ***** he recommended that her tumor (presumptively left) be sent for Oncotype. She is not yet aware of a result. She is concerned that the benefits of chemothe
- **Predicted**: mention=`TC`, code=`C4522122||docetaxel-cyclophosphamide`, assertion=`Conditional`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`TC`, code=`C4522122||docetaxel-cyclophosphamide`, assertion=`Hypothetical`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`


#### coral_pdac / note `3` / span (8406, 8415)

- **Note excerpt** (chars 8206–8429):
  > ewing patient's records and tests, obtaining history, placing orders, communicating with other healthcare professionals, counseling the patient, family, or caregiver, and/or care coordination for the diagnoses above.
- **Predicted**: mention=`diagnoses`, code=`C0011900||diagnoses`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`diagnoses`, code=`C0011900||diagnoses`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_assertion`


#### coral_pdac / note `6` / span (11673, 11690)

- **Note excerpt** (chars 11473–11730):
  > ords and tests, obtaining history and exam, placing orders, communicating with other healthcare professionals, counseling the patient, family or caregiver, documenting in the medical record, and/or care coordination for the diagnoses above.
- **Predicted**: mention=`care coordination`, code=`C4724363||coordination of care`, assertion=`Notassociated`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`care coordination`, code=`C4724363||coordination of care`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_assertion`


## Category: `wrong_value_or_date`

#### 4CE / note `BCH_1` / span (7172, 7190)

- **Note excerpt** (chars 6972–7215):
  > 2020 06:02 EST Bacteria, Urinalysis BTRACE (Abnormal) 2020 06:02 EST Mucus, Urinalysis B1+ (Abnormal) 2020 06:02 EST SARS CoV-2 (COVID-19) PCR, Resp, QuaL SARS-CoV-2 POS (Abnormal) 2020 06:54 EST Rapid Strep A POCT Negative 2020 08:44 EST
- **Predicted**: mention=`Rapid Strep A POCT`, code=`C0519937||strep a assay w/optic`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Gold (best overlap, IoU=1.00)**: mention=`Rapid Strep A POCT`, code=`C0519937||strep a assay w/optic`, assertion=`Present`, value=`negative`, unit=`nan`, begin_date=`[DATE]`, end_date=`[DATE]`
- **Rule category**: `wrong_value_or_date`


#### 4CE / note `d54bcf6fe1fa225b13277b3b115fdcc3d` / span (9344, 9352)

- **Note excerpt** (chars 9144–9439):
  > reathing and IS every 2 hours while awake. - Nutrition: regular - PT/OT: defer Code Status: FULL CODE, discussed with patient on admission. VTE Prophylaxis: SCDs Disposition: Patient with abnormal chest CT in need of labs likely requiring >2 midnights. Name, MD Hospital Medicine Service
- **Predicted**: mention=`chest CT`, code=`C0202823||computed tomography of chest`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`chest CT`, code=`C0202823||computed tomography of chest`, assertion=`Present`, value=`abnormal`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`


#### coral_breastca / note `23` / span (39, 59)

- **Note excerpt** (chars 0–259):
  > ID: 71 year old female CC: HR low, HER2 negative cancer of the right breast HPI: [REDACTED] is a 71 y.o. female with R breast cancer here for discussion for a new patient visit. [DATE]- Bilateral Breast MRI . Found 1.2 x 0.7 x 0.7 cm
- **Predicted**: mention=`HER2 negative cancer`, code=`C2316304||human epidermal growth factor 2 (her2) negative carcinoma of breast`, assertion=`Present`, value=`negative`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`HER2 negative cancer`, code=`C2316304||human epidermal growth factor 2 (her2) negative carcinoma of breast`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`


#### coral_breastca / note `38` / span (85, 108)

- **Note excerpt** (chars 0–308):
  > SUBJECTIVE [REDACTED] is a 49 y.o. female with ER+/PR-/HER2- left breast cancer, mammaprint low risk IDC of the left breast s/p NAHT, s/p bilateral mastectomies, s/p adjuvant tamoxifen *****/*****-*****/*****. She was switched to OS/AI in November 2018. Switched from letrozole to exemestane December 201
- **Predicted**: mention=`mammaprint low risk IDC`, code=`C1334206||intermediate-grade dcis`, assertion=`Present`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`mammaprint low risk IDC`, code=`C1334206||intermediate-grade dcis`, assertion=`Present`, value=`low risk`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`


#### coral_pdac / note `7` / span (16391, 16401)

- **Note excerpt** (chars 16191–16407):
  > illness. Risk of complications, morbidity/mortality of patient management: High; the patient's systemic cancer therapy requires regular and intensive monitoring for potential major/life-threatening toxicities.
- **Predicted**: mention=`toxicities`, code=`C0879626||adverse effects`, assertion=`Possible`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`toxicities`, code=`C0879626||adverse effects`, assertion=`Possible`, value=`potential major;life-threatening`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`


#### coral_pdac / note `18` / span (8464, 8468)

- **Note excerpt** (chars 8264–8492):
  > rtial obstruction. An urgent referral to GI for an ERCP was placed. Pt was also called and informed of these findings. ED precautions were reviewed. Lower extremity US did not identify any DVTs. [REDACTED] , NP
- **Predicted**: mention=`DVTs`, code=`C0149871||deep vein thromboses`, assertion=`Absent`, value=`negative`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Gold (best overlap, IoU=1.00)**: mention=`DVTs`, code=`C0149871||deep vein thromboses`, assertion=`Absent`, value=`nan`, unit=`nan`, begin_date=`nan`, end_date=`nan`
- **Rule category**: `wrong_value_or_date`

