# EXP-A_iaa_cohen_kappa

## 1. 元数据

- **EXP-ID**: EXP-A
- **作战表 E#**: E1 (covers R1 M1 / R2 M2 / **R5 A2 hard requirement**)
- **日期**: 2026-05-25
- **Job ID**: local (no SLURM; pure-CPU stats)
- **Commit hash**: `2d1fdf237faf1d444b8d751e6b810a0f5c438406` (40-char launch hash, backfilled by experiments-rules.md §8.1 step 4)
- **Branch**: `exp/EXP-A_iaa_cohen_kappa`
- **Owner**: zongxin (sub-agent: Claude Code)
- **Baseline of**: `i2b2` @ 8735bbb (RESPONSE_PLAN.md + EXPERIMENTS.md scaffold)

## 2. 目的

Compute inter-annotator agreement (IAA) on the BMJ revision cross-annotation
data to satisfy R1 M1 / R2 M2 / **R5 A2 hard requirement** ("IAA must be
reported quantitatively, not only as a Limitation"). Two annotators (Mo,
Enci) independently **re-reviewed** the AI-suggested draft annotations
(`*_for_review.csv`) for notes originally annotated by the other person.
The unit of agreement is each AI-draft `term_index` row: annotators
accept / drop / edit the draft entity, and may add new rows. Report
Cohen's κ + F1-based agreement at entity-level (kept vs dropped), at
assertion-level (conditional on both keeping the row), and value+unit
agreement rate. Per-dataset breakdown: 4CE / CORAL-merged
(CORAL-Pancreas + CORAL-Breast as user decided). MIMIC-III not in
scope (single-annotator).

## 3. Baseline

- Main branch reference: `i2b2` @ commit `8735bbb` (RESPONSE_PLAN.md +
  EXPERIMENTS.md scaffold at launch).
- No prior EXP-ID; EXP-A is the first BMJ-revision experiment.

## 4. Diff (vs baseline)

- **代码改动**: new `scripts/iaa/` package:
  - `compute_iaa.py` — main entry: aligns annotator CSV pairs by AI-draft
    `term_index`, computes Cohen's κ + F1 + per-category breakdown.
  - `iaa_utils.py` — load/normalize helpers (assertion class collapsing,
    type comparison, value/unit normalization).
- **超参改动**: N/A (no model / pipeline call).
- **数据改动**: N/A (uses existing artifacts only):
  - AI drafts: `papers/BMJ_AI_Submission/Major Revision/cross-annotation/For_{Mo,Enci}_IAA_cross_annotation.zip`
  - Cross-annotators' returns: `papers/.../From Mo_2_Zongxin_Compressed (zipped) Folder.zip`,
    `papers/.../To_Zongxin_Enci_add_annotation.zip`
  - Gold (original annotation): `outputs/reviewed_updated2/{4CE,coral_annotated_pdac,coral_annotated_breastca}/`

## 5. 复现命令

```bash
git checkout exp/EXP-A_iaa_cohen_kappa
cd "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data"

# Single command (no env vars needed; pure pandas + sklearn)
python -m scripts.iaa.compute_iaa \
    --cross_anno_dir "papers/BMJ_AI_Submission/Major Revision/cross-annotation" \
    --gold_dir outputs/reviewed_updated2 \
    --out_dir runs/EXP-A
```

Outputs in `runs/EXP-A/`:
- `metrics.json` — per-dataset (4CE / CORAL) + overall κ + F1 numbers
- `per_note_breakdown.csv` — one row per (note, annotator-pair) with raw counts
- `report.txt` — human-readable summary with sklearn-style classification reports for assertion/type
- `pair_manifest.csv` — list of all annotator pairs actually computed (PHI-free; just note IDs)

## 6. 配置快照

No config file; all CLI flags inline above. Key analysis decisions
(inline copy for durable reproducibility):

