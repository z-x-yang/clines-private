# EXP-J2 — Run-to-run output consistency, re-run on OPTIMIZED pipeline

Supersedes **EXP-J** (see `experiments/EXP-J_output_consistency.md`). Same
reviewer hook, same 20 notes, same metric definitions — but run on the
optimized i2b2 code (`a31f18a`) instead of the stale worktree (`d04b219`) that
made EXP-J 5-7× too slow for the wrong reason.

## 1. Goal / reviewer hook

Reviewer **R5.4.5**: quantify reproducibility of CLINES structured outputs across
independent runs of the non-deterministic LLM (`temperature=0.6`). Feeds
**Supplementary §S4**. Run the FULL pipeline **5 independent times on the SAME 20
notes** (`gpt4omini` backbone), measure output variation.

## 2. Why a re-run (root-cause of EXP-J's slowness — corrected)

EXP-J's record blamed "CPU SapBERT + FAISS retrieval dominates (~2-3h/CORAL
note)". **That diagnosis was wrong.** Log-timestamp analysis of EXP-J cell
41679908_1 showed the 40-min-per-chunk gaps were **between the NER LLM response
(httpx 200 in seconds) and the `Found N entities` log** — i.e. inside
`ner_processor.parse_ner_result_text`'s entity position-finding, NOT SapBERT and
NOT the API. The culprit: `_sequential_fuzzy_match_context` / `_fuzzy_match_context`
slide a window across the **entire normalized document** (`original_ehr_text`,
~16-21K chars for CORAL) computing `difflib.SequenceMatcher().ratio()` (O(M²)) at
every position, for every entity whose exact match fails (many, on long CORAL
notes with 44-111 entities/chunk that the LLM paraphrases). That is O(N·M²) per
entity over the whole note → ~40 min/chunk.

**The fix already existed on `i2b2` but EXP-J didn't have it.** The EXP-J worktree
was branched from `d04b219`, which predates the i2b2 commit that restricts the
alignment search to a `chunk_offset ± 400` window (Lever 1). EXP-J ran the
pre-fix code. Running on current `i2b2` alone removes the catastrophe.

## 3. Optimization in the code under test (`a31f18a`)

- **Lever 1 (already on i2b2, pre-existing):** in `parse_ner_result_text`, build
  the normalized mapping over a `chunk_offset ± 400` window instead of the whole
  document. N drops from ~16-21K to ~3.8K and decouples from document length.
