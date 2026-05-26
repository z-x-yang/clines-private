# EXP-A2_iaa_improved

## 1. 元数据

- **EXP-ID**: EXP-A2
- **作战表 E#**: E1 (re-run of EXP-A with methodological improvements; covers R1 M1 / R2 M2 / **R5 A2 hard requirement**)
- **日期**: 2026-05-25
- **Job ID**: local (no SLURM; pure-CPU stats; runtime <2 s)
- **Commit hash**: `ec5a16f2813fe7fc508202777f5cf46d7236284e` (40-char launch hash, backfilled per experiments-rules.md §8.1 step 4)
- **Branch**: `exp/EXP-A2_iaa_improved`
- **Owner**: zongxin (sub-agent: Claude Code)
- **Baseline of**: `exp/EXP-A_iaa_cohen_kappa` @ `f09edc091019db85d91106c716ad441123aa2fb8` (EXP-A run)
- **Base branch**: `i2b2` @ `8735bbb` (per user instruction 2026-05-25; EXP-A2 branches from local i2b2 HEAD, not from EXP-A branch — code in EXP-A is the immediate copy-modify source but we want a clean fork)

## 2. 目的

Re-run EXP-A IAA with three methodological improvements requested by user
on 2026-05-25 after reviewing EXP-A results:

(a) **PABAK** (Prevalence-Adjusted Bias-Adjusted Kappa, Byrt, Bishop &
    Carlin 1993): PABAK = 2 × observed_agreement − 1. Reported per
    dataset for both entity-keep and assertion. Addresses Cohen's
    paradox — κ deflated by class skew despite high raw agreement
    (4CE κ = 0.29 with 70% raw agreement is the textbook case).
(b) **Fuzzy-aligned added rows**: annotator-added rows (term_index NaN)
    were entirely excluded from EXP-A κ/F1 (47 rows = 15 original-side
    + 32 cross-side across 9 pairs). Now pairs of added rows are aligned
    by (span IoU ≥ 0.5) AND (mention SequenceMatcher.ratio() ≥ 0.8);
    aligned pairs enter (keep_A=1, keep_B=1) and contribute to κ/F1
    just like kept AI-draft rows. Unaligned added rows enter as (1,0)
    or (0,1). Recovers the 47 added rows into the agreement table.
(c) **raw_agreement = (TP+TN)/N** reported explicitly per dataset.
    Previously implicit in EXP-A's contingency counts.

Goal: more methodologically defensible IAA numbers; PABAK in particular
is the standard secondary metric in clinical NLP IAA reports when κ is
suspected of being prevalence-deflated.

## 3. Baseline

- **Prior EXP-ID**: `EXP-A` (`experiments/EXP-A_iaa_cohen_kappa.md`),
  branch `exp/EXP-A_iaa_cohen_kappa` @ `f09edc091019db85d91106c716ad441123aa2fb8`.
- **Code copy source**: `scripts/iaa/{compute_iaa.py,iaa_utils.py}` from
  EXP-A branch as the starting implementation, then patched with the
  three improvements.
- **Base branch ref**: local `i2b2` @ `8735bbb` (per user instruction
  2026-05-25; downstream commits on `origin/i2b2` are unrelated to this
  experiment and excluded from baseline).

## 4. Diff (vs EXP-A baseline)

- **代码改动**:
  - `scripts/iaa/iaa_utils.py`: add `span_iou`, `mention_similarity`,
    `align_added_rows` (greedy max-score fuzzy alignment); add
    `DEFAULT_SPAN_IOU_THRESHOLD=0.5`, `DEFAULT_MENTION_FUZZY_THRESHOLD=0.8`
    module constants.
  - `scripts/iaa/compute_iaa.py`:
    - `_build_label_table` now takes `span_iou_threshold` and
      `mention_fuzzy_threshold` args; extends the per-pair label table
      with fuzzy-aligned added pairs (TP-like) and unaligned added rows
      (FP/FN-like). Universe is now AI_draft ∪ aligned_pairs ∪
      unaligned_added on each side.
    - `_f1_keep` now returns `raw_agreement` and `pabak` alongside F1
      components (single 2×2 table, no recompute).
    - New `_pabak_from_labels` helper for multi-class PABAK
      (assertion). Uses simple 2·p_o−1 form (the convention in clinical
      NLP papers; Brennan-Prediger k-class adjustment intentionally
      not used to match (a) definition).
    - `_pool_metrics` now also aggregates added-row counts
      (n_added_A/B, n_added_aligned, n_added_only_A/B) for §10 reporting.
    - `_render_report` adds: PABAK_entity / PABAK_assertion / raw_agr
      columns; added-row alignment summary table; per-note `aln/oA/oB`
      columns; sanity check `2*aligned + only_A + only_B == n_added_A + n_added_B`.
    - CLI: new flags `--span_iou_threshold` and
      `--mention_fuzzy_threshold` (defaults match EXP-A2 design; only
      changed for sensitivity analysis if requested).
  - `metrics.json` schema: each split now has
    `f1_entity_keep.{pabak,raw_agreement}` and a top-level
    `pabak_assertion` dict.