```yaml
unit_of_agreement: term_index in AI draft   # AI-suggested row, stable cross-annotator key
keep_drop_unit: present in annotator CSV after review = "kept"; absent = "dropped"
span_alignment: exact (annotators use the tool's AI-suggested span; verified zero edits in 284-row spot-check)
assertion_collapse:                          # for Cohen's κ stability with sparse classes
  - Present, Historical, Recommended, Planned -> Present
  - Absent                                    -> Absent
  - Possible, Hypothetical                    -> Possible
  - Conditional                               -> Conditional
  - Notassociated, "Not associated"           -> Notassociated
type_comparison: exact UMLS semantic type string
value_comparison: exact string after .strip() (case-sensitive)
unit_comparison: exact string after .strip().lower()
added_rows: annotator-added rows (term_index = NaN) are reported as counts but excluded from κ
           (no reliable cross-annotator alignment key for them; documented in §10)
f1_definition: treat one annotator's "kept" set as reference, other as predicted, micro-F1 over
              term_index set per note; symmetrized (mean of A-as-ref and B-as-ref, which are equal
              by F1 symmetry)
bootstrap_ci: none in EXP-A (95% CI by stratified bootstrap is EXP-B; EXP-A gives point estimates
              + per-note breakdown so EXP-B can reuse).
```

## 7. 数据 / 输入模型快照

- **Cross-annotation packages**:
  - `papers/BMJ_AI_Submission/Major Revision/cross-annotation/For_Mo_IAA_cross_annotation.zip`
    — 3 4CE (KUMC_7, report03, report04) + 2 CORAL-pdac (7, 17) AI drafts
  - `papers/BMJ_AI_Submission/Major Revision/cross-annotation/For_Enci_IAA_cross_annotation.zip`
    — 3 4CE (BCH_6, COL_4, KUMC_1) + 1 CORAL-pdac (14) + 1 CORAL-breastca (38) AI drafts
- **Re-annotated returns**:
  - `papers/.../cross-annotation/From Mo_2_Zongxin_Compressed (zipped) Folder.zip` — Mo returned 5/5
  - `papers/.../cross-annotation/To_Zongxin_Enci_add_annotation.zip` — Enci returned 5/5 but **substituted BCH_7 for COL_4**
- **Gold standard** (original annotations):
  - `outputs/reviewed_updated2/4CE/{KUMC_7,report03,report04,BCH_6,KUMC_1}_updated.csv`
  - `outputs/reviewed_updated2/coral_annotated_pdac/{7,17,14}_updated.csv`
  - `outputs/reviewed_updated2/coral_annotated_breastca/38_updated.csv`
- **⚠ Missing gold standard** (blocker noted in §10): COL_4 and BCH_7 are NOT in
  `reviewed_updated2/4CE/` → Enci's BCH_7 re-annotation cannot be paired with a
  Mo-original gold; treated as **unpaired** + excluded from κ/F1, count
  reported separately. COL_4 task was not returned by Enci so trivially excluded.
- **agent_type column note**: Mo's drafts came from `deepseek`, Enci's drafts
  came from `gpt4o` + `llama` (column in CSV indicates AI draft source). Per
  user constraint, this is **not** a basis to exclude any data — IAA's unit is
  the **annotator's review decision** regardless of which AI generated the
  draft.

---

## 8. 结果

Aggregate per-dataset metrics (labels pooled across all paired notes; AI-draft
``term_index`` is the unit of agreement; F1 is symmetric in A,B by construction):

| Split    | n_pairs | n_draft | n_kept_both | **κ_entity (keep/drop)** | **F1_entity** | **κ_assertion** | κ_type | value_agreement | unit_agreement |
|----------|--------:|--------:|------------:|--------------------------:|--------------:|----------------:|-------:|----------------:|---------------:|
| Overall  | 9       | 3,534   | 1,940       | **0.401**                 | **0.807**     | **0.794**       | 0.952  | 0.701           | 0.956          |
| 4CE      | 5       | 1,372   | 784         | **0.294**                 | **0.797**     | **0.691**       | 0.883  | 0.679           | 0.920          |
| CORAL    | 4       | 2,162   | 1,156       | **0.461**                 | **0.814**     | **0.853**       | 0.998  | 0.715           | 0.981          |

