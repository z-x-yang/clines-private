#!/usr/bin/env bash
# Canonical SLURM job monitor (sacct state + .err/.out grep, dual-track).
#
# Why dual track: when sbatch sources `~/.claude/templates/slurm_failure_hold.sh`
# (HOLD_ON_FAIL=1), a Python crash gets caught by the EXIT trap and turned into
# a sleep loop that holds the SLURM allocation. From `sacct`'s view the job is
# still RUNNING — single-track sacct monitors stay silent for hours over a dead
# Python. We must also grep .err/.out for crash signatures during RUNNING.
#
# See ~/.claude/CLAUDE.md §7 (HOLD_ON_FAIL), §10 (Monitor), §10.5 (resume in
# place rather than scancel + resubmit).
#
# Usage (intended to be wrapped by Claude Code's Monitor tool):
#   bash ~/.claude/templates/slurm_monitor.sh <jobid> <err_log> <out_log> [poll_sec]
#
# Each notable transition / detection prints one line to stdout, which Monitor
# turns into a notification. The script exits when sacct reaches a terminal
# state. CRASH-IN-HOLD is reported once (does not exit) so the eventual
# sacct terminal state is still captured.

set -uo pipefail

if (( $# < 3 )); then
    echo "usage: $0 <jobid> <err_log_path> <out_log_path> [poll_sec=60]" >&2
    exit 2
fi

JOB="$1"
ERR_LOG="$2"
OUT_LOG="$3"
POLL_SEC="${4:-60}"

# Crash signatures we grep for. Tuned for PyTorch / DDP / generic Python crashes.
# Anchors with `^` where the marker is line-leading to reduce false positives
# (e.g. `assert` inside a docstring, `Killed` inside a quoted string).
CRASH_RE='Traceback|RuntimeError|AssertionError|FloatingPointError|CUDA out of memory|OutOfMemoryError|^Killed|^assert |^FAILED'

prev_state=""
crash_emitted=false

while true; do
    state=$(sacct -j "$JOB" -o State -P -n 2>/dev/null | head -1 | tr -d ' ')
    [[ -z "$state" ]] && state="QUEUED"

    if [[ "$state" != "$prev_state" ]]; then
        echo "[$(date +%H:%M:%S)] sbatch $JOB state=$state"
        prev_state="$state"
        if [[ "$state" == "RUNNING" ]]; then
            node=$(sacct -j "$JOB" -o NodeList -P -n 2>/dev/null | head -1 | tr -d ' ')
            echo "[$(date +%H:%M:%S)] sbatch $JOB running on node=$node"
        fi
    fi

    # Dual-track: while sacct says RUNNING, also grep .err/.out for Python
    # crash signatures. Emits ONCE per job (crash_emitted gate) — subsequent
    # iterations skip the grep until sacct catches up to a terminal state.
    if [[ "$state" == "RUNNING" ]] && ! $crash_emitted; then
        if grep -qE "$CRASH_RE" "$ERR_LOG" "$OUT_LOG" 2>/dev/null; then
            node=$(sacct -j "$JOB" -o NodeList -P -n 2>/dev/null | head -1 | tr -d ' ')
            echo "[$(date +%H:%M:%S)] sbatch $JOB CRASH-IN-HOLD detected (sacct=RUNNING but Python crashed; HOLD_ON_FAIL likely active)"
            echo "  ssh $node"
            echo "  tmux a -t debug_${JOB}"
            echo "===.err tail==="
            tail -30 "$ERR_LOG" 2>/dev/null || true
            crash_emitted=true
            # Don't exit — node still allocated, user/agent will ssh in to
            # resume. Loop continues so the eventual sacct terminal state is
            # still captured.
        fi
    fi

    case "$state" in
        COMPLETED|FAILED|CANCELLED*|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|BOOT_FAIL|DEADLINE|REVOKED|PREEMPTED)
            elapsed=$(sacct -j "$JOB" -o Elapsed -P -n 2>/dev/null | head -1 | tr -d ' ')
            echo "[$(date +%H:%M:%S)] sbatch $JOB FINAL state=$state elapsed=$elapsed"
            exit 0
            ;;
    esac
    sleep "$POLL_SEC"
done
