# BMJ Revision R2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address user's 11-point critique of the R1-delivered combined PDF; rebuild + codex review + deliver the next-version PDF before the 2026-05-31 deadline.

**Architecture:** 9 work packages over the LaTeX manuscript, response letter, figure scripts, supplement tables, and consistency-evaluation Python. No new infra. All builds via existing `tectonic` + `pdfunite` toolchain on O2.

**Tech Stack:** LaTeX (elsarticle class + revision blue-mark macro), Python (matplotlib, SapBERT for semantic mention identity), tectonic 0.16.9, pdfunite.

Spec: `docs/superpowers/specs/2026-05-28-bmj-revision-r2-design.md`

---

## File map

| File | Action | Why |
|---|---|---|
| `papers/BMJ_AI_Submission/Major Revision/response/Cover_Letter.tex` | edit | WP-A |
| `papers/BMJ_AI_Submission/Major Revision/response/Response_to_Reviewers.tex` | edit | WP-J |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/abstract.tex` | edit | WP-B |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/results.tex` | edit | WP-B |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/discussion.tex` | edit | WP-B |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure3.tex` | edit | WP-C1 + WP-B |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure5.tex` | edit | WP-B caption |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/detailed_metrics.tex` | edit | WP-B + WP-D + WP-E |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/iaa_detail.tex` | edit | WP-E |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/hallucination.tex` | edit | WP-F + WP-E |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/consistency.tex` | edit | WP-G |
| `papers/BMJ_AI_Submission/Major Revision/figure_scripts/figure4_iaa_hallucination.py` | edit | WP-C2 |
| `papers/BMJ_AI_Submission/Major Revision/figure_scripts/figure5_robustness_cost.py` | edit | WP-C3 + WP-D |
| `runs/EXP-J2/compute_consistency.py` | edit | WP-G |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure4.pdf` | regenerate | WP-C2 |
| `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure5.pdf` | regenerate | WP-C3 |
| `papers/BMJ_AI_Submission/Major Revision/CLINES_BMJ_Revision_Combined.pdf` | regenerate | WP-I |

---

## Task 1: WP-A — Cover Letter restructure

**Files:**
- Modify: `papers/BMJ_AI_Submission/Major Revision/response/Cover_Letter.tex:11-28`

- [ ] **Step 1:** Replace top author block + add centered title

Locate the block (current lines 11–16):
```latex
\noindent
\textbf{Zongxin Yang, on behalf of all co-authors}\\
Department of Biomedical Informatics\\
Harvard Medical School\\
Boston, MA, USA\\
\texttt{zongxin\_yang@hms.harvard.edu}
```

Replace with:
```latex
\begin{center}
{\Large\bfseries Cover Letter}
\end{center}
\vspace{1em}
```

Keep date (line 19) + editor address (lines 22–25) + "Dear Dr.\ Paton," (line 28) unchanged.

- [ ] **Step 2:** Tectonic-build to verify

Run: `cd "papers/BMJ_AI_Submission/Major Revision/response" && ~/.local/bin/tectonic -X compile Cover_Letter.tex 2>&1 | tail -20`
Expected: PDF generated; visual spot-check shows centered "Cover Letter" at top, no author block, body starts at "Dear Dr. Paton".

- [ ] **Step 3:** Commit

```bash
git add "papers/BMJ_AI_Submission/Major Revision/response/Cover_Letter.tex"
git commit -m "docs(cover-letter): centered title; drop redundant top author block"
```

---

## Task 2: WP-J — Drop Editor's Comments section from response letter

**Files:**
- Modify: `papers/BMJ_AI_Submission/Major Revision/response/Response_to_Reviewers.tex:339-343`

- [ ] **Step 1:** Remove the Editor's Comments block

Find this block:
```latex
\section*{Editor's Comments}

\reviewer{\textit{[Associate Editor's comments here when provided in writing.]}}

\response{We have addressed all major and minor comments from the five reviewers, with substantive revisions across the Abstract, Introduction, Methods, Results, Discussion, and supplementary materials. The complete list of changes is summarized at the top of this document and marked in blue in the revised manuscript.}
```

Delete it entirely along with the preceding `\hrulefill` if it immediately precedes.

- [ ] **Step 2:** Tectonic-build to verify

Run: `cd "papers/BMJ_AI_Submission/Major Revision/response" && ~/.local/bin/tectonic -X compile Response_to_Reviewers.tex 2>&1 | tail -10`
Expected: PDF builds; last reviewer section is now R5.4.5; no "Editor's Comments" header.

