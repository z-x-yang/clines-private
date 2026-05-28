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
  `import faiss, torch` OK). **CPU + API only.** SapBERT auto-CPU; 18GB UMLS embed
  cache HIT.
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

_(backfilled on COMPLETED — run compute_consistency.py against runs/EXP-J2/)_

## 9. vs baseline / interpretation

_(backfilled)_

## 10. Analysis

_(backfilled)_

## 11. Conclusion

_(backfilled — one line)_

## 12. Next step

_(backfilled — paste metrics into supplement_sections/consistency.tex S4, tighten R5.4.5, rebuild combined PDF)_

## 13. Artifact pointers

- Predictions: `runs/EXP-J2/run{1..5}/<slice>/EXP-J2_run{R}_<slice>_<noteid>_default.csv`
- Metrics JSON: `runs/EXP-J2/consistency_metrics.json` (to be produced)
- Metric script: `runs/EXP-J/compute_consistency.py` (reused; retarget to runs/EXP-J2/)
- Job script: `jobs/EXP-J2_cell.sh`
- SLURM logs: `runs/EXP-J2/logs/cell-<jobid>_{0..14}.{out,err}` (41735389 = failed
  pre-`--note_id_list` array; superseded by the a31f18a re-run)
- Code under test: commit `a31f18a` on `i2b2` / `exp/EXP-J2_output_consistency`
