# EXP-J — Run-to-run output consistency (CLINES pipeline, gpt4omini)

## 1. Goal / reviewer hook

Reviewer **R5.4.5** asked us to quantify how reproducible the CLINES structured
outputs are across independent runs (the pipeline uses a non-deterministic LLM,
`temperature=0.6`). Feeds **Supplementary §S4**. We run the FULL pipeline **5
independent times on the SAME 20 notes** with the `gpt4omini` backbone and
measure output variation.

## 2. Source of variation

`llm_interface/providers/openai_provider.py` calls the chat completion with
`temperature=0.6` (non-zero) for all non-`o3mini` models. This stochasticity is
the entire reason outputs can differ run-to-run; everything else in the pipeline
(SapBERT retrieval, FAISS, chunking, Step-4 reconcile) is deterministic given the
same LLM output. So EXP-J effectively measures how much temperature-0.6 sampling
propagates into the final i2b2-style CSV.

## 3. Baseline / provenance

- **Base branch / commit**: branched from `exp/EXP-G2_ablation_gpt4omini` @ `7322506`
  (the verified gpt-4o-mini harness with `--note_id_list` support + the
  result_aggregation join-by-TAG fix from `69d0a52`).
- **EXP-J branch**: `exp/EXP-J_output_consistency`.
- Worktree run location: `.claude/worktrees/exp-j-consistency` (shared NFS;
  symlinks `data/`, `cache/`, `umls_dictionary.txt`,
  `umls_body_loc_dictionary.txt` → repo / SHARE).
  - **Gotcha (fixed)**: first attempt put the worktree in node-local `/tmp/` →
    SLURM scheduled the job on a *different* node where the path was empty →
    instant `exit 4` (the "must run from worktree root" guard), jobid 41676527
    FAILED in 9s with empty logs. Worktrees for SLURM jobs MUST live on shared
    NFS (`/n/data1/...`), like every other `exp/*` worktree.

## 4. Env

- conda env **`sglang`** (`/home/zoy043/miniconda3/envs/sglang`): faiss 1.7.2,
  torch 2.6.0+cu124, openai 1.60.1, tiktoken, semchunk, demjson3, pandas — all
  present. (Same env EXP-G2 used.)
- **CPU + API only.** SapBERT auto-CPU (`use_gpu = torch.cuda.is_available()`).
  UMLS embedding cache at `./cache` (18GB: `dense_embed_all.pt` 17G etc.) is a
  cache HIT → no GPU embedding needed.
- Model mapping: `--model_name gpt4omini` → deployment `gpt-4o-mini-0718` via
  `openai_provider.py` n2n_dict (confirmed). API version `2025-04-01-preview`,
  endpoint `https://azure-ai.hms.edu`.

## 5. The 20 notes (deterministic: sorted, first-N per slice)

NOTE: `data/4CE/` actually contains **49** `.txt` files (task brief said 63);
we still take the sorted first 10. `sort` is lexicographic, so coral_pdac gives
`0,1,10,11,12` not `0,1,2,3,4`.

- **4CE (10)**: BCH_1, BCH_2, BCH_3, BCH_4, BCH_5, BCH_6, BCH_7, COL_1, COL_2, COL_3
- **coral_breastca (5)**: 20, 21, 22, 23, 24
- **coral_pdac (5)**: 0, 1, 10, 11, 12

Lists at `runs/EXP-J/notes_lists/{4CE,coral_breastca,coral_pdac}.txt`.

## 6. Exact commands (reproduce)

```bash
git checkout exp/EXP-J_output_consistency
# (re-establish symlinks: data, cache, umls_dictionary.txt, umls_body_loc_dictionary.txt)
set -a; source /home/zoy043/.clines_openai.env; set +a   # OPENAIKEY + OPENAIENDPOINT
export OPENAIENDPOINT="${OPENAIENDPOINT:-https://azure-ai.hms.edu}"
HOLD_ON_FAIL=1 sbatch --export=ALL,OPENAIKEY,OPENAIENDPOINT,HOLD_ON_FAIL jobs/EXP-J_cell.sh
# job ARRAY 0-14%6 (15 cells = 5 runs × 3 slices), -p short -c 8 --mem 96G -t 07:00:00
# SLURM_ARRAY_TASK_ID -> R = TID/3+1, slice = SLICES[TID%3]; per cell:
#   python main.py --notes_dir <DIR> --note_id_list runs/EXP-J/notes_lists/<slice>.txt \
#     --model_name gpt4omini --max_retries 1 --schema default \
#     --marker EXP-J_run${R}_<slice> --output_dir runs/EXP-J/run${R}/<slice> \
#     --chunk_size 768 --num_workers 4
# then:
python runs/EXP-J/compute_consistency.py   # writes runs/EXP-J/consistency_metrics.json
```