F1-entity components (overall): TP=1940, FP=594, FN=333, TN=667; P=0.766, R=0.854.

Per-note breakdown (`runs/EXP-A/per_note_breakdown.csv`):

| Dataset | Note         | Orig | Cross | n_draft | n_kept_A | n_kept_B | n_both | κ_keep | F1_keep | κ_assert | κ_type | val_agr | unit_agr |
|---------|--------------|------|-------|--------:|---------:|---------:|-------:|-------:|--------:|---------:|-------:|--------:|---------:|
| 4CE     | KUMC_7       | Enci | Mo    | 371     | 150      | 284      | 145    | 0.295  | 0.668   | 0.773    | 1.000  | 0.669   | 0.972    |
| 4CE     | report03     | Enci | Mo    | 334     | 252      | 280      | 237    | 0.470  | 0.891   | 0.842    | 1.000  | 0.717   | 0.966    |
| 4CE     | report04     | Enci | Mo    | 299     | 203      | 250      | 184    | 0.251  | 0.812   | 0.860    | 1.000  | 0.717   | 0.984    |
| 4CE     | BCH_6        | Mo   | Enci  | 178     | 148      | 141      | 124    | 0.248  | 0.858   | 0.765    | 0.991  | 0.823   | 0.984    |
| 4CE     | KUMC_1       | Mo   | Enci  | 190     | 149      | 111      | 94     | 0.162  | 0.723   | **−0.015** | **0.018** | 0.330 | 0.511 |
| CORAL   | pdac_7       | Enci | Mo    | 554     | 398      | 444      | 358    | 0.383  | 0.850   | 0.940    | 0.997  | 0.662   | 0.989    |
| CORAL   | pdac_17      | Enci | Mo    | 443     | 275      | 286      | 254    | 0.743  | 0.906   | 0.664    | 0.996  | 0.839   | 0.988    |
| CORAL   | pdac_14      | Mo   | Enci  | 656     | 407      | 457      | 340    | 0.380  | 0.787   | 0.900    | 1.000  | 0.679   | 0.974    |
| CORAL   | breastca_38  | Mo   | Enci  | 509     | 291      | 281      | 204    | 0.346  | 0.713   | 0.829    | 1.000  | 0.716   | 0.971    |

sklearn `classification_report` on collapsed assertion (kept-by-both rows,
A as ref / B as predicted), pooled overall:

```
               precision    recall  f1-score   support
       Absent     0.8907    0.9233    0.9067       300
  Conditional     0.6076    0.7059    0.6531        68
Notassociated     0.6562    0.6000    0.6269        70
     Possible     0.6778    0.7531    0.7135        81
      Present     0.9563    0.9395    0.9478      1421
     accuracy                         0.9088      1940
    macro avg     0.7577    0.7844    0.7696      1940
 weighted avg     0.9115    0.9088    0.9098      1940
```

Annotator-added rows (`term_index = NaN`, excluded from κ/F1; reported for §10
transparency): original-annotator side n=15, cross-annotator side n=32 across
all 9 pairs.

Unpaired notes:
- **4CE/BCH_7**: Enci substituted BCH_7 for the originally-assigned COL_4; no
  Mo-original gold in `outputs/reviewed_updated2/4CE/` → excluded from κ/F1.
- **4CE/COL_4**: Originally assigned to Enci but never returned (substituted) →
  no cross-annotation available.

## 9. vs baseline 对比

N/A — first baseline experiment in BMJ revision suite.

The numbers compare implicitly against the **literature convention** used by
clinical NER IAA papers (i2b2-2010, ClinicalTrials.gov):