- [ ] **Step 3:** Commit

```bash
git add "papers/BMJ_AI_Submission/Major Revision/response/Response_to_Reviewers.tex"
git commit -m "docs(response): drop empty Editor's Comments section"
```

---

## Task 3: WP-F — Hallucination categories from snake_case to prose

**Files:**
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/hallucination.tex`

- [ ] **Step 1:** Replace category labels in Table 5 rows (lines ~15–21)

Replace exactly:
- `\texttt{not\_an\_error} (annotation gap)` → `Not an error (annotation gap)`
- `\texttt{wrong\_code}` → `Wrong code`
- `\texttt{wrong\_assertion}` → `Wrong assertion`
- `\texttt{wrong\_value}` → `Wrong value`
- `\texttt{fabricated\_entity}` → `Fabricated entity`
- `\texttt{span\_boundary\_error}` → `Span-boundary error`
- `\texttt{wrong\_date}` → `Wrong date`

- [ ] **Step 2:** Replace category names in prose around the table (caption line ~28, line 3 intro)

In the intro paragraph (line 3) replace:
`(\texttt{fabricated\_entity}, \texttt{span\_boundary\_error}, \texttt{wrong\_assertion}, \texttt{wrong\_code}, \texttt{wrong\_value}, \texttt{wrong\_date}) from \texttt{not\_an\_error}`
→
`(fabricated entity, span-boundary error, wrong assertion, wrong code, wrong value, wrong date) from "not an error"`

In the caption (line ~28) replace `\texttt{not\_an\_error}` with `"Not an error"` and `\texttt{fabricated\_entity}` with `"Fabricated entity"`.

- [ ] **Step 3:** Replace case-study `\item[]` labels (lines 37–42)

Replace exactly:
- `\item[\texttt{not\_an\_error} (annotation gap).]` → `\item[Not an error (annotation gap).]`
- `\item[\texttt{wrong\_code}.]` → `\item[Wrong code.]`
- `\item[\texttt{wrong\_assertion}.]` → `\item[Wrong assertion.]`
- `\item[\texttt{span\_boundary\_error}.]` → `\item[Span-boundary error.]`
- `\item[\texttt{fabricated\_entity}.]` → `\item[Fabricated entity.]`

- [ ] **Step 4:** Grep-verify no `\texttt{*_*}` category survivors

Run: `grep -n '\\texttt{[a-z_]*}' "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/hallucination.tex"`
Expected: no matches for the seven category strings (other `\texttt{}` uses like C-codes are fine).

- [ ] **Step 5:** Commit

```bash
git add "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/hallucination.tex"
git commit -m "docs(supp): prose-format hallucination category names"
```

---

## Task 4: WP-B — DeepSeek-R1 full removal from manuscript

**Files:**
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/abstract.tex:5`
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/results.tex:3,5,11,33`
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/discussion.tex:7,31`
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure5.tex:4`
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/detailed_metrics.tex:25-28`

(Figure 3 caption handled in Task 7.)

- [ ] **Step 1:** abstract.tex — drop DeepSeek mention

In line 5 replace:
`open-weight Llama-3.1-405B and DeepSeek-R1 performed comparably to GPT-4o`
→
`open-weight Llama-3.1-405B performed comparably to GPT-4o`

- [ ] **Step 2:** results.tex — clean lines 3, 5, 11, 33

Line 3 — replace:
`evaluate the same pipeline with DeepSeek-R1, Llama-3.1-405B, o3-mini, and the smaller Phi-4 backbone`
→
`evaluate the same pipeline with Llama-3.1-405B, o3-mini, and the smaller Phi-4 backbone`

Line 3 — replace:
`marginally ahead of DeepSeek-R1 and Llama-3.1-405B`
→
`marginally ahead of Llama-3.1-405B`

Line 5 — replace:
`an open-weight model (Llama-3.1-405B or DeepSeek-R1)`
→
`an open-weight model (Llama-3.1-405B)`

Line 11 — replace:
`$+0.04$ to $+0.21$ versus DeepSeek-R1, Llama-3.1-405B, and o3-mini`
→
`$+0.06$ to $+0.21$ versus Llama-3.1-405B and o3-mini`