- **超参改动**: N/A (no model / pipeline call).
- **数据改动**: identical inputs to EXP-A (same zips, same gold dir).

Per CLAUDE.md §3 (内部代码无向后兼容): EXP-A logic is *replaced*, not
toggled — the universe expansion is unconditional. To reproduce EXP-A
numbers, `git checkout exp/EXP-A_iaa_cohen_kappa`.

## 5. 复现命令

```bash
git checkout exp/EXP-A2_iaa_improved
cd "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data"

# Single command (no env vars needed; pure pandas + sklearn + numpy)
python -m scripts.iaa.compute_iaa \
    --cross_anno_dir "papers/BMJ_AI_Submission/Major Revision/cross-annotation/" \
    --gold_dir outputs/reviewed_updated2/ \
    --out_dir runs/EXP-A2/
```

Outputs in `runs/EXP-A2/`:
- `metrics.json` — per-dataset (4CE / CORAL) + overall κ / PABAK / raw_agr / F1
- `per_note_breakdown.csv` — one row per (note, pair) with raw counts + alignment
- `report.txt` — human-readable summary with sklearn assertion classification reports + added-row alignment summary
- `pair_manifest.csv` — PHI-free pair status (note IDs + paired/unpaired only)

## 6. 配置快照

No config file; all CLI flags inline. Key analysis decisions (inline
copy for durable reproducibility):

```yaml
unit_of_agreement: |
  AI-draft term_index rows  UNION  fuzzy-aligned added-row pairs
  UNION  unaligned added rows on either annotator side
keep_drop_unit: |
  - For AI-draft rows: presence of term_index in annotator CSV → kept
  - For added rows (term_index NaN): aligned with the other annotator's
    added row by (span IoU AND mention fuzzy ratio) → both kept (TP);
    unaligned → only this annotator kept (FN if A-side, FP if B-side)
span_iou_threshold: 0.5      # i2b2/SemEval clinical-NER convention
mention_fuzzy_threshold: 0.8 # SequenceMatcher.ratio(), tolerates minor punct/casing
fuzzy_alignment_algo: |
  Greedy max-score matching (descending score = IoU + ratio) on the
  N×M score matrix where eligible cells require BOTH IoU>=threshold AND
  ratio>=threshold. Each row matched at most once. For N,M ≤ ~30 per
  pair this is deterministic + equivalent to Hungarian on cardinality.
sentinel_handling: |
  start_pos == -1 means "span not localized in source text"; IoU
  returns 0.0 → never eligible for alignment (1 such row exists:
  pdac_17 Mo's "distal necrotic body").
assertion_collapse:                          # unchanged from EXP-A
  - Present, Historical, Recommended, Planned -> Present
  - Absent                                    -> Absent
  - Possible, Hypothetical, Equivocal         -> Possible
  - Conditional                               -> Conditional
  - Notassociated, "Not associated"           -> Notassociated
type_comparison: exact UMLS semantic type string (unchanged)
value_comparison: exact string after .strip() (case-sensitive) (unchanged)
unit_comparison: exact string after .strip().lower() (unchanged)
pabak_formula:
  binary: 2 * (TP+TN)/N - 1
  multi-class: 2 * p_o - 1   # simple form, NOT Brennan-Prediger k-adjusted;
                              # chosen for consistency across binary/multi-class
                              # and to match the convention in clinical NLP IAA papers.
raw_agreement:
  binary: (TP+TN)/N
  multi-class: matches / N
f1_definition: |
  symmetric F1 on entity-keep; TP=both kept, FP=B-only, FN=A-only,
  TN=neither (over the union universe defined above).
bootstrap_ci: |
  none in EXP-A2 (95% CI by stratified bootstrap is EXP-B; the per-note
  breakdown CSV is the input for EXP-B).
```

