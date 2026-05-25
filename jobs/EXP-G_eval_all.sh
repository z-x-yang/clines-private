#!/bin/bash
# EXP-G eval — for each (ablation, dataset), run scripts/eval_predictions.py
# against the matched 5-note gold slice and dump a metrics.json per cell.
#
# Strategy: the predictions land in runs/EXP-G/preds/<ablation>/<dataset>/.
# We need to match the eval_predictions.py file-naming convention
# (`<dataset_dir>_<note_id>_default_<model>_with_positions.csv`), which it
# expects in a flat prediction directory. Our marker writes files as
# `<MARKER>_<note_id>_<schema>.csv` = e.g.
# `EXP-G_full_4CE_BCH_1_default.csv`. We therefore generate a small symlink
# tree per (ablation, dataset) under runs/EXP-G/eval/<ablation>/<dataset>/
# that bridges these names, then point eval_predictions.py at it.

set -euo pipefail

ABLATIONS=(full sapbert_off semchunk_off date_off step4_off)
DATASETS=(4CE coral_pdac coral_breastca)
MODEL_NAME="${MODEL_NAME:-gpt4o}"
GT_ROOT="outputs/reviewed_updated2"

# Map dataset key → groundtruth subdir name expected by eval_predictions.py
declare -A GT_DIR=( \
    [4CE]=4CE \
    [coral_pdac]=coral_annotated_pdac \
    [coral_breastca]=coral_annotated_breastca \
)

source /home/zoy043/miniconda3/etc/profile.d/conda.sh
conda activate sglang

for abl in "${ABLATIONS[@]}"; do
    for ds in "${DATASETS[@]}"; do
        marker="EXP-G_${abl}_${ds}"
        pred_src="runs/EXP-G/preds/${abl}/${ds}"
        eval_dir="runs/EXP-G/eval/${abl}/${ds}"
        gt_subdir="${GT_DIR[$ds]}"

        if [[ ! -d "${pred_src}" ]]; then
            echo "SKIP ${marker}: ${pred_src} missing (job not yet complete or failed)"
            continue
        fi

        mkdir -p "${eval_dir}/preds_named" "${eval_dir}/gt"

        # Symlink predictions into eval_predictions.py's expected layout.
        # Source files are named: <marker>_<note_id>_default.csv
        # Target files must be:   <gt_subdir>_<note_id>_default_<model>_with_positions.csv
        shopt -s nullglob
        for f in "${pred_src}/${marker}_"*_default.csv; do
            note_id=$(basename "$f" "_default.csv")
            note_id="${note_id#${marker}_}"
            tgt="${eval_dir}/preds_named/${gt_subdir}_${note_id}_default_${MODEL_NAME}_with_positions.csv"
            ln -sf "$(readlink -f "$f")" "${tgt}"
        done
        shopt -u nullglob

        # Build gt tree expected by eval_predictions.py: <eval_dir>/gt/<gt_subdir>/<note>_updated.csv
        gt_target="${eval_dir}/gt/${gt_subdir}"
        mkdir -p "${gt_target}"
        # Only link the 5 representative gold files (so eval ignores the rest)
        while IFS= read -r note_id; do
            [[ -z "$note_id" || "$note_id" =~ ^# ]] && continue
            src="${GT_ROOT}/${gt_subdir}/${note_id}_updated.csv"
            if [[ -f "$src" ]]; then
                ln -sf "$(readlink -f "$src")" "${gt_target}/${note_id}_updated.csv"
            else
                echo "ERROR: missing gold for ${gt_subdir}/${note_id}" >&2
                exit 3
            fi
        done < "runs/EXP-G/notes_lists/${ds}.txt"

        OUT_JSON="${eval_dir}/metrics.json"
        echo "==> eval ${marker}"
        # fail-fast: do not swallow eval errors; bubble up
        python scripts/eval_predictions.py \
            --prediction_dir "${eval_dir}/preds_named" \
            --groundtruth_dir "${eval_dir}/gt" \
            --columns mention assertion_status value unit code \
            --output_file "${OUT_JSON}" \
            --model_name "${MODEL_NAME}" \
            --no_note_metrics
    done
done

echo "Done. Per-cell metrics: runs/EXP-G/eval/<abl>/<dataset>/metrics.json"