- Cohen's κ on entity-level keep/drop = **0.29 (4CE) / 0.46 (CORAL)** → ranges
  Landis & Koch (1977) interpret as "fair" to "moderate". The 4CE figure is
  conservative; the CORAL figure is in the typical "moderate" band reported in
  the literature for fine-grained clinical concept agreement.
- F1-entity = **0.80 (4CE) / 0.81 (CORAL)** → strong overlap, comparable to
  i2b2-2010 published IAA F1 in the 0.75-0.90 range (Uzuner 2011 JAMIA 18(5)).
- κ_assertion (kept-by-both) = **0.69 (4CE) / 0.85 (CORAL)** → "substantial"
  agreement (Landis & Koch) on the polarity decision.

## 10. 分析

### Key observations

1. **κ_entity is lower than F1_entity because of class imbalance.** Among the
   AI-draft rows, the "kept by both" cell dominates (TP=1940) and "neither
   kept" is also frequent (TN=667), but "only-one-kept" cells (FP=594, FN=333)
   pull κ down. With ~80% raw agreement and a baseline-prevalence-weighted
   chance agreement also high, the κ correction reduces the value substantially
   (κ = (p_o − p_e) / (1 − p_e)). This is a known property of κ on imbalanced
   binary decisions and is consistent with the F1 = 0.81 number that better
   reflects practical inter-rater agreement on what content to keep.

2. **κ_type is misleadingly high (CORAL κ_type = 0.998).** Spot-check confirms
   annotators almost never edit the AI-suggested UMLS semantic type — they
   accept/reject the row but leave the type field alone. So κ_type measures
   "did both annotators leave the AI's type guess unchanged?" rather than
   independent semantic-type judgment. **Recommend Methods report κ_type with
   the caveat or omit it** — value of the metric ≈ 0 for assessing genuine
   annotator agreement.

3. **value_agreement (0.70) and unit_agreement (0.96)** are conditional on both
   keeping the row. Value disagreements are mostly due to one annotator filling
   in a missing value and the other leaving it blank, or different precision /
   formatting. Unit is more standardized hence much higher agreement.

4. **4CE/KUMC_1 outlier (κ_assert = −0.015, κ_type = 0.018, val = 0.33, unit =
   0.51).** Spot-check shows Mo and Enci genuinely disagree on many entities
   (e.g. mention="against her will", Mo: Bird/Absent; Enci: Mental or
   Behavioral Dysfunction/Present). Two likely drivers: (a) KUMC_1 is a
   psychiatric note with ambiguous concept boundaries; (b) one of the
   annotators may have accepted clearly-wrong AI-draft types/assertions
   without editing them. This is the strongest single piece of evidence
   that the "review-style" caveat is needed — annotators sometimes accept
   AI errors that another annotator would flag. The note is **kept in
   the analysis**: removing outliers post-hoc would be cherry-picking.

