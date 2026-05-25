#!/usr/bin/env bash
#SBATCH --job-name=EXP-F_baseline
#SBATCH --time=08:00:00
#SBATCH --mem=8G
#SBATCH -c 2
#SBATCH -p short
#SBATCH -o logs/slurm/%x_%j.out
#SBATCH -e logs/slurm/%x_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=zongxin_yang@hms.harvard.edu

# EXP-F single-call / CoT baseline runner.
#
# Inputs via env vars (set on the `sbatch --export=...` command line):
#   MODEL          required: 'o3-mini-0131' or 'gpt-4o-1120'
#   MODE           required: 'single' or 'cot'
#   DATASETS       required: space-separated dataset dirs (e.g. "4CE coral_annotated_pdac")
#   AGENT_LABEL    required: tag for the agent_type column ('o3mini_sp' / 'gpt4o_cot')
#   PROJECT_ROOT   required: absolute path to language-into-clinical-data
#   OUTPUT_DIR     required: absolute path for predictions + usage
#   CONDA_PYTHON   required: absolute path to python interpreter with deps
#   OPENAIKEY      required: HMS Azure OpenAI key (forwarded via --export)
#   OPENAIENDPOINT optional: default https://azure-ai.hms.edu (forwarded)
#   HOLD_ON_FAIL   optional: 1 to keep node alive on failure (default 0)

set -euo pipefail

# Source slurm_failure_hold (no-op unless HOLD_ON_FAIL=1).
source "${PROJECT_ROOT}/scripts/slurm_failure_hold.sh"

# Fail-fast on missing required inputs (CLAUDE.md §2).
: "${MODEL:?MODEL env var required}"
: "${MODE:?MODE env var required}"
: "${DATASETS:?DATASETS env var required (space-separated)}"
: "${AGENT_LABEL:?AGENT_LABEL env var required}"
: "${PROJECT_ROOT:?PROJECT_ROOT env var required}"
: "${OUTPUT_DIR:?OUTPUT_DIR env var required}"
: "${CONDA_PYTHON:?CONDA_PYTHON env var required}"
: "${OPENAIKEY:?OPENAIKEY env var required (HMS Azure OpenAI key)}"
export OPENAIENDPOINT="${OPENAIENDPOINT:-https://azure-ai.hms.edu}"

mkdir -p "$OUTPUT_DIR"
mkdir -p "${PROJECT_ROOT}/logs/slurm"

echo "=== EXP-F baseline run ==="
echo "  JOB_ID:       ${SLURM_JOB_ID:-local}"
echo "  Node:         $(hostname)"
echo "  Started:      $(date -Iseconds)"
echo "  MODEL:        $MODEL"
echo "  MODE:         $MODE"
echo "  DATASETS:     $DATASETS"
echo "  AGENT_LABEL:  $AGENT_LABEL"
echo "  PROJECT_ROOT: $PROJECT_ROOT"
echo "  OUTPUT_DIR:   $OUTPUT_DIR"
echo "  CONDA_PYTHON: $CONDA_PYTHON"
echo "  HOLD_ON_FAIL: ${HOLD_ON_FAIL:-0}"
echo "=========================="

# Sanity-check PROJECT_ROOT looks right BEFORE cd'ing. If the env var
# points somewhere wrong (e.g. user typo, stale path), failing here is
# better than running with cwd=$HOME and writing artifacts in random
# places. Same hardening pattern as EXP-G (jobs/EXP-G_run.sh).
if [[ ! -d "$PROJECT_ROOT/data" || ! -d "$PROJECT_ROOT/jobs" || ! -f "$PROJECT_ROOT/scripts/baselines/single_call_baseline.py" ]]; then
    echo "ERROR: PROJECT_ROOT=$PROJECT_ROOT does not look like the CLINES project root" >&2
    echo "  (missing data/, jobs/, or scripts/baselines/single_call_baseline.py)" >&2
    exit 2
fi
cd "$PROJECT_ROOT"

# Run. `eval` to expand DATASETS as separate args (it's intentionally one
# string for sbatch --export friendliness).
cmd=( "$CONDA_PYTHON" "scripts/baselines/single_call_baseline.py"
      --model "$MODEL"
      --mode "$MODE"
      --datasets $DATASETS
      --data-root "${PROJECT_ROOT}/data"
      --gold-root "${PROJECT_ROOT}/outputs/reviewed_updated2"
      --output-dir "$OUTPUT_DIR"
      --agent-label "$AGENT_LABEL"
      --chunk-size-tokens 768
      --chunk-max-retries 2
      --log-level INFO )

if [[ -n "${MAX_NOTES:-}" ]]; then
    cmd+=( --max-notes "$MAX_NOTES" )
fi
if [[ -n "${START_INDEX:-}" ]]; then
    cmd+=( --start-index "$START_INDEX" )
fi

echo "+ ${cmd[*]}"
"${cmd[@]}"

echo "=== EXP-F baseline run COMPLETE: $(date -Iseconds) ==="
