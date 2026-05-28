#!/usr/bin/env bash
# Build script for BMJ Digital Health & AI Major Revision (2026-05-26).
#
# Compiles two PDFs from the SAME lancet_draft.tex by toggling the \revmode
# flag at the top of the .tex via sed (with a safe backup-and-restore):
#   lancet_draft_revised.pdf   blue-highlighted additions (\revmodetrue)
#   lancet_draft_clean.pdf     clean revised manuscript  (\revmodefalse)
#
# Requires: pdflatex + bibtex on PATH (TeX Live 2022+ recommended).
#
# Usage:
#   bash build_revision.sh           build both variants
#   bash build_revision.sh rev       only revised (blue marks)
#   bash build_revision.sh clean     only clean (no marks)

set -euo pipefail

cd "$(dirname "$0")"
MAIN="lancet_draft"

command -v pdflatex >/dev/null || { echo "ERROR: pdflatex not found on PATH"; exit 1; }
command -v bibtex   >/dev/null || { echo "ERROR: bibtex not found on PATH"; exit 1; }

# Always restore original .tex on exit (success, failure, or Ctrl-C).
cp "${MAIN}.tex" "${MAIN}.tex.bak"
trap 'mv -f "${MAIN}.tex.bak" "${MAIN}.tex" 2>/dev/null || true' EXIT

set_revmode() {
    # $1 = true | false   ->  rewrite the toggle line in-place.
    local mode="$1"
    # Restore from backup first so each variant builds from a known state.
    cp -f "${MAIN}.tex.bak" "${MAIN}.tex"
    case "$mode" in
        true)  sed -i 's/^\\revmodefalse/\\revmodetrue/'  "${MAIN}.tex" ;;
        false) sed -i 's/^\\revmodetrue/\\revmodefalse/'  "${MAIN}.tex" ;;
        *) echo "internal error: set_revmode $mode"; exit 2 ;;
    esac
}

run_passes() {
    # $1 = output jobname (without .pdf)
    local jobname="$1"
    pdflatex -interaction=nonstopmode -jobname="${jobname}" "${MAIN}.tex" > "${jobname}.build.log" 2>&1 || { tail -50 "${jobname}.build.log"; exit 1; }
    bibtex "${jobname}" >> "${jobname}.build.log" 2>&1 || true
    pdflatex -interaction=nonstopmode -jobname="${jobname}" "${MAIN}.tex" > /dev/null 2>&1
    pdflatex -interaction=nonstopmode -jobname="${jobname}" "${MAIN}.tex" > /dev/null 2>&1
}

build_variant() {
    local variant="$1"
    local mode="$2"
    local out="${MAIN}_${variant}"
    echo "=== building ${out}.pdf  (revmode=${mode}) ==="
    set_revmode "${mode}"
    run_passes "${out}"
    [[ -f "${out}.pdf" ]] && echo "  -> ${out}.pdf"
}

case "${1:-both}" in
    rev|revised) build_variant revised true ;;
    clean)       build_variant clean   false ;;
    both|"")
        build_variant revised true
        build_variant clean   false
        ;;
    *) echo "Usage: $0 [rev|clean|both]"; exit 2 ;;
esac

echo
echo "=== output PDFs ==="
ls -la "${MAIN}_revised.pdf" "${MAIN}_clean.pdf" 2>/dev/null || true