5. **CORAL κ > 4CE κ across all three metrics.** Plausible reason: CORAL
   (oncology) has more standardized clinical vocabulary (drugs, procedures,
   findings); 4CE includes more nursing-/discharge-style narrative with
   ambiguous "Notassociated" rows (e.g. section headers like "ADMISSION
   DATE", "NAME"). The 4CE Notassociated class has the worst per-class F1
   (0.40-0.63 across splits), confirming this driver.

### Pre-flagged caveats (now confirmed)

1. **Review-style, not blind double annotation**: Both annotators worked from
   the same AI-suggested draft. κ reflects acceptance/rejection/edit agreement
   on AI suggestions, not de-novo agreement on free text. **Methods must state
   this explicitly** — recommended wording:
   > "For inter-annotator agreement, both annotators independently reviewed the
   > same AI-suggested draft annotation (presented without the other
   > annotator's labels). Cohen's κ and F1-based agreement therefore reflect
   > the consistency of acceptance, rejection, and editing decisions on
   > AI-generated drafts, not de-novo agreement on free-text mark-up. We
   > consider this an honest measure of the annotation workflow our pipeline
   > supports in practice."

2. **BCH_7 ↔ COL_4 substitution**: Enci re-annotated BCH_7 instead of
   COL_4. Confirmed BCH_7 has no Mo-original gold; excluded from κ/F1.
   n_pairs(4CE) = 5 instead of planned 6 (Mo's 3 paired + Enci's 2 paired).
   Total n_pairs = 9.

3. **CORAL-Breast n=1 (note 38)**: Below 10% (n=1/13≈8%). Per user decision
   CORAL is reported merged (Breast + Pancreas, total n=4 / 29 = 14%), so the
   merged stat is above the reviewer's ≥10% threshold.

4. **Added rows (term_index = NaN)**: 15 (original side) + 32 (cross side) =
   47 added rows across 9 pairs, none aligned cross-annotator. This is a
   known underestimate of disagreement; reported as counts.

## 11. 结论

**PASS** (with caveats). Numbers are reportable for R5 A2 hard requirement:
**Cohen's κ_entity = 0.29 (4CE) / 0.46 (CORAL) / 0.40 (overall); F1_entity =
0.80 (4CE) / 0.81 (CORAL); κ_assertion = 0.69 / 0.85 / 0.79**. Methods must
clearly state the review-style design.

## 12. 下一步

1. Author Methods §3.3 "Annotation reliability" subsection (W-18 in
   `RESPONSE_PLAN.md` §3.3) using the recommended wording in §10 caveat #1.
2. Decide whether to report κ_type or replace it with raw type-agreement rate
   given the §10 #2 caveat (recommend: report raw agreement rate, omit κ_type,
   or footnote the limitation).
3. Forward per-note breakdown to EXP-B for bootstrap CI on these κ/F1 values
   if reviewer expects CIs on IAA (R1 M2 spirit).
4. Forward KUMC_1 outlier example to EXP-E hallucination taxonomy as a
   real-world case where two annotators inconsistently corrected an AI error.
5. (Optional, lower priority) Ask Enci for one additional CORAL-Breast
   cross-annotation to lift CORAL-Breast above 10% standalone (currently 8%);
   only needed if reviewer asks for sub-dataset breakdown.

## 13. Artifact pointers

(All paths relative to project root unless noted; absolute paths via
`readlink -f` for forensic.)

- `runs/EXP-A/metrics.json` — per-dataset Cohen's κ + F1 numbers + config (no PHI; **committed**)
- `runs/EXP-A/per_note_breakdown.csv` — counts + κ + F1 per (note, pair) (no PHI: only note IDs + numbers; **committed**)
- `runs/EXP-A/pair_manifest.csv` — pair status (paired / unpaired-with-reason; no PHI; **committed**)
- `runs/EXP-A/report.txt` — human-readable summary with sklearn-style classification reports (no PHI; **committed**)
- `runs/EXP-A/_unzipped/` — intermediate unzip of cross-annotation packages **(contains PHI; gitignored by `runs/`; do NOT commit, do NOT rsync outside project)**
- `runs/EXP-A/snapshot/git_info.txt` — `N/A: snapshot writer 未实现, 见 EXPERIMENTS.md banner; git 信息见字段 1`
- `runs/EXP-A/snapshot/config_resolved.yaml` — `N/A: snapshot writer 未实现; config 见字段 6 inline copy`
- `runs/EXP-A/snapshot/env.txt` — `N/A: snapshot writer 未实现, 无 fallback`
- `scripts/iaa/compute_iaa.py` + `scripts/iaa/iaa_utils.py` — analysis code (**committed**)

---

## 更新日志

- 2026-05-25: launch — scaffold .md + scripts on branch `exp/EXP-A_iaa_cohen_kappa`.
- 2026-05-25: run — computed IAA on 9 paired notes (4CE n=5 / CORAL n=4); 2 unpaired (BCH_7 / COL_4). Backfilled §8-13. Status: **PASS**.