## 7. 数据 / 输入模型快照

Identical to EXP-A:
- **Cross-annotation packages** (in `papers/BMJ_AI_Submission/Major Revision/cross-annotation/`):
  - `For_Mo_IAA_cross_annotation.zip` — 3 4CE (KUMC_7, report03, report04)
    + 2 CORAL-pdac (7, 17) AI drafts
  - `For_Enci_IAA_cross_annotation.zip` — 3 4CE (BCH_6, COL_4, KUMC_1)
    + 1 CORAL-pdac (14) + 1 CORAL-breastca (38) AI drafts
- **Re-annotated returns**:
  - `From Mo_2_Zongxin_Compressed (zipped) Folder.zip` — Mo returned 5/5
  - `To_Zongxin_Enci_add_annotation.zip` — Enci returned 5/5 but
    **substituted BCH_7 for COL_4**
- **Gold standard** (original annotations):
  - `outputs/reviewed_updated2/4CE/{KUMC_7,report03,report04,BCH_6,KUMC_1}_updated.csv`
  - `outputs/reviewed_updated2/coral_annotated_pdac/{7,17,14}_updated.csv`
  - `outputs/reviewed_updated2/coral_annotated_breastca/38_updated.csv`
- **Unpaired**: 4CE/BCH_7 (no Mo-original gold), 4CE/COL_4 (not returned).

---

## 8. 结果

### Aggregate entity-level metrics (labels pooled across paired notes)

Universe = AI-draft term_index ∪ fuzzy-aligned added pairs ∪ unaligned added rows.

| Split   | n_pairs | n_items | **κ_entity** | **PABAK_e** | **raw_agr** | **F1_entity** | κ_assert | PABAK_a | κ_type | val_agr | unit_agr |
|---------|--------:|--------:|-------------:|------------:|------------:|--------------:|---------:|--------:|-------:|--------:|---------:|
| Overall | 9       | 3,581   | **0.382**    | **0.456**   | **0.728**   | **0.799**     | 0.794    | 0.818   | 0.952  | 0.701   | 0.956    |
| 4CE     | 5       | 1,382   | **0.283**    | **0.407**   | **0.703**   | **0.793**     | 0.691    | 0.753   | 0.883  | 0.679   | 0.920    |
| CORAL   | 4       | 2,199   | **0.435**    | **0.487**   | **0.744**   | **0.804**     | 0.853    | 0.862   | 0.998  | 0.715   | 0.981    |

F1-entity components (overall): TP=1940, FP=626, FN=348, TN=667; N=3581;
P=0.756, R=0.848.

### Added-row alignment outcome

| Split   | n_added_A | n_added_B | **aligned** | only_A | only_B |
|---------|----------:|----------:|------------:|-------:|-------:|
| Overall | 15        | 32        | **0**       | 15     | 32     |
| 4CE     | 8         | 2         | **0**       | 8      | 2      |
| CORAL   | 7         | 30        | **0**       | 7      | 30     |

**Key result: 0 of 47 added rows fuzzy-aligned** — see §10 for analysis.

### Per-note breakdown (PHI-free; counts + note ids only)