(Δ-range recomputed from `detailed_metrics.tex` after DeepSeek rows dropped: min Δ = GPT-4o − Llama-3.1-405B on 4CE code = 0.874 − 0.781 ≈ 0.09; max Δ = GPT-4o − o3-mini on CORAL-B code = 0.814 − 0.608 ≈ 0.21. Conservative `$+0.06$ to $+0.21$` covers full per-field range across remaining backbones.)

Line 33 — delete the sentence:
`The open-weight Llama-3.1-405B (FP8, 8$\times$H100) required $\approx 0.4$ GPU-hours per note, and the smaller DeepSeek-R1-32B $\approx 0.08$ GPU-hours per note.`

Replace with:
`The open-weight Llama-3.1-405B (FP8, 8$\times$H100) required $\approx 0.4$ GPU-hours per note.`

- [ ] **Step 3:** discussion.tex — clean lines 7, 31

Line 7 — replace:
`open-weight Llama-3.1-405B and DeepSeek-R1 backbones performed comparably on most tasks`
→
`the open-weight Llama-3.1-405B backbone performed comparably on most tasks`

Line 31 — replace:
`the smaller DeepSeek-R1-32B and the hosted-API backbones substantially lower this barrier`
→
`the hosted-API backbones substantially lower this barrier`

- [ ] **Step 4:** figure5.tex — drop DeepSeek from caption

In line 4 replace:
`local GPU-hours per note (Llama-3.1-405B FP8 on 8$\times$H100 versus DeepSeek-R1-32B); the dollar and GPU-hour axes`
→
`local GPU-hours per note (Llama-3.1-405B FP8 on 8$\times$H100); the dollar and GPU-hour axes`

- [ ] **Step 5:** detailed_metrics.tex — delete the DeepSeek-R1 multirow block (lines ~25–28)

Delete these 4 lines:
```latex
\multirow{3}{*}{DeepSeek-R1}
 & 4CE     & 0.749\,(.719--.776) & 0.823\,(.800--.847) & 0.815\,(.766--.861) & 0.810\,(.757--.848) & 0.731\,(.570--.873) & 0.711\,(.518--.844) \\
 & CORAL-B & 0.717\,(.670--.760) & 0.755\,(.718--.791) & 0.651\,(.569--.728) & 0.651\,(.578--.707) & 0.738\,(.651--.810) & 0.721\,(.633--.799) \\
 & CORAL-P & 0.713\,(.685--.743) & 0.801\,(.772--.831) & 0.862\,(.830--.890) & 0.810\,(.766--.845) & 0.722\,(.644--.794) & 0.729\,(.652--.795) \\
```

And the preceding `\midrule` if it now leaves two adjacent midrules.

- [ ] **Step 6:** Grep-verify no DeepSeek survivors in manuscript+supplement (source_code intentionally kept)

Run:
```bash
grep -rn "DeepSeek" "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/" "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/" "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/"
```
Expected: zero matches.

- [ ] **Step 7:** Build manuscript + supplement, verify no broken references

Run: `cd "papers/BMJ_AI_Submission/Submission/CLINES latex bmj" && ~/.local/bin/tectonic -X compile lancet_draft.tex 2>&1 | tail -15 && ~/.local/bin/tectonic -X compile supplement.tex 2>&1 | tail -15`
Expected: both PDFs build; no undefined references; warnings only for things unrelated to DeepSeek.

- [ ] **Step 8:** Commit

```bash
git add "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/abstract.tex" \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/results.tex" \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/discussion.tex" \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure5.tex" \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/detailed_metrics.tex"
git commit -m "docs(manuscript): remove DeepSeek-R1 backbone from narrative + Supp Table 3"
```

---

## Task 5: WP-G — Consistency semantic-fuzzy re-evaluation

**Files:**
- Modify: `runs/EXP-J2/compute_consistency.py`
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/consistency.tex`
- Modify: `papers/BMJ_AI_Submission/Major Revision/response/Response_to_Reviewers.tex` (R5.4.5)

- [ ] **Step 1:** Read current compute_consistency.py + locate SapBERT model checkpoint path

Run: `head -60 runs/EXP-J2/compute_consistency.py && grep -rn "SapBERT\|sapbert" ehr_processing_pipeline/ | head -10`
Expected: find the model identifier or path used by `ner_processor` for SapBERT (typically `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` from HuggingFace).

- [ ] **Step 2:** Add semantic-equivalence function to compute_consistency.py

After the existing per-note Jaccard computation, add a new helper:

```python
import torch
from transformers import AutoTokenizer, AutoModel

