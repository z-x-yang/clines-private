#!/usr/bin/env bash
#SBATCH --job-name=EXP-H_dl_baseline
#SBATCH --partition=gpu_quad
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/slurm/EXP-H_%j.out
#SBATCH --error=logs/slurm/EXP-H_%j.err

# EXP-H DL baseline (BMJ R5 A4 / R3 C8): inference of two full-size HF NER
# models on 4CE / CORAL-BreastCA / CORAL-PDAC, output in CLINES with_positions/
# schema so scripts/eval_predictions.py can score against reviewed_updated2.
#
# Models:
#   - samrawal/bert-base-uncased_clinical-ner   (BERT-base 110M, i2b2 problem/test/treatment)
#   - longluu/Clinical-NER-MedMentions-GatorTronBase  (GatorTron-base 345M, MedMentions semantic types)
#
# Inference only (no fine-tune). Both models published on HF with NER heads
# already trained on their respective NER corpora.

set -euo pipefail

# scripts/slurm_failure_hold.sh canonical template (CLAUDE.md §7).
# Default OFF; submit with HOLD_ON_FAIL=1 sbatch jobs/EXP-H_dl_baseline.sh to enable.
source scripts/slurm_failure_hold.sh

PROJECT_ROOT="/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data"
WORKTREE="${PROJECT_ROOT}/.claude/worktrees/agent-abc0b1625fcda06e4"
cd "$WORKTREE"

# pretrained models cached here so they survive cluster scratch wipes
export HF_HOME="${HF_HOME:-${HOME}/.cache/huggingface}"

CONDA_PY=/home/zoy043/miniconda3/envs/generel/bin/python
echo "[exp-h] python=$($CONDA_PY -c 'import sys; print(sys.executable)')"
echo "[exp-h] torch=$($CONDA_PY -c 'import torch; print(torch.__version__, torch.cuda.is_available())')"
echo "[exp-h] transformers=$($CONDA_PY -c 'import transformers; print(transformers.__version__)')"
echo "[exp-h] gpu=$(nvidia-smi -L 2>/dev/null || echo none)"

RUN_DIR="${WORKTREE}/runs/EXP-H"
mkdir -p "${RUN_DIR}/eval"

DATA_ROOT="${PROJECT_ROOT}/data"
GOLD_ROOT="${PROJECT_ROOT}/outputs/reviewed_updated2"

# Pre-flight checks (fail-fast before consuming GPU time)
for ds in 4CE coral_annotated_breastca coral_annotated_pdac; do
    if ! compgen -G "${DATA_ROOT}/${ds}/*.txt" > /dev/null; then
        echo "[exp-h] FATAL: no .txt files in ${DATA_ROOT}/${ds}"
        exit 10
    fi
    if ! compgen -G "${GOLD_ROOT}/${ds}/*_updated.csv" > /dev/null; then
        echo "[exp-h] FATAL: no gold *_updated.csv in ${GOLD_ROOT}/${ds}"
        exit 11
    fi
done
echo "[exp-h] pre-flight datasets OK"

# Pre-warm HF cache by probing each model config; fails loudly if HF unreachable
for mid in samrawal/bert-base-uncased_clinical-ner longluu/Clinical-NER-MedMentions-GatorTronBase; do
    if ! "$CONDA_PY" -c "from transformers import AutoConfig; AutoConfig.from_pretrained('${mid}')" 2>&1; then
        echo "[exp-h] FATAL: cannot reach HF for ${mid}"
        exit 12
    fi
done
echo "[exp-h] pre-flight HF models reachable"

run_one () {
    local marker="$1"
    local model_name="$2"
    local dataset="$3"

    local out_dir="${RUN_DIR}/preds/${marker}/${dataset}"
    mkdir -p "$out_dir"

    echo "[exp-h] >>> ${marker} on ${dataset}"
    "$CONDA_PY" scripts/dl_baseline/infer_hf_ner.py \
        --input_dir "${DATA_ROOT}/${dataset}" \
        --gold_dir "${GOLD_ROOT}/${dataset}" \
        --output_dir "${out_dir}" \
        --model_name "${model_name}" \
        --marker "${marker}" \
        --dataset "${dataset}" \
        --max_seq_length 512 \
        --batch_size 8 \
        --device cuda
}

# === inference: 2 models x 3 datasets = 6 runs ===
# BERT-base clinical NER (i2b2 problem/test/treatment)
run_one bertbase_clin   samrawal/bert-base-uncased_clinical-ner          4CE
run_one bertbase_clin   samrawal/bert-base-uncased_clinical-ner          coral_annotated_breastca
run_one bertbase_clin   samrawal/bert-base-uncased_clinical-ner          coral_annotated_pdac

# GatorTron-base MedMentions NER (345M, UMLS-ish semantic types)
run_one gatortron_base  longluu/Clinical-NER-MedMentions-GatorTronBase   4CE
run_one gatortron_base  longluu/Clinical-NER-MedMentions-GatorTronBase   coral_annotated_breastca
run_one gatortron_base  longluu/Clinical-NER-MedMentions-GatorTronBase   coral_annotated_pdac

# === merge into a single with_positions dir per marker so eval can ingest ===
# Fail-fast (CLAUDE.md §2): if any per-dataset inference left no files, abort
# rather than silently producing partial eval numbers downstream.
EXPECTED_FILES=49   # 21 (4CE) + 13 (coral_breastca) + 15 (coral_pdac) gold notes
for marker in bertbase_clin gatortron_base; do
    merged="${RUN_DIR}/preds/${marker}/with_positions_all"
    mkdir -p "$merged"
    for ds in 4CE coral_annotated_breastca coral_annotated_pdac; do
        src_dir="${RUN_DIR}/preds/${marker}/${ds}/with_positions"
        if [[ ! -d "$src_dir" ]] || ! compgen -G "${src_dir}/*.csv" > /dev/null; then
            echo "[exp-h] FATAL: ${marker} ${ds} produced no with_positions/*.csv (dir=${src_dir})"
            exit 5
        fi
        cp "${src_dir}/"*.csv "$merged/"
    done
    got=$(ls "$merged" | wc -l)
    echo "[exp-h] merged ${marker} -> ${got} files (expected ${EXPECTED_FILES})"
    if [[ "$got" -ne "$EXPECTED_FILES" ]]; then
        echo "[exp-h] FATAL: ${marker} merged count ${got} != expected ${EXPECTED_FILES}"
        exit 6
    fi
done

# === evaluation: CLINES eval pipeline with --columns mention ===
TS=$(date +"%Y%m%d_%H%M%S")
for marker in bertbase_clin gatortron_base; do
    out_json="${RUN_DIR}/eval/${marker}_eval_${TS}.json"
    echo "[exp-h] evaluating ${marker} -> ${out_json}"
    "$CONDA_PY" scripts/eval_predictions.py \
        --prediction_dir "${RUN_DIR}/preds/${marker}/with_positions_all" \
        --groundtruth_dir "${GOLD_ROOT}" \
        --columns mention \
        --output_file "${out_json}" \
        --model_name "${marker}" \
        --no_note_metrics
done

echo "[exp-h] DONE. Eval outputs in ${RUN_DIR}/eval/"
ls -la "${RUN_DIR}/eval/"
