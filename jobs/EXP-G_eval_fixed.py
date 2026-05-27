"""Corrected EXP-G / EXP-G2 ablation eval.

The committed jobs/EXP-G_eval_all.sh symlinks the raw `default`-schema pred
CSVs straight into eval_predictions.py, but those carry mention_start_pos /
mention_end_pos, while eval_predictions.py (and the gold) need start_pos /
end_pos computed by the canonical scripts/process_entity_index.py
--use_sequential builder (the same step that produced outputs/with_positions/
for the paper's main results). This runner inserts that missing step so the
ablation numbers are computed the SAME way as the main results.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data")
PY = "/home/zoy043/miniconda3/envs/sglang/bin/python"

GT_DIR = {"4CE": "4CE", "coral_pdac": "coral_annotated_pdac", "coral_breastca": "coral_annotated_breastca"}
NOTE_DATA = {"4CE": "data/4CE", "coral_pdac": "data/coral_annotated_pdac", "coral_breastca": "data/coral_annotated_breastca"}
NOTES = {"4CE": ["KUMC_5", "d30982c684512d4f0b6fd79836539d9ac"], "coral_pdac": ["14", "1"], "coral_breastca": ["34", "36"]}
ABLATIONS = ["full", "sapbert_off", "semchunk_off", "date_off", "step4_off"]
DATASETS = ["4CE", "coral_pdac", "coral_breastca"]

GRIDS = [
    {"exp": "EXP-G", "wt": ROOT / ".claude/worktrees/agent-a15417ba335fb18f3", "marker": "EXP-G", "model": "gpt4o"},
    {"exp": "EXP-G2", "wt": ROOT / ".claude/worktrees/agent-expg2-gpt4omini", "marker": "EXP-G2", "model": "gpt4omini"},
]

summary = {}
for g in GRIDS:
    exp, wt, marker, model = g["exp"], g["wt"], g["marker"], g["model"]
    summary[exp] = {}
    for abl in ABLATIONS:
        for ds in DATASETS:
            gt_sub = GT_DIR[ds]
            pred_src = wt / f"runs/{exp}/preds/{abl}/{ds}"
            eval_dir = wt / f"runs/{exp}/eval/{abl}/{ds}"
            preds_named = eval_dir / "preds_named"
            gt_tree = eval_dir / "gt" / gt_sub
            preds_named.mkdir(parents=True, exist_ok=True)
            gt_tree.mkdir(parents=True, exist_ok=True)

            for note in NOTES[ds]:
                raw = pred_src / f"{marker}_{abl}_{ds}_{note}_default.csv"
                if not raw.exists():
                    print(f"MISSING raw pred: {raw}", file=sys.stderr); sys.exit(2)
                note_txt = ROOT / NOTE_DATA[ds] / f"{note}.txt"
                out_csv = preds_named / f"{gt_sub}_{note}_default_{model}_with_positions.csv"
                r = subprocess.run([PY, "scripts/process_entity_index.py",
                                    "--note_path", str(note_txt), "--csv_path", str(raw),
                                    "--output_path", str(out_csv), "--agent_type", model,
                                    "--use_sequential"], cwd=ROOT, capture_output=True, text=True)
                if r.returncode != 0:
                    print(f"position-build FAILED {exp}/{abl}/{ds}/{note}:\n{r.stderr[-800:]}", file=sys.stderr); sys.exit(3)
                # gold symlink
                gsrc = ROOT / f"outputs/reviewed_updated2/{gt_sub}/{note}_updated.csv"
                if not gsrc.exists():
                    print(f"MISSING gold: {gsrc}", file=sys.stderr); sys.exit(4)
                gdst = gt_tree / f"{note}_updated.csv"
                if gdst.is_symlink() or gdst.exists():
                    gdst.unlink()
                gdst.symlink_to(gsrc)

            out_json = eval_dir / "metrics.json"
            r = subprocess.run([PY, "scripts/eval_predictions.py",
                                "--prediction_dir", str(preds_named),
                                "--groundtruth_dir", str(eval_dir / "gt"),
                                "--columns", "mention", "assertion_status", "value", "unit", "code",
                                "--output_file", str(out_json),
                                "--model_name", model, "--no_note_metrics"],
                               cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"eval FAILED {exp}/{abl}/{ds}:\n{r.stderr[-1500:]}", file=sys.stderr); sys.exit(5)
            m = json.loads(out_json.read_text())
            summary[exp][f"{abl}/{ds}"] = m
            print(f"OK {exp}/{abl}/{ds}")

Path("/tmp/expg_eval_summary.json").write_text(json.dumps(summary, indent=2, default=str))
print("\nDONE -> /tmp/expg_eval_summary.json")