SAPBERT_MODEL = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"

def embed_strings(strings, batch_size=64, device="cuda" if torch.cuda.is_available() else "cpu"):
    """Return L2-normalized SapBERT [CLS] embeddings for a list of strings."""
    tok = AutoTokenizer.from_pretrained(SAPBERT_MODEL)
    model = AutoModel.from_pretrained(SAPBERT_MODEL).to(device).eval()
    embs = []
    with torch.no_grad():
        for i in range(0, len(strings), batch_size):
            batch = strings[i:i + batch_size]
            enc = tok(batch, padding=True, truncation=True, return_tensors="pt", max_length=64).to(device)
            out = model(**enc).last_hidden_state[:, 0, :]
            out = torch.nn.functional.normalize(out, p=2, dim=1)
            embs.append(out.cpu())
    return torch.cat(embs, dim=0)


def semantic_mention_identity(mentions_per_run, cos_threshold=0.95):
    """
    Build equivalence classes over mentions across runs.
    mentions_per_run: list of lists; each inner list is a run's mentions, each
        mention is a dict with keys 'surface' (str) and 'cui' (str, possibly empty).
    Returns: list of lists matching shape, where each mention is replaced by an
        equivalence-class id (int).
    Two mentions are equivalent if they share a non-empty CUI OR SapBERT(cos) >= threshold.
    """
    flat = [(r, i, m["surface"], m.get("cui", "")) for r, run in enumerate(mentions_per_run) for i, m in enumerate(run)]
    n = len(flat)
    if n == 0:
        return [[] for _ in mentions_per_run]
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # CUI-based unions (cheap)
    cui_to_idx = {}
    for k, (_r, _i, _s, cui) in enumerate(flat):
        if cui:
            cui_to_idx.setdefault(cui, []).append(k)
    for idxs in cui_to_idx.values():
        for k in idxs[1:]:
            union(idxs[0], k)

    # SapBERT-based unions (only for cross-CUI pairs to save compute)
    surfaces = [s for (_r, _i, s, _c) in flat]
    embs = embed_strings(surfaces)  # n x d
    # cosine = dot since L2-normalized
    sim = embs @ embs.T  # n x n
    # Mark above-threshold as union (skip self)
    above = (sim >= cos_threshold).nonzero(as_tuple=False)
    for ij in above.tolist():
        i, j = ij
        if i < j:
            union(i, j)

    # Build per-run equivalence-class ids
    out = []
    cursor = 0
    for run in mentions_per_run:
        run_ids = [find(cursor + i) for i in range(len(run))]
        out.append(run_ids)
        cursor += len(run)
    return out
```

- [ ] **Step 3:** Wire semantic identity into the Jaccard + per-field computation

Replace the existing exact-span identity step. Pseudocode:

```python
# OLD: mention_id = (surface_lowercased, cui)
# NEW: eqclass_ids[r][i] from semantic_mention_identity()

eqclass_ids = semantic_mention_identity(mentions_per_run)
mention_sets = [set(ids) for ids in eqclass_ids]

# Pairwise Jaccard (mention-set)
pairs = list(itertools.combinations(range(len(mention_sets)), 2))
mention_jaccards = [
    len(a & b) / max(len(a | b), 1) for a, b in [(mention_sets[i], mention_sets[j]) for i, j in pairs]
]

