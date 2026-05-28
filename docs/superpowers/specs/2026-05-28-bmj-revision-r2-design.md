# CLINES BMJ Revision R2 — Design

**Manuscript**: `bmjdh-2026-000027` · **BMJ DH&AI deadline**: 2026-05-31
**Branch**: `i2b2` (paper subtree under `papers/BMJ_AI_Submission/`)
**Trigger**: User reviewed the 89-page R1 PDF on 2026-05-28 and returned 11 issues across cover letter, manuscript figures, supplement tables, and consistency framing. This spec is the second-round response plan.

## Decisions locked

1. **Summary Box** — keep (reviewer R1.18 + R5.2.1/2 explicitly required it).
2. **DeepSeek-R1** — fully remove from manuscript (user critique mentioned "V3" but grep confirms only R1 appears; treated as typo).
3. **Output consistency 60%** — re-evaluate same outputs with semantic fuzzy matching (SapBERT cos ≥ 0.95) instead of exact span match; no LLM re-run.
4. **Release scope** — unchanged: single-note inference reference impl on GitHub. Drop the over-promise to release `consistency_metrics.json` (no reviewer asked for it).
5. **Cover letter editor name** — `Dr. Paton` (Chris Paton is BMJ DH&AI EiC; "Patton" user wrote = typo).
6. **Cover letter date+editor address block** — keep (standard format); drop only the top author self-introduction block; add centered "Cover Letter" title.
7. **Figures 4/5 redesign scope** — light refresh (Nature-style muted palette, serif font, `constrained_layout`); structure unchanged.
8. **Editor's Comments section in response letter** — remove (Associate Editor gave no independent technical comment, only a standard decision-letter notice; current placeholder reads awkwardly).

## Work packages

Total ~5–6 h. Parallelism noted in last column.

| ID | Scope | Est | Parallel with |
|---|---|---|---|
| WP-A | Cover Letter restructure | 10 m | A/F/G/J |
| WP-B | DeepSeek-R1 full removal (manuscript text + figure captions + supp Table 3 rows) | 1.5 h | F/G/J |
| WP-C | Figure 3 revert + Figure 4/5 redesign (light refresh) | 2–3 h | depends on B |
| WP-D | Model-label swap in Fig 5 + Supp Table 3 per real run identity | 30 m | merge with C3 |
| WP-E | Supp Tables 3/4/5 width fixes | 30 m | after D |
| WP-F | Hallucination §9.1 Table 6 — `\texttt{snake\_case}` → prose categories | 15 m | A/B/G/J |
| WP-G | Consistency semantic-fuzzy re-evaluation + S4 + R5.4.5 backfill + drop over-promise | 1–2 h | A/B/F/J |
| WP-I | Rebuild 4 PDFs, pdfunite, codex adversarial review, deliver | 30 m + review wait | terminal |
| WP-J | Drop Editor's Comments section from Response_to_Reviewers.tex | 5 m | A/B/F/G |

## WP details

### WP-A — Cover_Letter.tex restructure

File: `papers/BMJ_AI_Submission/Major Revision/response/Cover_Letter.tex`

Diff sketch:
- **Delete** lines 11–16 (top `Zongxin Yang, on behalf of all co-authors / DBMI / HMS / Boston / email` block) — the closing signature already lists author names.
- **Add** at top, before any other content: `\begin{center}\Large\bfseries Cover Letter\end{center}\vspace{1em}`.
- **Keep** lines 19–25 (date + editor address `Dr. Chris Paton / Editor in Chief / BMJ Digital Health & AI`) — verify spelling `Paton` (single t, correct).
- **Keep** line 28 "Dear Dr.\ Paton," and everything below.

### WP-B — DeepSeek-R1 removal

Locations (grep-confirmed):