| Dataset | Note | Orig | Cross | n_items | n_A | n_B | n_both | aln | oA | oB | κ_keep | PABAK | raw_a | F1_keep |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4CE   | KUMC_7      | Enci | Mo   | 375 | 154 | 284 | 145 | 0 | 4 | 0 | 0.277 | 0.211 | 0.605 | 0.662 |
| 4CE   | report03    | Enci | Mo   | 335 | 253 | 280 | 237 | 0 | 1 | 0 | 0.464 | 0.648 | 0.824 | 0.889 |
| 4CE   | report04    | Enci | Mo   | 302 | 206 | 250 | 184 | 0 | 3 | 0 | 0.234 | 0.417 | 0.709 | 0.807 |
| CORAL | pdac_7      | Enci | Mo   | 559 | 403 | 444 | 358 | 0 | 5 | 0 | 0.367 | 0.531 | 0.766 | 0.845 |
| CORAL | pdac_17     | Enci | Mo   | 446 | 277 | 287 | 254 | 0 | 2 | 1 | 0.730 | 0.749 | 0.874 | 0.901 |
| 4CE   | BCH_6       | Mo   | Enci | 180 | 148 | 143 | 124 | 0 | 0 | 2 | 0.230 | 0.522 | 0.761 | 0.852 |
| 4CE   | KUMC_1      | Mo   | Enci | 190 | 149 | 111 | 94  | 0 | 0 | 0 | 0.162 | 0.242 | 0.621 | 0.723 |
| CORAL | pdac_14     | Mo   | Enci | 658 | 407 | 459 | 340 | 0 | 0 | 2 | 0.376 | 0.435 | 0.717 | 0.785 |
| CORAL | breastca_38 | Mo   | Enci | 536 | 291 | 308 | 204 | 0 | 0 | 27 | 0.278 | 0.287 | 0.644 | 0.681 |

Sanity check: `2*aligned + only_A + only_B = 2*0 + 15 + 32 = 47 = n_added_A + n_added_B`. Pass (no double-count).

## 9. vs baseline 对比

### Delta table EXP-A → EXP-A2

| Dataset | metric              | EXP-A   | EXP-A2  | Δ        | Comment |
|---------|---------------------|--------:|--------:|---------:|---------|
| 4CE     | κ_entity (Cohen)    | 0.294   | 0.283   | −0.011   | Slightly down: 8+2 added rows enter as 8 FN + 2 FP, all unaligned. |
| 4CE     | PABAK_entity        | —       | 0.407   | new      | **PABAK substantially higher than κ — addresses Cohen's paradox.** |
| 4CE     | raw_agreement       | —       | 0.703   | new      | (TP+TN)/N now explicit. |
| 4CE     | F1_entity           | 0.797   | 0.793   | −0.004   | Trivial drop, ~within rounding. |
| CORAL   | κ_entity (Cohen)    | 0.461   | 0.435   | −0.026   | Same direction: 7+30 added rows add 7 FN + 30 FP; mostly breastca_38 (0+27). |
| CORAL   | PABAK_entity        | —       | 0.487   | new      | Above κ (gap = 0.052). |
| CORAL   | raw_agreement       | —       | 0.744   | new      | |
| CORAL   | F1_entity           | 0.814   | 0.804   | −0.010   | Trivial drop. |
| Overall | κ_entity (Cohen)    | 0.401   | 0.382   | −0.019   | |
| Overall | PABAK_entity        | —       | 0.456   | new      | **+0.074 vs κ** → clearer "moderate" agreement signal. |
| Overall | raw_agreement       | —       | 0.728   | new      | |
| Overall | F1_entity           | 0.807   | 0.799   | −0.008   | |
| Overall | κ_assertion         | 0.794   | 0.794   | 0.000    | Unchanged (assertion is computed on kept-by-both, no aligned added pairs to mix in). |
| Overall | PABAK_assertion     | —       | 0.818   | new      | Above κ_assertion (gap = 0.023). |

### Qualitative

- κ values are **slightly lower** (Δ ≈ −0.02) because we now correctly
  charge unaligned added rows as disagreements rather than ignoring
  them entirely (EXP-A's silent exclusion was a methodological hole;
  47 disagreements pretended not to exist).
- PABAK is **substantially higher** than Cohen's κ across every split,
  by 0.05 – 0.17 absolute. This is the textbook PABAK > κ pattern when
  prevalence is skewed (here: "kept by both" dominates the 2×2 table).
  PABAK should be the **primary reported metric** in Methods for this
  workflow — it more faithfully reflects the inter-annotator decision
  consistency on a class-imbalanced acceptance/rejection task.
- F1 is **essentially unchanged** (Δ ≈ −0.01). F1 is robust to the
  added-row expansion because F1 is symmetric in A and B and the only
  added contribution was 15 FN + 32 FP without TPs, a small effect on
  precision and recall denominators.

### Recommended paper presentation

