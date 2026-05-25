#!/usr/bin/env bash
# slurm_failure_hold.sh — Hold the SLURM allocation alive when a job fails,
# so the user can ssh in, attach a tmux session, and continue debugging
# without losing queue priority by re-submitting.
#
# Usage:
#   1. Copy / symlink this file into <project>/scripts/slurm_failure_hold.sh
#      (canonical template lives at ~/.claude/templates/slurm_failure_hold.sh,
#       referenced from CLAUDE.md §7).
#   2. In your sbatch script, after `set -euo pipefail`:
#         source scripts/slurm_failure_hold.sh
#      MUST be sourced BEFORE any other `trap ... EXIT` setup. If an EXIT trap
#      is already installed when this file is sourced, it will exit 2 with a
#      clear error message (we deliberately do NOT silently overwrite — that
#      would lose your other cleanup logic; this aligns with §2 fail-fast).
#   3. Submit with HOLD_ON_FAIL=1 to enable, e.g.:
#         HOLD_ON_FAIL=1 sbatch jobs/train.sh
#      Default (HOLD_ON_FAIL unset or 0): trap not installed, job unchanged.
#
# On failure (when enabled):
#   - Prints `ssh <host>` + `tmux a -t debug_$SLURM_JOB_ID` hints
#     (or "tmux not available - ssh in directly" if tmux missing)
#   - Sleeps until min(walltime - 5min capped at 24h, release file created)
#   - Preserves original exit code; sacct still records FAILED
#   - SIGTERM (e.g. `scancel`) breaks the sleep and exits immediately
#
# Compliance with CLAUDE.md §2 fail-fast:
#   - Default OFF (opt-in via env var), never a hidden behavior
#   - Existing EXIT traps are NOT silently replaced — script exits loudly
#   - Exit code preserved, sacct = FAILED, ssh/tmux hints logged loudly
#   - Semantics: "fail and release" -> "fail and hold for debug, then release"

