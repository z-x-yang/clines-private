# Case Studies with Note Context
选取4CE与CORAL（breastca/pdac）典型错误，展示原文上下文（基于GT位置±140字符；无位置信息则使用记录中的context）。

---

## 4CE
### Phi‑4 — mention
- file `4CE_BCH_1_default_phi4_with_positions.csv` pos `(6338, 6348)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/BCH_1.txt`
  - Pred: `urinalysis` | GT: `Appearance, Urinalysis`
  - Context: esium	2.1 mg/dL	2020 05:36 EST 	Troponin T	Not Reported	2020 14:15 EST 	Pregnancy Test, Urine HCG POCT	Negative	2020 05:30 EST 	Appearance, Urinalysis	-	2020 06:02 EST 	Color, Urinalysis	Yellow	2020 06:02 EST 	Specific Gravity, Urinalysis	1.033 (High)	2020 06:02 EST 	pH, Urinalysis	p6.0	20
- file `4CE_BCH_1_default_phi4_with_positions.csv` pos `(6408, 6424)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/BCH_1.txt`
  - Pred: `specific gravity` | GT: `Specific Gravity, Urinalysis`
  - Context:  	Pregnancy Test, Urine HCG POCT	Negative	2020 05:30 EST 	Appearance, Urinalysis	-	2020 06:02 EST 	Color, Urinalysis	Yellow	2020 06:02 EST 	Specific Gravity, Urinalysis	1.033 (High)	2020 06:02 EST 	pH, Urinalysis	p6.0	2020 06:02 EST 	Glucose, Urinalysis	-	2020 06:02 EST 	Ketone, Urinalysis	K3+ (
- file `4CE_BCH_1_default_phi4_with_positions.csv` pos `(1195, 1205)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/BCH_1.txt`
  - Pred: `covid test` | GT: `Covid test`
  - Context:  			  			In the ED, she was afebrile and slightly tachycardic. CBC and chem were unremarkable. UA significant for spec grav of 1.03. Repeat Covid test positive. Rapid strep negative. ECG normal. She was given 2 x NS boluses with improvement in tachycardia. PO intake improved minimally in t
### Phi‑4 — assertion_status
- note `0`
  - Pred: `title` | GT: `Present`
  - Context: Hemoglobin
- note `0`
  - Pred: `title` | GT: `Present`
  - Context: allergies
- note `0`
  - Pred: `Present` | GT: `Notassociated`
  - Context: hypertension
### Phi‑4 — value
- note `0`
  - Pred: `11.1` | GT: `6.5`
  - Context: Hemoglobin
- note `0`
  - Pred: `64` | GT: `104`
  - Context: pulse
- note `0`
  - Pred: `Missing prediction` | GT: `101`
  - Context: ame back to town the Tuesday after event and he felt fine. Then 3-4 days ago he says he started feeling completely wiped out. He developed a runny nose, cough, sore throat, fevers, to 101 and loose stool 1-3x daily. He has had lots of myaglias and profound weakness, causing him to fall at least 4-5x. He says he was initally able to drag hims
### Phi‑4 — unit
- note `0`
  - Pred: `Missing prediction` | GT: `F`
  - Context: ame back to town the Tuesday after event and he felt fine. Then 3-4 days ago he says he started feeling completely wiped out. He developed a runny nose, cough, sore throat, fevers, to 101 and loose stool 1-3x daily. He has had lots of myaglias and profound weakness, causing him to fall at least 4-5x. He says he was initally able to drag hims
- note `0`
  - Pred: `Missing prediction` | GT: `times/day`
  - Context:  after event and he felt fine. Then 3-4 days ago he says he started feeling completely wiped out. He developed a runny nose, cough, sore throat, fevers, to 101 and loose stool 1-3x daily. He has had lots of myaglias and profound weakness, causing him to fall at least 4-5x. He says he was initally able to drag himself across the room and get up bu
- note `0`
  - Pred: `Missing prediction` | GT: `bpm`
  - Context:  coming down with symptoms today. He has not had covid before but has had the vaccine and booster, last in the fall.  In the ED he was AF but had HR  100 and SBP 122/79. SpO2 was 98% on RA and his lab workup was relatively unremarkable except for a positive COVID-19 PCR.  Information and History obtai
### GPT‑4o — mention (contrast)
- file `BCH_1_updated.csv` pos `(946, 965)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/BCH_1.txt`
  - Pred: `Missing prediction` | GT: `shortness of breath`
  - Context:  prompting her to come into the ED. Endorses some intermittent chest pain on the left, not pleuritic, likely muscular in nature. Denies any shortness of breath, wheezing, haemoptysis, dysuria, calf pain, hx/FHx of blood clots or bleeding disorders.  			  			In the ED, she was afebrile and slightly 
- file `BCH_1_updated.csv` pos `(967, 975)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/BCH_1.txt`
  - Pred: `Missing prediction` | GT: `wheezing`
  - Context: e into the ED. Endorses some intermittent chest pain on the left, not pleuritic, likely muscular in nature. Denies any shortness of breath, wheezing, haemoptysis, dysuria, calf pain, hx/FHx of blood clots or bleeding disorders.  			  			In the ED, she was afebrile and slightly tachycardi
## coral_breastca
### Phi‑4 — mention
- file `coral_annotated_breastca_21_default_phi4_with_positions.csv` pos `(85, 98)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `cancer center` | GT: `COMPREHENSIVE CANCER CENTER`
  - Context:                         UCSF ***** ***** FAMILY                        COMPREHENSIVE CANCER CENTER                      ***** ***** ***** ***** Care Center                             ***** ***** *****                           Second ***
- file `coral_annotated_breastca_21_default_phi4_with_positions.csv` pos `(1087, 1117)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `infiltrating ductal carcinoma` | GT: `infiltrating ductal  carcinoma`
  - Context: d a right breast mass  removed in February 1994 with an axillary lymph node dissection.  That  surgical procedure revealed a 1 cm, grade 1, infiltrating ductal  carcinoma with clear surgical margins and 21 axillary lymph nodes were  negative for metastatic carcinoma.  S-phase was low at 3.6%.  The tumor  was 
- file `coral_annotated_breastca_21_default_phi4_with_positions.csv` pos `(1300, 1331)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `progesterone-receptor negative` | GT: `progesterone-receptor  negative`
  - Context: y lymph nodes were  negative for metastatic carcinoma.  S-phase was low at 3.6%.  The tumor  was found to be estrogen-receptor positive and progesterone-receptor  negative.  She received interstitial radiation, which comprised 4500  centigray over a 3 cm diameter.  She received tamoxifen from 1994 to  1996 and
### Phi‑4 — assertion_status
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `Present` | GT: `Notassociated`
  - Context: Aging Clinic
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `present` | GT: `Notassociated`
  - Context: Breast Care Center
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `hypothetical` | GT: `Present`
  - Context: CALGB 40503
### Phi‑4 — value
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `[{{ BP }}]` | GT: `160/82`
  - Context: blood pressure
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `24` | GT: `56`
  - Context: hormone replacement therapy
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `Missing prediction` | GT: `1`
  - Context: issection. The surgical procedure revealed a 1 cm, grade 1, infiltrating ductal carcin
### Phi‑4 — unit
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `months` | GT: `years`
  - Context: hormone replacement therapy
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `beats per minute` | GT: `bpm`
  - Context: pulse
- note `21`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `breaths per minute` | GT: `breaths/min`
  - Context: respirations
### GPT‑4o — mention (contrast)
- file `coral_annotated_breastca_21_default_gpt4o_with_positions.csv` pos `(8734, 8760)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `left supraclavicular space` | GT: `left subclavian triangle space`
  - Context: Her oropharynx is clear.  She is anicteric.  LYMPH NODES: She has no cervical or axillary adenopathy.  There are  soft, mobile nodes in the left supraclavicular space.  LUNGS: Her lungs are clear bilaterally to auscultation and percussion.  CARDIAC: Her cardiac exam is without murmur or gallop.  BREASTS: 
- file `coral_annotated_breastca_21_default_gpt4o_with_positions.csv` pos `(12516, 12519)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt`
  - Pred: `CBC` | GT: `complete blood count normal`
  - Context: cia and gliosis consistent with a prior insult.  We  obtained laboratory studies on the day of her visit as well.  These  revealed a normal CBC, creatinine, electrolytes, liver function tests,  and calcium.  Interestingly, a CA27-29 was only 15 and an LDH was normal  as well.  Based
## coral_pdac
### Phi‑4 — mention
- file `coral_annotated_pdac_0_default_phi4_with_positions.csv` pos `(1775, 1787)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/0.txt`
  - Pred: `hypertension` | GT: `Hypertension`
  - Context: some social and economic issues.    His girlfriend gave birth to a baby girl on April 27.     PAST MEDICAL HISTORY:     MEDICAL ILLNESSES:  Hypertension, voluntarily stopped his antihypertensive    PRIOR SURGERIES:  Drainage of a perirectal abscess, age 17    INJURIES:  None reported    CURR
- file `coral_annotated_pdac_0_default_phi4_with_positions.csv` pos `(3976, 3980)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/0.txt`
  - Pred: `RANS` | GT: `Aspartate Transaminase`
  - Context: nge    Creatinine 1.06 0.61 - 1.24 mg/dL    eGFR if non-African   American 83 >60 mL/min    eGFR if African Amer 96 >60 mL/min   Aspartate Transaminase   Result Value Ref Range    Aspartate transaminase 20 17 - 42 U/L   Alanine Transaminase   Result Value Ref Range    Alanine transam
- file `coral_annotated_pdac_0_default_phi4_with_positions.csv` pos `(2020, 2025)`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/0.txt`
  - Pred: `hives` | GT: `Hives`
  - Context: ess, age 17    INJURIES:  None reported    CURRENT MEDICATIONS:  See   intake    ALLERGIES:  Allergies   Allergen Reactions    Penicillins Hives       FAMILY HISTORY:  There is no cancer among his first-degree relatives. He has 2 siblings. His maternal grandmother had colorectal canc
### Phi‑4 — assertion_status
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `title` | GT: `Present`
  - Context: CT Chest
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `hypothetical` | GT: `Present`
  - Context: Pain
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `possible` | GT: `Present`
  - Context: biliary obstruction
### Phi‑4 — value
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `67` | GT: `60`
  - Context: Alkaline phosphatase
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `14.4` | GT: `11.1,low`
  - Context: Hemoglobin
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `286` | GT: `203`
  - Context: Platelet count
### Phi‑4 — unit
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `mL` | GT: `cc`
  - Context: omnipaque
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `Missing prediction` | GT: `cycle`
  - Context: initially saw him, he had lost 43 pounds and was having a lot of pain. We elected to start gemcitabine and Abraxane. He's completed 6 full cycles. At the end of 2 cycles, his CT scan s
- note `10`
  - Note: `/n/lw_groups/hms/dbmi/yu/lab/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/10.txt`
  - Pred: `Missing prediction` | GT: `cycle`
  - Context:  lost 43 pounds and was having a lot of pain. We elected to start gemcitabine and Abraxane. He's completed 6 full cycles. At the end of 2 cycles, his CT scan suggested progression. 
### GPT‑4o — mention (contrast)
- file `0_updated.csv` pos `(548, 570)`
  - Pred: `Missing prediction` | GT: `Fine-needle aspiration`
  - Context: nan
- file `0_updated.csv` pos `(811, 822)`
  - Pred: `Missing prediction` | GT: `progression`
  - Context: nan