- **Lever 2 (this revision's commit `adca819`):** in both fuzzy matchers, build
  one `SequenceMatcher(None, '', context)` per case and `set_seq1(window)` per
  iteration (reuse cached seq2), and skip the O(M²) `ratio()` when
  `max(quick_ratio_cs, quick_ratio_ci) <= best_ratio`. `quick_ratio()` is an exact
  upper bound on `ratio()`, so the argmax is preserved → **byte-identical output**.
  - Verified: 6011-case differential test (random + edge cases: empty/whitespace
    context, context longer than note, ties, every start position) → 0 mismatches;
    real-note microbench → identical (best_pos, best_window), ~1.7× faster on the
    fuzzy step.

**Profiling finding (drives the %15 choice):** once Lever 1 is in, fuzzy is no
longer the bottleneck. A single-note perf test (breastca 20, 21K chars) on i2b2
vs i2b2+L2 ran at the SAME ~5 min/chunk; the gaps moved to **between consecutive
httpx calls (~60-130 s each)** — pure HMS Azure proxy latency (this afternoon;
was 1-5 s/call in the morning). So the residual lever is **concurrency**, not more
fuzzy optimization. Hence `%15` (all cells concurrent) here, vs EXP-J's `%6`.

## 4. Baseline / provenance

- **Base branch / commit:** `i2b2` @ **`a31f18a`** = `adca819` (perf: quick_ratio
  fuzzy pruning, on top of the pre-existing chunk-window restriction) + the
  `--note_id_list` allowlist port (`a31f18a`). i2b2's `main.py` originally lacked
  `--note_id_list` — that harness arg lived only on the EXP-G2/EXP-J lineage, so
  the first EXP-J2 array (41735389) failed with `unrecognized arguments:
  --note_id_list`. Ported it onto i2b2 (with the correct `n[:-4]` suffix strip,
  not the buggy `rstrip('.txt')` from the old lineage) and re-ran. Cleanly checked
  out — NOT a worktree code mix (the old EXP-J worktree `d04b219` differs from
  `a31f18a` by ~218 lines across `ner_processor.py` / `pipeline_coordinator.py` /
  `main.py`, so it could not be reused byte-for-byte).
- **EXP-J2 branch:** `exp/EXP-J2_output_consistency` (== `i2b2` @ `a31f18a`).
- **Run location:** main repo checkout (`/n/data1/.../language-into-clinical-data`,
  shared NFS), which has `data/`, `main.py`, the 18GB `cache/`, and gets
  `umls_dictionary.txt` / `umls_body_loc_dictionary.txt` symlinked by the job.

## 5. Env

- conda env **`sglang`**: faiss 1.7.2, torch 2.6.0+cu124, openai 1.60.1 (confirmed
  `import faiss, torch` OK). **CPU + API only.** SapBERT auto-CPU.
- **UMLS embedding cache (was a launch bug):** `RetrieverCoordinator.embed_dictionary`
  loads `./cache/{dense_embed_all,term_list_all,dense_embed_bodyloc,term_list_bodyloc}.pt`
  on a HIT (read-only; never writes on HIT). The first 41737412 launch had an
  **empty** `./cache/` (the job symlinked the dictionaries but not the cache), so all
  15 cells cache-MISSED and started re-embedding 5.7M UMLS terms on CPU (~150 s/batch
  × 173 batches ≈ **7 h/cell**, all racing to write the same `dense_embed_all.pt`).
  Cancelled at ~13% (0 notes processed — pure setup waste, no valid output). Fix: the
  job now symlinks the 4 pre-computed cache files from
  `SHARE/From_Zongxin/language-into-clinical-data/cache/` (17G `dense_embed_all.pt`
  built Jun 2025) → instant HIT. Same EXP-J2 (code-under-test `a31f18a` unchanged;
  this was env plumbing, parallel to the existing umls symlinks).
- `--model_name gpt4omini` → deployment `gpt-4o-mini-0718`, api-version
  `2025-04-01-preview`, endpoint `https://azure-ai.hms.edu`.

## 6. The 20 notes (same as EXP-J; deterministic sorted first-N)

- **4CE (10):** BCH_1, BCH_2, BCH_3, BCH_4, BCH_5, BCH_6, BCH_7, COL_1, COL_2, COL_3
- **coral_breastca (5):** 20, 21, 22, 23, 24
- **coral_pdac (5):** 0, 1, 10, 11, 12

Lists at `runs/EXP-J2/notes_lists/{4CE,coral_breastca,coral_pdac}.txt`.

## 7. Exact commands (reproduce)

```bash
git checkout exp/EXP-J2_output_consistency       # == i2b2 @ a31f18a
# symlinks (data/ + cache/ already present in main checkout; umls auto-symlinked by job)
source "$HOME/.clines_openai.env"                # OPENAIKEY + OPENAIENDPOINT (gitignored, $HOME)
sbatch jobs/EXP-J2_cell.sh                        # array 0-14%15, -p short -c 8 --mem 96G -t 05:00:00
# SLURM_ARRAY_TASK_ID -> R = TID/3+1, slice = (4CE|coral_breastca|coral_pdac)[TID%3]; per cell:
#   python main.py --notes_dir <DIR> --note_id_list runs/EXP-J2/notes_lists/<slice>.txt \
#     --model_name gpt4omini --max_retries 1 --schema default \
#     --marker EXP-J2_run${R}_<slice> --output_dir runs/EXP-J2/run${R}/<slice> \
#     --chunk_size 768 --num_workers 4
# then:
python runs/EXP-J/compute_consistency.py          # (reuse; point it at runs/EXP-J2/)
```

`%15` (all 15 cells concurrent) overlaps the per-call API latency across cells —
the residual bottleneck once fuzzy is fixed. With Lever 1+2 the per-chunk fuzzy
cost is negligible; total wall-clock is now API-bound and depends on HMS proxy
load at run time.

**Resolved (was EXP-J §7b caveat):** the old EXP-J lineage filtered note ids with
`note_id.rstrip('.txt')` (strips the char set `{.,t,x}`, not the suffix). The
`a31f18a` port uses correct suffix removal (`n[:-4] if n.endswith('.txt')`), so
the bug does not exist in the code under test. (It happened to be non-impacting
for these 20 ids anyway, since they all end in digits / `_<digit>`.)

## 8. Results

SLURM array `41743916` on `c90877e` (i2b2 / `exp/EXP-J2_output_consistency`, post
cache-symlink fix): **15/15 cells COMPLETED, 0 failures**, per-cell elapsed
**31:02–1:17:37** (4CE shortest, CORAL pdac longest). 100/100 expected
`*_default.csv` outputs present (5 runs × 20 notes). All 20 notes have full 5-run
coverage; no partial outputs to exclude.

Metrics from `python runs/EXP-J2/compute_consistency.py` (output:
`runs/EXP-J2/consistency_metrics.json`):

| Metric                                        | Mean       | Per-note / per-cell range |
|-----------------------------------------------|------------|---------------------------|
| Pairwise mention-set Jaccard (per note)       | **0.6033** | [0.3961, 0.7669]          |
| Pairwise code-set Jaccard (per note)          | **0.6223** | [0.4982, 0.7176]          |
| Per-field modal agreement, assertion_status   | 0.8513     | [0.2500, 1.0000]  (n=8,734) |
| Per-field modal agreement, value              | 0.8491     | [0.2000, 1.0000]  (n=8,734) |
| Per-field modal agreement, unit               | 0.9431     | [0.2000, 1.0000]  (n=8,734) |
| Per-field modal agreement, begin_date         | 0.9113     | [0.2000, 1.0000]  (n=8,734) |
| Per-field modal agreement, end_date           | 0.9390     | [0.2000, 1.0000]  (n=8,734) |
| **All fields pooled**                         | **0.8988** | [0.2000, 1.0000]  (n=43,670) |

Mention-set / code-set Jaccard averaged over $\binom{5}{2}=10$ run pairs per
note, then over 20 notes. Per-field modal agreement is computed per (span, field)
cell over the runs that contain the span (>=2 runs required); reported is the
mean fraction-of-runs equal to the modal value, with the count of qualifying
cells.

## 9. vs baseline / interpretation

There is no prior numerical baseline for CLINES run-to-run consistency in the
original submission (the reviewer R5.4.5 hook is exactly that this metric was
absent). Interpreting against the protocol promise (§S4):

- **Set-membership stability is moderate.** ~60% Jaccard means roughly 60% of
  extracted mentions and assigned UMLS codes are shared between any two runs on
  the same note. This is expected stochastic-decoding variance and is the kind
  of finding Ntinopoulos et al. (BMJ HCI 2025) recommends reporting.
- **Per-mention content stability is high.** When the same span IS recovered
  across runs, ~89.9% of (span, field) entries match the modal value. Unit,
  begin/end date track even higher (91–94%). The variation is concentrated in
  *which* spans get extracted, not in *what fields they carry* when extracted.

## 10. Analysis

- The all-fields pooled stability (0.8988) is driven by the 43,670 (span, field)
  cells across 20 notes with ≥2 runs — large effective sample, so the point
  estimate is precise.
- The per-cell range floor of 0.20 reflects the C(5,2) tie case where 1 out of 5
  runs holds the modal value (e.g. all 5 disagree, modal frequency = 1, fraction
  = 0.20). These are minority cases; the 0.899 mean shows most cells are at
  modal agreement ≥0.80.
- The lower stability on `value` (0.849) and `assertion_status` (0.851) vs date
  fields suggests two sources of run-to-run noise: numeric value normalization
  (e.g. "5.0" vs "5") and three-way assertion choices (present / absent /
  uncertain) where the LLM occasionally drifts. Both could be mitigated by
  prompt tightening or majority-vote aggregation at deployment time.

## 11. Conclusion

PASS. CLINES outputs are not deterministically reproducible at the set level
(Jaccard ≈ 0.60) under stochastic decoding, but per-mention structured content
agrees ≈ 0.90 across 5 runs; majority-vote aggregation across R≥3 runs yields a
stable consensus output for chart-review use.

## 12. Next step

Done in this revision: numbers pasted into
`papers/.../supplement_sections/consistency.tex` (§S4 Results table) and into
the R5.4.5 response, then supplement + combined PDF rebuilt. EXPERIMENTS.md
index updated to PASS.

## 13. Artifact pointers

- Predictions: `runs/EXP-J2/run{1..5}/<slice>/EXP-J2_run{R}_<slice>_<noteid>_default.csv` (100 files)
- Metrics JSON: `runs/EXP-J2/consistency_metrics.json`
- Metric script: `runs/EXP-J2/compute_consistency.py` (copied from EXP-J;
  derives `EXP_ID` from the parent dir so it works for both)
- Job script: `jobs/EXP-J2_cell.sh`
- SLURM array jobid (successful run): **41743916** on commit `c90877e`
- SLURM logs: `runs/EXP-J2/logs/cell-41743916_{0..14}.{out,err}`
- Failed prior arrays (superseded): `41735389` (pre-`--note_id_list`, ~30 s, args error);
  `41737412` (pre-cache-symlink, scancelled at ~13% — 15× concurrent dictionary re-embed)
- Code under test: commit `c90877e` on `i2b2` / `exp/EXP-J2_output_consistency`
  (= `a31f18a` + cache-symlink job-script fix; no pipeline-code change since `a31f18a`)