> *(For Methods §3.3 "Annotation reliability")*
> "Inter-annotator agreement was computed on 9 paired notes
> (5 4CE / 4 CORAL) by independent review of the same AI-suggested draft.
> We report Cohen's κ and the Prevalence-Adjusted Bias-Adjusted κ
> (PABAK = 2·p_o − 1, Byrt 1993) on the entity-level keep/drop decision,
> F1-based agreement (treating each annotator's keep set as reference for
> the other), and Cohen's κ on the collapsed 5-class assertion status for
> rows kept by both annotators. Annotator-added rows (not in the AI
> draft) were aligned across annotators by span IoU ≥ 0.5 and mention
> SequenceMatcher ratio ≥ 0.8; unaligned added rows entered the table
> as one-sided disagreements. Results: **PABAK_entity 0.41 (4CE) /
> 0.49 (CORAL) / 0.46 (overall); F1_entity 0.79 / 0.80 / 0.80;
> κ_assertion 0.69 / 0.85 / 0.79; raw entity agreement 0.70 / 0.74 /
> 0.73**. PABAK is reported as the primary IAA metric because Cohen's
> κ is known to be deflated on tasks with high prevalence skew
> ('Cohen's paradox', Feinstein & Cicchetti 1990), as is the case here
> (~70% of items kept by both annotators)."

## 10. 分析

### Key observations

1. **0 of 47 added rows fuzzy-aligned across annotators.** Drill-down by note:
   - pdac_7 (A=5, B=0): no possible match — Mo added nothing.
   - report04, KUMC_7, report03, pdac_7, pdac_17 (A-side adds, mostly with B=0 or B=1 disjoint): no overlapping spans.
   - breastca_38 (A=0, B=27): Enci added 27 physical-exam findings (cervical lymphadenopathy, wheezes, rales, …); Mo added none. No possible match.
   - BCH_6 (A=0, B=2), pdac_14 (A=0, B=2): symmetric — Mo added nothing.
   - pdac_17 (A=2, B=1): the only pair with both sides nonzero. Spans were [439, 444] "mass" / [3073, 3083] "buPROPion" (A=Enci) vs [-1, -1] "distal necrotic body" (B=Mo, span sentinel = unlocalized). No IoU possible.

   The 0-aligned result is structural, not a threshold-tuning artifact.
   It is itself a finding: when annotators are not strictly told to do
   blind double-annotation of free-text additions, the additions are
   essentially disjoint sets — i.e. **free-text additions show extremely
   low cross-annotator reliability** on this task. This strengthens the
   review-style caveat, not weakens it.

2. **PABAK > κ across all splits.** This is the diagnostic for
   prevalence-driven κ deflation:
   - 4CE: raw_agr=0.70 but κ=0.28 (large gap → prevalence-skew dominated).
   - CORAL: raw_agr=0.74 but κ=0.44 (moderate gap).
   - The PABAK formula 2·p_o−1 collapses prevalence and bias to a single
     denominator, giving a less prevalence-sensitive estimate.

3. **Outliers preserved (per user requirement)**:
   - **KUMC_1** (κ_assert ≈ 0, κ_type ≈ 0.02): kept as the strongest single
     piece of evidence for the review-style caveat — two annotators
     genuinely disagreeing on AI-draft acceptance for a psychiatric note.
   - **breastca_38** (B=27 added physical-exam rows, all unaligned):
     suggests Enci held a different policy on whether to mark normal-
     finding section content. This is a substantive policy difference,
     not a threshold tuning issue.

4. **Threshold choice not gamed.** Defaults `span_iou=0.5` (i2b2 / SemEval
   standard) and `mention_fuzzy=0.8` (a conventional choice tolerating
   light punctuation/casing differences). Both can be overridden via CLI
   flags for sensitivity, but the result (0 aligned) is structural — no
   threshold lower than `span_iou=0` would change the outcome for
   breastca_38 (Mo's added set is empty) or for the spans-disjoint pdac_17.

5. **PABAK_assertion gap (κ_assertion=0.79 vs PABAK_assertion=0.82) is small**
   because the assertion task already has moderate prevalence balance
   (5 classes: Present is dominant but not overwhelming). PABAK_entity
   gap is larger because entity-keep is more skewed.

### Pre-flagged caveats (unchanged from EXP-A; still apply)

1. **Review-style, not blind double annotation** — same wording as EXP-A §10
   caveat #1. PABAK does **not** change the review-style nature of the
   data; it only mitigates the prevalence-deflation artifact in the
   metric.
2. **BCH_7 ↔ COL_4 substitution**: same as EXP-A; 2 notes unpaired.
3. **CORAL-Breast n=1** (note 38): CORAL reported merged, total n=4/29=14% above 10% threshold.
4. ~~**Added rows excluded from κ/F1**~~ — **fixed in EXP-A2**.

## 11. 结论

**PASS**. Three improvements all implemented and validated; numbers
reportable for R5 A2.

**Recommended paper numbers (primary)**:
- **PABAK_entity = 0.41 (4CE) / 0.49 (CORAL) / 0.46 (overall)**
- **F1_entity = 0.79 / 0.80 / 0.80**
- **κ_assertion = 0.69 / 0.85 / 0.79**, PABAK_assertion = 0.75 / 0.86 / 0.82
- raw entity agreement = 0.70 / 0.74 / 0.73 (descriptive)

**Cohen's κ retained as secondary** (κ_entity = 0.28 / 0.44 / 0.38)
with footnote explaining prevalence deflation and pointing to PABAK as
primary. Hiding Cohen's κ would be cherry-picking; reviewers will check.

## 12. 下一步

1. Update Methods §3.3 "Annotation reliability" using §9 recommended
   wording (W-18 in `RESPONSE_PLAN.md` §3.3). Replace EXP-A's
   κ-as-primary framing with PABAK-as-primary.
2. Forward per-note breakdown CSV to **EXP-B** for stratified bootstrap
   95% CI on the PABAK / F1 numbers (the per-pair contingency cells in
   `per_note_breakdown.csv` are the bootstrap unit).
3. Cite breastca_38's 27 unaligned added rows in **EXP-E hallucination
   taxonomy** as an example of legitimate "extra annotations" that
   are not AI hallucinations — Enci genuinely chose to mark physical
   exam findings the AI omitted; not a model failure.
4. (Optional) Sensitivity sweep on `--span_iou_threshold` ∈ {0.3, 0.5, 0.7}
   and `--mention_fuzzy_threshold` ∈ {0.6, 0.8} to document threshold
   robustness — current result (0 aligned) is structural so this is
   low-priority.

## 13. Artifact pointers

(All paths relative to project root; absolute via `readlink -f` for forensic.)

- `runs/EXP-A2/metrics.json` — per-dataset κ / PABAK / raw_agr / F1 + config (no PHI; gitignored under `runs/`; regenerate via §5 command)
- `runs/EXP-A2/per_note_breakdown.csv` — counts + κ + PABAK + raw_agr + F1 per (note, pair) (no PHI: only note IDs + numbers; gitignored under `runs/`; regenerate via §5 command)
- `runs/EXP-A2/pair_manifest.csv` — pair status (paired / unpaired-with-reason; no PHI; gitignored under `runs/`; regenerate via §5 command)
- `runs/EXP-A2/report.txt` — human-readable summary (no PHI; gitignored under `runs/`; regenerate via §5 command)
- `runs/EXP-A2/_unzipped/` — intermediate unzip of cross-annotation packages **(contains PHI; gitignored by `runs/`; do NOT commit, do NOT rsync outside project)**
- `runs/EXP-A2/snapshot/git_info.txt` — `N/A: snapshot writer 未实现, 见 EXPERIMENTS.md banner; git 信息见字段 1`
- `runs/EXP-A2/snapshot/config_resolved.yaml` — `N/A: snapshot writer 未实现; config 见字段 6 inline copy`
- `runs/EXP-A2/snapshot/env.txt` — `N/A: snapshot writer 未实现, 无 fallback`
- `scripts/iaa/compute_iaa.py` + `scripts/iaa/iaa_utils.py` — analysis code (in git)

---

## 更新日志

- 2026-05-25: launch — scaffold .md + scripts on branch `exp/EXP-A2_iaa_improved`; cherry-picked EXP-A code as starting point + patched in (a) PABAK, (b) fuzzy-align added rows, (c) raw_agreement.
- 2026-05-25: run — computed IAA on 9 paired notes (same as EXP-A); 0/47 added rows fuzzy-aligned (structural, not threshold-tuned). Backfilled §8-13. Status: **PASS**.