| File | Action |
|---|---|
| `sections/abstract.tex:5` | Drop "and DeepSeek-R1" from open-weight clause |
| `sections/results.tex:3` | Drop DeepSeek-R1 from backbone enumeration and from "marginally ahead of …" |
| `sections/results.tex:5` | Drop "or DeepSeek-R1" |
| `sections/results.tex:11` | Recompute Δ-range against remaining backbones (was "$+0.04$ to $+0.21$ versus DeepSeek-R1, Llama-3.1-405B, and o3-mini"). New range computed from `detailed_metrics.tex` after DeepSeek rows dropped. |
| `sections/results.tex:33` | Drop "the smaller DeepSeek-R1-32B ≈ 0.08 GPU-hours per note" sentence |
| `sections/discussion.tex:7` | Drop "and DeepSeek-R1" |
| `sections/discussion.tex:31` | Rewrite "smaller DeepSeek-R1-32B and the hosted-API backbones" → "the hosted-API backbones" |
| `figures/figure3.tex:5` | Caption: see WP-C1 (backbone list rewritten anyway) |
| `figures/figure5.tex:4` | Caption: drop "versus DeepSeek-R1-32B" |
| `supplement_sections/detailed_metrics.tex:25-28` | Delete the DeepSeek-R1 `\multirow{3}` block (3 data rows) |

`source_code/` keeps `deepseek` references (llm_manager.py, providers/local_llm_provider.py, scripts) — these are optional backend support in the public reference implementation and stay.

### WP-C — Figure 3 / 4 / 5

**C1 · Figure 3 revert**: `figures/figure3.tex`
- Replace `\includegraphics[width=\linewidth]{figures/figure3_abcd.pdf}` + `\includegraphics[width=0.82\linewidth]{figures/figure3_e.pdf}` with a single `\includegraphics[width=\linewidth]{figures/figure3.pdf}`.
- Rewrite caption to match original figure3.pdf content: 4 datasets (MIMIC-III + 4CE + CORAL-Breast + CORAL-Pancreas) panels A–D; panel E = length-performance for CLINES (Llama3.1-405B) + CLINES (GPT-4o) + CLINES (o3-mini-medium) vs Clinical-DistilBERT + Clinical-MobileBERT.
- Side effect: Fig 3 model-label issue auto-resolved (original figure is correct).

**C2 · Figure 4 light refresh**: locate the figure 4 source script under `papers/BMJ_AI_Submission/Major Revision/figure_scripts/` (resolved at impl time)
- `mpl.rcParams['font.family'] = 'serif'`; `mpl.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']`
- Palette: `seaborn.color_palette("colorblind")` with saturation ×0.85
- Layout: `fig, axes = plt.subplots(..., constrained_layout=True)`; per-subpanel `ax.set_title(..., pad=10, loc='left')`
- Remove figure-internal annotation strings (`Top-6 pooled: F1=...`, `20% threshold`, `substantial agreement (Landis-Koch)`, `7,171 candidate FPs`) — move into LaTeX caption
- Figure size 8×6 inch; `dpi=300` for PDF export

**C3 · Figure 5 light refresh + DeepSeek removal + label swap**: locate the figure 5 source script under `papers/BMJ_AI_Submission/Major Revision/figure_scripts/` (resolved at impl time)
- Same palette/font/layout treatment as C2
- Panel (b): drop the DeepSeek 32B GPU-h bar
- Panels (a)/(c)/(d) **model labels remapped to real run identity**:
  - rendered `CLINES (GPT-4o)` → `CLINES (o3-mini-medium)`
  - rendered `Llama-3.1-405B` → `CLINES (GPT-4o)`
  - rendered `o3-mini` → `CLINES (Llama-3.1-405B)`
- Remove figure-internal sub-caption strings (`Hosted LLMs billed in API $...`, `n=2 notes/dataset...`, `no norm.`) — move into LaTeX caption

### WP-D — Model-label swap

Effectively absorbed into WP-C3 for Fig 5; remaining surface = `supplement_sections/detailed_metrics.tex` Table 3.