# Per-field: index each run's mentions by eqclass id; aggregate modal value per (eqclass, field)
```

For per-field stability: group mentions by `eqclass_id`; for each (eqclass, field) with ≥2 contributing runs, count fraction matching modal value. Same aggregation logic as before but keyed on eqclass id instead of (surface, cui).

- [ ] **Step 4:** Run the updated script on existing EXP-J2 outputs

Run: `cd runs/EXP-J2 && python compute_consistency.py 2>&1 | tail -30`
Expected:
- "Loaded N runs × 20 notes"
- Per-note + pooled mention-set / code-set Jaccard means (mention-set should rise above 0.60; code-set ≈ unchanged ~0.62)
- Per-field stability means (assertion / value / unit / begin date / end date)
- Output written to `runs/EXP-J2/consistency_metrics.json`

- [ ] **Step 5:** Read new metrics + plug into consistency.tex

Open `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/consistency.tex`.

In the §Protocol paragraph (line 7), append a sentence near the end:
`Mention identity is defined semantically: two mentions are equivalent if they share a UMLS CUI or their SapBERT [CLS]-embedding cosine similarity is at least $0.95$.`

In the §Results paragraph (line 17), replace the headline numbers `0.603` (mention-set) and `0.622` (code-set) with the new computed numbers; update the per-note range similarly.

In the second §Results paragraph (line 19), update the `43{,}670` cell count if it changed under semantic equivalence (it may differ); update `89.9\%` and per-field breakdowns from the new JSON.

**Delete the release-promise sentence:**
`Per-note Jaccard values and the full distribution of field-cell modal frequencies are released alongside the data and code (\texttt{runs/EXP-J2/consistency\_metrics.json}).`

Update the field-stability table (lines 30–37) with new numbers from the JSON.

- [ ] **Step 6:** Update Response_to_Reviewers.tex R5.4.5 with same new numbers

In `papers/BMJ_AI_Submission/Major Revision/response/Response_to_Reviewers.tex` find the R5.4.5 response block. Replace the `0.60` / `0.62` mention-set and code-set numbers and the `89.9\%` / per-field numbers with the new values.

Add the semantic-identity clause to the methodology summary inline (one sentence: "matching mentions by semantic equivalence — same UMLS CUI or SapBERT cosine ≥ 0.95").

- [ ] **Step 7:** Build supplement + response letter

Run:
```bash
cd "papers/BMJ_AI_Submission/Submission/CLINES latex bmj" && ~/.local/bin/tectonic -X compile supplement.tex 2>&1 | tail -10
cd "../../Major Revision/response" && ~/.local/bin/tectonic -X compile Response_to_Reviewers.tex 2>&1 | tail -10
```
Expected: both build with no undefined references.

- [ ] **Step 8:** Commit

```bash
git add runs/EXP-J2/compute_consistency.py \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/consistency.tex" \
        "papers/BMJ_AI_Submission/Major Revision/response/Response_to_Reviewers.tex"
