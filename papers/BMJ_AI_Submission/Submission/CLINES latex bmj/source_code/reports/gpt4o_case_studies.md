## GPT-4o Case Studies (incremental log)\n\n- Note: This file is incrementally updated during mining.\n
### Lab unit inference from abbreviations (Lat/BE/Glic)

- Note: `data/4CE/ICSM_1.txt`
- Prediction: `outputs/gpt4o_output/4CE_ICSM_1_default.csv`
- Highlight: 缩写+数值无单位 → 正确推理term与单位（mmol/L, mg/dL），infer=True

````
10:10:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/ICSM_1.txt
// ... see file for full context ...
````

````
12:14:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_ICSM_1_default.csv
// ... see file for full context ...
````


### European date disambiguation (dd/mm → ISO)

- Note: `data/4CE/ICSM_1.txt`
- Prediction: `outputs/gpt4o_output/4CE_ICSM_1_default.csv`
- Highlight: 多处dd/mm被正确解析为YYYY-MM-DD（begin/end一致）

````
11:19:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/ICSM_1.txt
// ... see file for full context ...
````

````
5:16:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_ICSM_1_default.csv
// ... see file for full context ...
````


### Abbreviation normalization (IOT/TI/RX → UMLS)

- Note: `data/4CE/ICSM_1.txt`
- Prediction: `outputs/gpt4o_output/4CE_ICSM_1_default.csv`
- Highlight: 缩写→正确UMLS（Procedure/Org/Imaging）

````
15:16:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_ICSM_1_default.csv
// ... see file for full context ...
````

````
16:16:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_ICSM_1_default.csv
// ... see file for full context ...
````

````
24:25:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_ICSM_1_default.csv
// ... see file for full context ...
````


### Entity relation (CAD related PCI)

- Note: `data/4CE/report01.txt`
- Prediction: `outputs/gpt4o_output/4CE_report01_default.csv`
- Highlight: 用related互指显式化关系（CAD s/p PCI）

````
55:57:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/report01.txt
// ... see file for full context ...
````

````
12:14:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_report01_default.csv
// ... see file for full context ...
````


### Diverse assertion statuses (Present/Absent/Possible/Conditional)

- Note: `data/coral_annotated_pdac/0.txt`
- Prediction: `outputs/gpt4o_output/coral_annotated_pdac_0_default.csv`
- Highlight: 同一文档多断言类型并存，均正确标注

````
1:3:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/coral_annotated_pdac_0_default.csv
// ... see file for full context ...
````

````
19:25:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/coral_annotated_pdac_0_default.csv
// ... see file for full context ...
````


### Non-numeric values (elevated/negative/half pack)

- Note: `data/4CE/report01.txt`
- Prediction: `outputs/gpt4o_output/4CE_report01_default.csv`
- Highlight: 值为文字或量纲短语也被结构化捕获

````
33:36:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_report01_default.csv
// ... see file for full context ...
````

````
44:47:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_report01_default.csv
// ... see file for full context ...
````


### Lab unit inference: PaO2 without unit → mmHg (infer=True)

- Note: `data/4CE/report01.txt`
- Prediction: `outputs/gpt4o_output/4CE_report01_default.csv`
- Highlight: 原文仅“PaO2 of 57”无单位，模型补出mmHg并标infer=True

````
55:61:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/report01.txt
// ... see file for full context ...
````

````
58:60:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_report01_default.csv
// ... see file for full context ...
````


### Abbreviation normalization: ETOH/NKA → correct UMLS (Absent)

- Note: `data/4CE/UPMC_Note1.txt`
- Prediction: `outputs/gpt4o_output/4CE_UPMC_Note1_default.csv`
- Highlight: “ETOH”“NKA”在复杂病历段落中仍被正确归一并断言为Absent

````
1:1:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/4CE/UPMC_Note1.txt
// ... see file for full context ...
````

````
24:28:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_UPMC_Note1_default.csv
// ... see file for full context ...
````


### Entity relations in PDAC: stent ↔ biliary obstruction (related)

- Note: `data/coral_annotated_pdac/0.txt`
- Prediction: `outputs/gpt4o_output/coral_annotated_pdac_0_default.csv`
- Highlight: 多处stent条目互相关联并与梗阻上下文对齐（related索引）

````
1:2:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_pdac/0.txt
// ... see file for full context ...
````

````
20:22:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/coral_annotated_pdac_0_default.csv
// ... see file for full context ...
````


### Non-numeric values: “mid 90s”/“high 80s” captured structurally

- Note: `data/4CE/report01.txt`
- Prediction: `outputs/gpt4o_output/4CE_report01_default.csv`
- Highlight: 饱和度等以文字范围表达的值被写入value字段，便于规则/阈值

````
63:66:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_report01_default.csv
// ... see file for full context ...
````

````
54:56:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_report01_default.csv
// ... see file for full context ...
````


### Abbreviation normalization: ICU/PCI/EVAR across long narrative

- Note: `data/4CE/report01.txt`
- Prediction: `outputs/gpt4o_output/4CE_report01_default.csv`
- Highlight: 跨大段H&P文本多缩写一次性正确归一，稳健性较好

````
6:7:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_report01_default.csv
// ... see file for full context ...
````

````
14:16:/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/gpt4o_output/4CE_report01_default.csv
// ... see file for full context ...
````




### Case studies: robust clinical inference across modalities and contexts

We conducted targeted case studies to evaluate the breadth and reliability of the agent's clinical information extraction in real-world notes spanning multiple institutions and languages. The selected examples illustrate four strengths: (i) unit inference for underspecified measurements; (ii) normalization of ambiguous mentions to standardized terminologies; (iii) extraction of clinically salient relations across entities; and (iv) robust handling of nuanced assertion status and non-numeric values.

First, in multilingual emergency and ICU narratives, abbreviations such as "Lat 2.4", "BE -30" and "Glic 617" lacked explicit units. The agent consistently inferred the underlying laboratory concepts (lactate, base excess, glucose) and recovered appropriate units (mmol/L, mmol/L, mg/dL), yielding structured outputs aligned with UMLS concepts. This capability mitigates common documentation variability and enables downstream quantitative analyses without manual curation.

Second, the agent reliably normalized terse or institution-specific abbreviations—e.g., IOT (invasive mechanical ventilation), TI (ICU), RX (chest X-ray), PCI and EVAR—to the correct controlled terms, preserving semantic type (procedure, organization, imaging). This normalization stabilized downstream mapping and allowed aggregation across heterogeneous charting styles.

Third, beyond isolated entities, the agent surfaced clinically meaningful relations. For example, in coronary artery disease notes, the system linked CAD with s/p PCI using explicit cross-references, and in oncology follow-ups it connected biliary obstruction, stent placement, and subsequent infectious management steps. Such graph-structured outputs facilitate cohort identification and timeline reconstruction.

Fourth, the system handled nuanced assertions (Present, Absent, Possible, Conditional) within the same document and captured non-numeric values such as "elevated", "negative", and qualitative ranges (e.g., "mid 90s" oxygen saturation). These representations preserve clinical nuance while remaining machine-actionable, improving phenotyping and decision support.

Collectively, these studies demonstrate that the agent is not merely a string matcher but a robust clinical reasoner: it infers missing units, resolves abbreviations across languages, encodes relations that reflect care processes, and preserves uncertainty. This combination materially reduces manual normalization burden and increases the fidelity of downstream analytics.