Re-label per real run identity:
- `GPT-4o-1120` rows (highest F1) → `o3-mini-medium`
- `Llama-3.1-405B-FP8` rows (middle F1) → `GPT-4o`
- `o3-mini` rows (lowest F1) → `Llama-3.1-405B`
- DeepSeek-R1 rows: already deleted in WP-B
- Caption: update backbone enumeration accordingly

Cross-check that any *narrative* numbers cited in `results.tex` (e.g., "code F1 of 0.874 on 4CE" for "CLINES (GPT-4o)") remain numerically attached to the right backbone after the swap; if the highest-F1 backbone is actually o3-mini-medium, results.tex headline numbers shift assignment. Run this cross-check pass before WP-I.

### WP-E — Supp Tables width fix

Three tables overrun page width in current build:
- `detailed_metrics.tex` Table (was Table 3): already `\scriptsize` + `\tabcolsep=3.2pt`. After WP-B deletes 3 rows, still 8 cols × 9 rows. Add `\begin{table}[H]\centering\resizebox{\textwidth}{!}{...}` wrap OR switch to `landscape` via `lscape` package.
- `iaa_detail.tex` Table (was Table 4): 7 cols with arrow notation; `\footnotesize` → drop to `\scriptsize` if needed, or `resizebox`.
- `hallucination.tex` Table (Table 5): 3 cols, currently fits; verify after WP-F rewrite (longer category names).

Default approach: try `\resizebox{\textwidth}{!}{...}` first (1-line change per table); fall back to `\begin{landscape}...\end{landscape}` if shrunk text becomes unreadable.

### WP-F — Hallucination §9.1 prose categories

File: `supplement_sections/hallucination.tex`

In Table 5 (lines 11–27) and in the case-study description list (lines 36–42), replace `\texttt{snake\_case}` category names with prose:

| Current | Replacement |
|---|---|
| `\texttt{not\_an\_error}` (annotation gap) | "Not an error (annotation gap)" |
| `\texttt{wrong\_code}` | "Wrong code" |
| `\texttt{wrong\_assertion}` | "Wrong assertion" |
| `\texttt{wrong\_value}` | "Wrong value" |
| `\texttt{fabricated\_entity}` | "Fabricated entity" |
| `\texttt{span\_boundary\_error}` | "Span-boundary error" |
| `\texttt{wrong\_date}` | "Wrong date" |

Apply consistently across table rows + bold totals + case-study `\item[]` headers.

### WP-G — Consistency semantic fuzzy re-evaluation

Files:
- `runs/EXP-J2/compute_consistency.py` — modify to compute semantic mention identity
- `papers/.../supplement_sections/consistency.tex` — re-fill Results + Table with new numbers
- `papers/.../Major Revision/response/Response_to_Reviewers.tex` (R5.4.5) — update numbers

Algorithm change:
```
for each note:
  collect all mention surface strings from 5 runs
  embed all unique strings with the SapBERT model checkpoint already used by the
    pipeline (load model from same path the NER processor loads; do NOT use
    cache/dense_embed_all.pt which is the precomputed UMLS-dictionary embedding cache)
  build equivalence graph: edge between two mentions if
    (a) SapBERT(cos) ≥ 0.95, OR
    (b) both map to same UMLS CUI (using their assigned codes)
  connected components = semantic-equivalent mention identities
  recompute:
    - mention-set Jaccard with equivalence-class identity
    - code-set Jaccard (unchanged — already CUI-level)
    - per-field stability (group by equivalence class for "matched mention" definition)
```

Expected numbers (rough): mention-set Jaccard ~0.75–0.85; code-set ~0.62 unchanged; per-field ~0.90 unchanged.

Implementation runs locally on O2 worker (no SLURM, ~10–15 min wall clock; mention count is ~10⁴ scale).