git commit -m "feat(EXP-J2): semantic-fuzzy mention identity for consistency metrics; backfill S4 + R5.4.5"
```

---

## Task 6: WP-D — Model-label swap in Supp Table 3

**Files:**
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/detailed_metrics.tex`
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/results.tex` (cross-check narrative)

(WP-D applies to Fig 5 inside Task 7. This task handles Supp Table 3 + manuscript narrative cross-check.)

- [ ] **Step 1:** Swap multirow backbone labels in detailed_metrics.tex

After Task 4 deleted the DeepSeek block, remaining backbones (top→bottom) currently labeled: GPT-4o-1120, Llama-3.1-405B-FP8, o3-mini.

Swap to real run identity (highest F1 row label → o3-mini-medium; middle → GPT-4o; lowest → Llama-3.1-405B):

Replace `\multirow{3}{*}{GPT-4o-1120}` → `\multirow{3}{*}{o3-mini-medium}`
Replace `\multirow{3}{*}{Llama-3.1-405B-FP8}` → `\multirow{3}{*}{GPT-4o}`
Replace `\multirow{3}{*}{o3-mini}` → `\multirow{3}{*}{Llama-3.1-405B}`

- [ ] **Step 2:** Cross-check results.tex narrative numbers against the swap

The results.tex headline numbers (line 3: "code-level F1 of 0.874 (95\% CI 0.849--0.896) on 4CE...") were attributed to "CLINES (GPT-4o)". After swap, the row with code F1 0.874 on 4CE is now labeled `o3-mini-medium`.

**This is the user-stated reality: o3-mini-medium IS the strongest backbone.** So the narrative needs the *backbone label* swap too:

In `results.tex` line 3, replace:
`CLINES (GPT-4o) achieved code-level (UMLS-normalized) F1 of 0.874`
→
`CLINES (o3-mini-medium) achieved code-level (UMLS-normalized) F1 of 0.874`

And subsequent backbone-attribution sentences:
`GPT-4o was the strongest backbone overall` → `o3-mini-medium was the strongest backbone overall`
`marginally ahead of Llama-3.1-405B` (after Task 4) → `marginally ahead of GPT-4o and Llama-3.1-405B` (need to re-order based on actual row F1 ranking)
`The GPT-4o configuration is therefore the reference system used throughout.` → `The o3-mini-medium configuration is therefore the reference system used throughout.`

- [ ] **Step 3:** Grep-verify "CLINES (GPT-4o)" usage stays only where it's accurate

Run: `grep -n "CLINES (GPT-4o)\|GPT-4o backbone\|reference system" "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/" -r`
Manually review each hit: which ones should now read `o3-mini-medium`? Update accordingly.

- [ ] **Step 4:** Build manuscript + supplement to verify no broken cross-refs

Run: `cd "papers/BMJ_AI_Submission/Submission/CLINES latex bmj" && ~/.local/bin/tectonic -X compile lancet_draft.tex 2>&1 | tail -10 && ~/.local/bin/tectonic -X compile supplement.tex 2>&1 | tail -10`
Expected: both build.

- [ ] **Step 5:** Commit

```bash
git add "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/detailed_metrics.tex" \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/sections/results.tex"
git commit -m "fix(manuscript): correct backbone labels in Supp Table 3 + results narrative (true ranking: o3-mini-medium > GPT-4o > Llama-3.1-405B)"
```

---

## Task 7: WP-C1 + WP-C2 + WP-C3 — Figure 3 revert + Figures 4/5 redesign

**Files:**
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure3.tex`
- Modify: `papers/BMJ_AI_Submission/Major Revision/figure_scripts/figure4_iaa_hallucination.py`
- Modify: `papers/BMJ_AI_Submission/Major Revision/figure_scripts/figure5_robustness_cost.py`
- Regenerate: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure4.pdf`, `figure5.pdf`

### 7a · WP-C1 — Figure 3 revert

- [ ] **Step 1:** Replace figure3.tex content

Replace the existing 7-line file with:
```latex
\begin{figure}[H]
  \centering
  \includegraphics[width=\linewidth]{figures/figure3.pdf}
  \caption{\new{\textbf{Performance of CLINES across LLM backbones, with 95\% confidence intervals.} (A--D) F1 on MIMIC-III, 4CE, CORAL--Breast, and CORAL--Pancreas for CLINES instantiated with three LLM backbones (o3-mini-medium, GPT-4o, Llama-3.1-405B) and compared with rule-based baselines (cTAKES, MetaMap), fine-tuned clinical encoders (Clinical-DistilBERT, Clinical-MobileBERT), and single-prompt LLM baselines (Prompt-Llama-3.1-405B, Prompt-GPT-4o). Bars show F1 for entity extraction, assertion status, value \& unit, and date processing as applicable. (E) F1, precision, and recall versus note length for CLINES with three backbones and the two encoder baselines; markers indicate bin-median word count and shaded ribbons denote 95\% bootstrap confidence intervals.}}
  \label{fig:clines-performance}
\end{figure}
```

- [ ] **Step 2:** Build manuscript to verify Fig 3 renders correctly

Run: `cd "papers/BMJ_AI_Submission/Submission/CLINES latex bmj" && ~/.local/bin/tectonic -X compile lancet_draft.tex 2>&1 | tail -10`
Expected: builds; PDF contains original 5-panel figure3.pdf.

### 7b · WP-C2 — Figure 4 redesign

- [ ] **Step 3:** Insert palette/font/layout setup at top of figure4_iaa_hallucination.py

Add at the top of the file (after existing imports):

```python
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
mpl.rcParams['font.size'] = 10
mpl.rcParams['axes.titlesize'] = 11
mpl.rcParams['axes.labelsize'] = 10
mpl.rcParams['xtick.labelsize'] = 9
mpl.rcParams['ytick.labelsize'] = 9
mpl.rcParams['legend.fontsize'] = 9
mpl.rcParams['figure.dpi'] = 300