if [[ "${HOLD_ON_FAIL:-0}" == "1" ]]; then
    # Refuse to clobber an existing EXIT trap. Chaining traps generically is
    # error-prone (escaping, signal context), so we fail loudly and let the
    # user decide how to compose handlers.
    __sfh_existing_trap=$(trap -p EXIT 2>/dev/null || true)
    if [[ -n $__sfh_existing_trap ]]; then
        echo "[slurm_failure_hold] ERROR: an EXIT trap is already installed:" >&2
        echo "    $__sfh_existing_trap" >&2
        echo "[slurm_failure_hold] Refusing to silently overwrite. Source this file BEFORE any other trap, or wrap your existing handler into __sfh_on_exit manually." >&2
        unset __sfh_existing_trap
        exit 2
    fi
    unset __sfh_existing_trap

    __sfh_have_tmux=0
    if command -v tmux >/dev/null 2>&1; then
        __sfh_have_tmux=1
    fi

    __sfh_session="debug_${SLURM_JOB_ID:-local$$}"
    if [[ $__sfh_have_tmux -eq 1 ]]; then
        # Per-job session name avoids collision with stale sessions from
        # prior failed jobs.
        tmux new-session -d -s "$__sfh_session" 2>/dev/null || true
    fi

    # User-private release-file directory under TMPDIR. Mode 0700 prevents
    # other users on shared nodes from creating the release token to force
    # an early release.
    __sfh_release_dir="${TMPDIR:-/tmp}/slurm_failure_hold/${USER:-unknown}"
    mkdir -p "$__sfh_release_dir" 2>/dev/null || true
    chmod 0700 "$__sfh_release_dir" 2>/dev/null || true

    __sfh_walltime_to_sec() {
        # Convert SLURM TimeLimit string to seconds.
        # Formats accepted: D-HH:MM:SS | HH:MM:SS | MM:SS | SS | UNLIMITED
        local s=${1:-01:00:00}
        if [[ $s == "UNLIMITED" ]]; then
            # Cap at 24h: a forgotten release should not hold a node for days.
            echo $((24 * 3600))
            return
        fi
        local days=0 rest=$s
        if [[ $rest == *-* ]]; then
            days=${rest%%-*}
            rest=${rest#*-}
        fi
        local a b c
        IFS=: read -r a b c <<< "$rest"
        local h=0 m=0 sec=0
        if [[ -n ${c:-} ]]; then
            h=$a; m=$b; sec=$c
        elif [[ -n ${b:-} ]]; then
            m=$a; sec=$b
        else
            sec=$a
        fi
        echo $((10#${days:-0} * 86400 + 10#${h:-0} * 3600 + 10#${m:-0} * 60 + 10#${sec:-0}))
    }

    __sfh_on_exit() {
        local rc=$?
        if [[ $rc -eq 0 ]]; then
            return 0
        fi

        # In failure-handling territory we relax strict mode so the handler
        # itself cannot tank on a benign command failure (e.g. scontrol absent).
        set +e
        set +u
        set +o pipefail 2>/dev/null

        local host
        host=$(scontrol show node "$(hostname)" 2>/dev/null | grep -oP '\bNodeAddr=\K\S+')
        host=${host:-$(hostname)}

        # Compute REMAINING walltime, not total. RunTime in scontrol output is
        # how long the job has been running; we subtract it from TimeLimit so
        # we don't sleep past the wall and get force-killed (which prevents
        # clean rc preservation and the release message).
        local job_info walltime_str runtime_str total_sec elapsed_sec hold_sec
        job_info=$(scontrol show job "${SLURM_JOB_ID:-}" 2>/dev/null)
        # Anchor matches at field boundary so we don't catch e.g. "Partition_TimeLimit".
        walltime_str=$(echo "$job_info" | grep -oP '\bTimeLimit=\K\S+')
        runtime_str=$(echo "$job_info" | grep -oP '\bRunTime=\K\S+')
        total_sec=$(__sfh_walltime_to_sec "${walltime_str:-01:00:00}")
        elapsed_sec=$(__sfh_walltime_to_sec "${runtime_str:-00:00:00}")
        hold_sec=$((total_sec - elapsed_sec - 300))
        # Cap at 24h regardless of walltime — protects against UNLIMITED or
        # very long allocations being held forever on a forgotten release.
        if [[ $hold_sec -gt $((24 * 3600)) ]]; then
            hold_sec=$((24 * 3600))
        fi
        if [[ $hold_sec -lt 60 ]]; then
            # Walltime nearly up: print a warning so the user knows the hold
            # window is small and SLURM may force-kill before they can attach.
            echo "[slurm_failure_hold] WARNING: remaining walltime is ${hold_sec}s (TimeLimit=${walltime_str:-?}, RunTime=${runtime_str:-?}); SLURM may force-kill before you can attach"
            hold_sec=60
        fi

        local release_file="$__sfh_release_dir/release_${SLURM_JOB_ID:-local$$}"

        echo "================================================================"
        echo "JOB FAILED (exit code $rc) — HOLDING ALLOCATION FOR DEBUG"
        echo
        echo "  ssh $host"
        if [[ $__sfh_have_tmux -eq 1 ]]; then
            echo "  tmux a -t $__sfh_session"
        else
            echo "  (tmux not available — attach directly via ssh, then re-run your debug commands)"
        fi
        echo
        echo "  Release early:  touch $release_file"
        echo "  Auto-release in: ${hold_sec}s (min of remaining-walltime-5min, 24h)"
        echo "================================================================"

        # Reliable signal handling: run sleep in background and kill it from
        # the trap. A foreground `sleep` with `trap 'true'` is not guaranteed
        # to break promptly (bash may queue the signal until sleep returns).
        local __sfh_stop=0
        local __sfh_sleep_pid=0
        trap '__sfh_stop=1; [[ $__sfh_sleep_pid -gt 0 ]] && kill $__sfh_sleep_pid 2>/dev/null' TERM INT

        local elapsed=0
        local step=30
        while [[ ! -f $release_file && $elapsed -lt $hold_sec && $__sfh_stop -eq 0 ]]; do
            sleep $step &
            __sfh_sleep_pid=$!
            wait $__sfh_sleep_pid 2>/dev/null
            __sfh_sleep_pid=0
            elapsed=$((elapsed + step))
        done

        trap - TERM INT

        if [[ $__sfh_stop -eq 1 ]]; then
            echo "[slurm_failure_hold] Interrupted by signal (scancel / SIGTERM); exiting rc=$rc"
        elif [[ -f $release_file ]]; then
            rm -f "$release_file"
            echo "[slurm_failure_hold] Released by user; exiting rc=$rc"
        else
            echo "[slurm_failure_hold] Auto-released after ${elapsed}s (cap ${hold_sec}s); exiting rc=$rc"
        fi
        return $rc
    }

    trap __sfh_on_exit EXIT
fi