S4 / R5.4.5 text updates:
- Replace headline "0.603 mean mention-set Jaccard" with new semantic-Jaccard number + explanatory clause ("matching mentions by semantic equivalence — same UMLS CUI or SapBERT cos ≥ 0.95").
- **Delete** the over-promise sentence: "Per-note Jaccard values and the full distribution of field-cell modal frequencies are released alongside the data and code (`runs/EXP-J2/consistency_metrics.json`)."
- Keep `\label{supp:consistency-field-stability}` and the field-stability table (numbers may shift slightly under semantic equivalence; recompute and refill).

### WP-I — Rebuild + codex + deliver

1. Re-run figure scripts (figure4_*.py, figure5_*.py) under new palette/font/layout → write `figures/figure4.pdf` + `figures/figure5.pdf`.
2. `tectonic` build:
   - `papers/.../Major Revision/response/Cover_Letter.tex`
   - `papers/.../Major Revision/response/Response_to_Reviewers.tex`
   - `papers/.../Submission/CLINES latex bmj/lancet_draft.tex` (revised, blue marks) — main manuscript
   - `papers/.../Submission/CLINES latex bmj/supplement.tex`
3. `pdfunite` → `CLINES_BMJ_Revision_Combined.pdf` in `papers/.../Major Revision/`.
4. Launch codex adversarial review in background (per CLAUDE §6 — this revision touches core narrative + figure data + supplement tables; criteria triggered). User explicitly requested codex review be launched concurrently with PDF delivery.
5. Send PDF to user via SendUserFile (proactive status) — do NOT wait for codex to finish.
6. When codex review completes (could be after PDF is in user's hands), report classified findings (auto-fixed / conflicts with preferences / needs user judgment).

### WP-J — Drop Editor's Comments section

File: `papers/BMJ_AI_Submission/Major Revision/response/Response_to_Reviewers.tex` (around lines 339–343)

Delete the entire trailing block:
```latex
\section*{Editor's Comments}
\reviewer{\textit{[Associate Editor's comments here when provided in writing.]}}
\response{We have addressed all major and minor comments from the five reviewers...}
```

Rationale: Associate Editor gave no independent technical comment in `revision_comments.txt`; the placeholder + generic response reads awkwardly.

## Execution order

1. **Parallel batch 1** (no cross-deps): WP-A, WP-F, WP-J — small mechanical edits
2. **WP-B** — DeepSeek removal sets the stage for figure regen
3. **WP-G** — Consistency re-eval (runs while figures regen)
4. **WP-C** — Figure 3 revert, Figure 4/5 regen
5. **WP-D + WP-E** — Label swap + table width (touching same supp file as WP-B already cleared)
6. **WP-I** — Build PDFs, launch codex review (background), deliver

## Out of scope

- Re-running EXP-J2 with full GPT-4o backbone (user chose semantic-fuzzy path instead)
- Renaming `runs/EXP-J2/` directory or git branch (release scope cancelled the need)
- Adding head-to-head Healthcare NLP / CLEAR empirical comparison (already discussed-only in R5.4.5; not asked)
- Restructuring abstract beyond the BMJ DH&AI headings (already in)

## Risk register

| Risk | Mitigation |
|---|---|
| Semantic-fuzzy still shows <0.75 mention-set Jaccard | Fallback narrative emphasising 0.62 code-set + 0.90 field-stability already prepared; no separate code change needed |
| Codex review surfaces blocking issue post-build | Standard CLAUDE §6 classification flow; fix in-loop before delivery |
| pdfunite fails on tectonic-built PDFs | Confirmed working in R1 delivery (89-page combined); same toolchain |
| Model-label swap creates inconsistency between results.tex narrative and figure | Explicit cross-check pass between WP-D and WP-I |

## Git workflow

Per CLAUDE §9: small frequent commits per WP completion; never amend; push to `origin` (z-x-yang/clines-private) only after WP-I completes and PDF is delivered.