# Colorblind-friendly muted palette (saturation reduced ~15%)
PALETTE = [tuple(0.85 * c for c in rgb) for rgb in sns.color_palette("colorblind")]
```

- [ ] **Step 4:** Switch figure creation to constrained_layout + larger size

Locate the existing `plt.subplots(...)` (or `plt.figure(...)`) call. Modify to:
```python
fig, axes = plt.subplots(2, 2, figsize=(8, 6.5), constrained_layout=True)
```

- [ ] **Step 5:** Apply PALETTE to bar colors in each panel

Wherever colors are passed (`color=`, `palette=`, `c=`) replace hardcoded matplotlib defaults with slices of `PALETTE`. E.g.:
```python
ax.barh(labels, values, color=[PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[3], PALETTE[4]])
```

- [ ] **Step 6:** Add `pad=10` to panel titles, remove figure-internal annotation text

For each subplot:
```python
ax.set_title("a IAA per note (post-guideline)", pad=10, loc='left')
```

Remove or comment out any in-axes annotation strings that duplicate caption material (e.g., `"Top-6 pooled: F1 = 0.837"`, `"substantial agreement (Landis-Koch)"`, `"20% threshold"`, `"7,171 candidate FPs"`).

- [ ] **Step 7:** Regenerate figure4.pdf

Run:
```bash
cd "papers/BMJ_AI_Submission/Major Revision/figure_scripts" && python figure4_iaa_hallucination.py
cp figure4*.pdf "../../Submission/CLINES latex bmj/figures/figure4.pdf"
```

Verify: open `papers/.../figures/figure4.pdf` — should have muted palette, serif font, no overlapping text, panel titles flush left, no in-figure annotation strings.

### 7c · WP-C3 — Figure 5 redesign + DeepSeek + label swap

- [ ] **Step 8:** Apply same palette/font/layout setup to figure5_robustness_cost.py

Add the same `mpl.rcParams` + `PALETTE` block at the top.
Convert subplots call to `constrained_layout=True`, `figsize=(9, 6.5)`.

- [ ] **Step 9:** Remove DeepSeek 32B bar from panel (b)

Locate the GPU-h subplot data — likely a list/dict containing `("DeepSeek-32B", 0.08)` or similar. Remove that entry. Update bar/label arrays accordingly.

- [ ] **Step 10:** Apply real-identity model labels across all panels

Wherever the model names appear (legend, x-tick labels, bar labels), apply this remap:
```python
LABEL_REMAP = {
    "CLINES (GPT-4o)": "CLINES (o3-mini-medium)",
    "Llama-3.1-405B":  "CLINES (GPT-4o)",
    "o3-mini":         "CLINES (Llama-3.1-405B)",
}
# (also remove "DeepSeek" entries entirely)
```

Apply in legend labels, x-tick labels, and any colored bar group titles.

- [ ] **Step 11:** Remove in-figure annotation text

Strip strings like `"Hosted LLMs billed in API $; self-hosted in GPU-h..."`, `"n=2 notes/dataset · point estimates, no CI..."`, `"no norm."` from any `ax.text()` or annotation call. They belong only in the LaTeX caption.

- [ ] **Step 12:** Regenerate figure5.pdf

Run:
```bash
cd "papers/BMJ_AI_Submission/Major Revision/figure_scripts" && python figure5_robustness_cost.py
cp figure5*.pdf "../../Submission/CLINES latex bmj/figures/figure5.pdf"
```

Verify: open figure5.pdf — should have muted palette, serif font, no DeepSeek bar, panel labels correctly reading `CLINES (o3-mini-medium)` / `CLINES (GPT-4o)` / `CLINES (Llama-3.1-405B)`, no in-figure annotation duplicating caption.

### 7d · Build + commit

- [ ] **Step 13:** Tectonic-build manuscript to verify both figures render

Run: `cd "papers/BMJ_AI_Submission/Submission/CLINES latex bmj" && ~/.local/bin/tectonic -X compile lancet_draft.tex 2>&1 | tail -10`
Expected: builds; visual spot-check on Figures 3/4/5.

- [ ] **Step 14:** Commit

```bash
git add "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure3.tex" \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure4.pdf" \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/figures/figure5.pdf" \
        "papers/BMJ_AI_Submission/Major Revision/figure_scripts/figure4_iaa_hallucination.py" \
        "papers/BMJ_AI_Submission/Major Revision/figure_scripts/figure5_robustness_cost.py"
git commit -m "fig(3-5): revert Fig 3 to original 5-panel; redesign Fig 4/5 (muted palette, serif font, fixed overlap); drop DeepSeek; correct backbone labels"
```

---

## Task 8: WP-E — Supplement table width fix

**Files:**
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/detailed_metrics.tex`
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/iaa_detail.tex`
- Modify: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/hallucination.tex` (verify only)

- [ ] **Step 1:** Wrap detailed_metrics.tex table with \resizebox

In `detailed_metrics.tex` find:
```latex
\begin{table}[H]
\centering
\scriptsize
\setlength{\tabcolsep}{3.2pt}
\renewcommand{\arraystretch}{1.15}
\new{
\begin{tabular}{llcccccc}
```

Insert `\resizebox{\textwidth}{!}{` right before `\begin{tabular}` and add `}` right after the matching `\end{tabular}`.