**Why a job array (not one sequential job):** the FULL gpt4omini pipeline costs
~1h/note on CPU (CPU SapBERT + FAISS UMLS retrieval dominates; EXP-G2 `full`
cells: 4CE 2h35m, coral_pdac 2h07m, coral_breastca 2h12m — each for only 2
notes). A single 5×20 sequential job would need ~50h ≫ 8h walltime (first attempt
jobid 41676993 was on track to TIMEOUT after ~1 run; cancelled). Splitting into
15 independent cells × num_workers=4, throttled to 6 concurrent array tasks
(`%6`, ≤24 concurrent Azure calls to respect rate limits), fits each cell in
walltime. Worst cell = 4CE (10 notes) ~ <5h.

## 7. Metrics definitions

- **mention-set Jaccard**: per note, set of `(mention_start_pos, mention_end_pos,
  mention)` spans; pairwise Jaccard over C(5,2)=10 run pairs; mean across pairs &
  notes, with min/max.
- **code-set Jaccard**: same, over the set of `code` values.
- **per-field majority-vote stability**: for each span seen in ≥2 runs and each
  field in {assertion_status, value, unit, begin_date, end_date}, fraction of
  contributing runs equal to the modal value; averaged over cells. Per-field +
  overall.

Submission history (HOLD_ON_FAIL=1):
- 41676527 FAILED (`/tmp` worktree gotcha).
- 41676993 (single sequential job) cancelled — would TIMEOUT (~50h vs 8h).
- **41679908** (array `0-14%6`): 3 4CE cells COMPLETED (run1/2/3, 10 notes each);
  the 6 CORAL cells were **externally `scancel`'d at 16:20:05** (`CANCELLED by
  213028`, Reason=None — an explicit scancel from a process under my uid, NOT a
  SLURM limit and NOT issued by this agent; likely a stray cleanup / another
  session). Tasks 9-14 (runs 4-5) never launched. Partial CORAL: run1/2 had only
  2-3 of 5 notes done after 4h27m.
- **41711380** (array `0-14%6`, `--requeue`): RESUBMIT. main.py skips notes whose
  output CSV already exists, so the 3 complete 4CE runs are instant skips; 4CE
  runs 4-5 (~2h each, reliable) + CORAL resume from partial.

**CORAL is the bottleneck (timing from 41679908):** a single CORAL note takes
~2-3h wall-clock (`coral_breastca_22`: 11:54→14:43 = 2h49m), vs 4CE ~10-70 min/note
(whole 10-note 4CE cell ~2h). CORAL notes are full pathology reports. 5 CORAL
notes × 5 runs ≈ 37h/slice even parallelized — at the edge of feasibility. The
reliable core deliverable is **4CE × 5 runs (n=10 notes)**; CORAL is best-effort
and may land partial.

---

## 7b. Codex adversarial review (per pref §6)

Ran a codex adversarial review on `jobs/EXP-J_cell.sh` + `compute_consistency.py`.
The companion connection died mid-run (known instability) before emitting a final
ranked verdict, but its investigation log covered all concern areas and surfaced
one concrete finding:

- **`rstrip('.txt')` bug** in the inherited `main.py` (`note_id_for_key =
  note_filename.rstrip('.txt')` and the note_id_list filter). `str.rstrip` strips
  a *character set* `{., t, x}`, not the `.txt` suffix. **Verified non-impacting
  for EXP-J**: all 20 selected ids (`BCH_1`..`COL_3`, `20`..`24`, `0`/`1`/`10`/`11`/`12`)
  end in digits or `_<digit>`, none in `{., t, x}`, so each round-trips correctly
  (`'BCH_1.txt'.rstrip('.txt') == 'BCH_1'`). Pre-existing frozen-paper-code bug,
  out of scope to fix here (fixing main.py mid-run = new EXP-ID per §9.2). Logged
  for a future cleanup PR.
- Codex was also probing whether per-note workers fan out to multiple LLM modules
  (which would amplify concurrency beyond the 60-call estimate) — already mitigated
  by the `%6` array throttle (≤6 cells × 4 workers concurrent).

Independently verified by me: array-id→(R,slice) arithmetic enumerates all 15
cells exactly once; output paths fully isolated per (run,slice); `main.py`'s
output-exists skip is keyed on `{marker}_{noteid}` where marker embeds the run
number, so it never leaks across the 5 runs (only idempotent same-cell resume);
both scripts pass `bash -n` / `py_compile`.

## 8. Results

_(backfilled on COMPLETED)_

## 9. vs baseline / interpretation

_(backfilled)_

## 10. Analysis

_(backfilled)_

## 11. Conclusion

_(backfilled — one line)_

## 12. Next step

_(backfilled)_

## 13. Artifact pointers

- Predictions: `runs/EXP-J/run{1..5}/<slice>/EXP-J_run{R}_<slice>_<noteid>_default.csv`
- Metrics JSON: `runs/EXP-J/consistency_metrics.json`
- Metric script: `runs/EXP-J/compute_consistency.py`
- Job script: `jobs/EXP-J_cell.sh` (job array, on exp branch)
- SLURM logs: `runs/EXP-J/logs/cell-41679908_{0..14}.{out,err}`