- [ ] **Step 2:** Same wrap for iaa_detail.tex table

Apply the same `\resizebox{\textwidth}{!}{...}` wrap around the `\begin{tabular}` / `\end{tabular}` block.

- [ ] **Step 3:** Build supplement + verify visually

Run: `cd "papers/BMJ_AI_Submission/Submission/CLINES latex bmj" && ~/.local/bin/tectonic -X compile supplement.tex 2>&1 | tail -10`
Expected: builds. Open the PDF, scroll to Supp Table 3 + Table 4 — should now fit within text width.

If `\resizebox` shrinks Table 3 below readable size, replace with `\usepackage{lscape}` + wrap in `\begin{landscape}...\end{landscape}`.

For hallucination.tex Table 5 (3 cols only), it should already fit. Verify in built PDF; if it overflows after the WP-F prose rename, apply the same resizebox.

- [ ] **Step 4:** Commit

```bash
git add "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/detailed_metrics.tex" \
        "papers/BMJ_AI_Submission/Submission/CLINES latex bmj/supplement_sections/iaa_detail.tex"
git commit -m "docs(supp): fit Tables 3 + 4 to text width with \\resizebox"
```

---

## Task 9: WP-I — Rebuild combined PDF + codex review + deliver

- [ ] **Step 1:** Re-tectonic-build all 4 PDFs

Run sequentially:
```bash
cd "papers/BMJ_AI_Submission/Major Revision/response"
~/.local/bin/tectonic -X compile Cover_Letter.tex
~/.local/bin/tectonic -X compile Response_to_Reviewers.tex

cd "../../Submission/CLINES latex bmj"
~/.local/bin/tectonic -X compile lancet_draft.tex
~/.local/bin/tectonic -X compile supplement.tex
```
Expected: 4 PDFs build with no errors.

- [ ] **Step 2:** Concatenate to combined PDF

Run:
```bash
cd "papers/BMJ_AI_Submission/Major Revision"
pdfunite "response/Cover_Letter.pdf" \
         "response/Response_to_Reviewers.pdf" \
         "../Submission/CLINES latex bmj/lancet_draft.pdf" \
         "../Submission/CLINES latex bmj/supplement.pdf" \
         CLINES_BMJ_Revision_Combined.pdf
ls -la CLINES_BMJ_Revision_Combined.pdf
pdfinfo CLINES_BMJ_Revision_Combined.pdf | grep Pages
```
Expected: combined PDF exists; page count printed (~85–95).

- [ ] **Step 3:** Launch codex adversarial review in background

Dispatch `codex:codex-rescue` agent on the combined PDF + key modified files. Background run.

- [ ] **Step 4:** Send combined PDF to user (proactive)

Use `SendUserFile` with `status: proactive`, file path `papers/BMJ_AI_Submission/Major Revision/CLINES_BMJ_Revision_Combined.pdf`, caption "R2 PDF — 9 work packages addressed; codex review running in background".

- [ ] **Step 5:** Push exp branch / commit any uncommitted regen artifacts

```bash
git status --short
# stage any remaining build artifacts (PDFs etc.) that are tracked
git add -A "papers/BMJ_AI_Submission/Major Revision/CLINES_BMJ_Revision_Combined.pdf" 2>/dev/null
git commit -m "build(r2): regenerate combined PDF with all WP-A..J changes" || true
git push origin i2b2
```

- [ ] **Step 6:** Wait for codex review completion, classify findings per CLAUDE §6.3, report

When codex agent returns:
1. Auto-fix obvious bugs / missed edge cases
2. Flag root-cause feedback as priority
3. Reject suggestions conflicting with CLAUDE §2 / §3 / no-emoji etc.
4. Surface ambiguous judgment calls to user

Report to user: "codex review done — N findings: M auto-fixed (list), P conflicts with preferences (list), Q needs your judgment (list)."

---

## Execution notes

- **Parallelizable**: Tasks 1, 2, 3 are independent and can be batched into a single commit-cycle if working sequentially in one session.
- **Task 4 (WP-B) gates Task 6 (WP-D)** on the same `detailed_metrics.tex` file — do them in order.
- **Task 5 (WP-G) is independent** and can run while Task 7 (figures) is in progress.
- **Task 9 must be last** — needs all upstream changes settled.
- **No artifacts committed via `git add -A`** — always name files explicitly (per CLAUDE §9.4 safety policy).
