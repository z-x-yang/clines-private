#!/usr/bin/env bash
# Build the FIGURE-FREE main-document variants for the BMJ resubmission.
#
# BMJ editorial requires figures uploaded separately (designation 'Figure'),
# NOT embedded in the main document. The figure legends are entered into
# ScholarOne's per-figure Caption/Legend field, so the body must contain
# NO image AND NO legend text -- only the in-text "Figure N" references must
# still resolve. This script compiles two such no-figure PDFs from the SAME
# lancet_draft.tex:
#   lancet_draft_nofig_clean.pdf     clean revised text   (\revmodefalse)  -> "Main Document"
#   lancet_draft_nofig_revised.pdf   blue tracked changes (\revmodetrue)   -> "Main Document - Marked Copy"
#
# Mechanism: right after \begin{document} (Python literal replace, not sed, to
# avoid \t/\n/\r escape mangling of the LaTeX payload) we inject
#   \renewcommand{\includegraphics}[2][]{}                  % image  -> nothing
#   \renewcommand{\caption}[2][]{\refstepcounter{figure}}   % legend -> step counter only
# The figure float + \label are untouched, so each figure still consumes its
# auto-number and every \ref{fig:...} resolves to 1-4 exactly as in the
# embedded version -- but no image and no legend text appear in the body.
#
# Usage:
#   bash build_nofig.sh           build both variants
#   bash build_nofig.sh clean     only clean
#   bash build_nofig.sh rev       only revised (marked copy)

set -euo pipefail
cd "$(dirname "$0")"
MAIN="lancet_draft"

command -v pdflatex >/dev/null || { echo "ERROR: pdflatex not found on PATH"; exit 1; }
command -v bibtex   >/dev/null || { echo "ERROR: bibtex not found on PATH"; exit 1; }
command -v python3  >/dev/null || { echo "ERROR: python3 not found on PATH"; exit 1; }

# Crash recovery: a leftover .nofigbak means a previous run died before its
# EXIT trap restored the source. The backup is pristine by construction (only
# ever written from a clean .tex below; prepare_tex never touches it), whereas
# lancet_draft.tex may still hold injected \renewcommand lines. Restore it
# first so we never snapshot a contaminated source over a good backup.
if [[ -f "${MAIN}.tex.nofigbak" ]]; then
    echo "WARN: stale ${MAIN}.tex.nofigbak found (previous run crashed); restoring pristine source from it." >&2
    mv -f "${MAIN}.tex.nofigbak" "${MAIN}.tex"
fi

# Snapshot the now-pristine source; EXIT trap restores it (success/fail/Ctrl-C).
cp "${MAIN}.tex" "${MAIN}.tex.nofigbak"
trap 'mv -f "${MAIN}.tex.nofigbak" "${MAIN}.tex" 2>/dev/null || true' EXIT

prepare_tex() {
    # $1 = true|false  -> restore pristine, set revmode, inject figure suppression.
    local mode="$1"
    cp -f "${MAIN}.tex.nofigbak" "${MAIN}.tex"
    case "$mode" in
        true)  sed -i 's/^\\revmodefalse/\\revmodetrue/'  "${MAIN}.tex" ;;
        false) sed -i 's/^\\revmodetrue/\\revmodefalse/'  "${MAIN}.tex" ;;
        *) echo "internal error: prepare_tex $mode"; exit 2 ;;
    esac
    MAIN="${MAIN}" python3 - <<'PY'
import os
p = os.environ["MAIN"] + ".tex"
s = open(p, encoding="utf-8").read()
redef = (r'\renewcommand{\includegraphics}[2][]{}'
         '\n'
         r'\renewcommand{\caption}[2][]{\refstepcounter{figure}}')
needle = r'\begin{document}'
if needle not in s:
    raise SystemExit("FATAL: \\begin{document} not found in " + p)
s = s.replace(needle, needle + "\n" + redef + "\n", 1)
open(p, "w", encoding="utf-8").write(s)
PY
}

run_passes() {
    local out="$1"
    pdflatex -interaction=nonstopmode -jobname="${out}" "${MAIN}.tex" > "${out}.build.log" 2>&1 || { tail -50 "${out}.build.log"; exit 1; }
    # bibtex returns 1 on benign warnings (e.g. undefined-citation) and >=2 on
    # real errors. Surface warnings (don't silently swallow, per fail-fast) but
    # only abort on real errors, so a broken bib can't pass as a clean build.
    local brc=0
    bibtex "${out}" >> "${out}.build.log" 2>&1 || brc=$?
    if [[ $brc -ge 2 ]]; then
        echo "ERROR: bibtex failed (rc=$brc) for ${out}; see ${out}.build.log" >&2
        tail -20 "${out}.build.log" >&2
        exit 1
    elif [[ $brc -eq 1 ]]; then
        echo "WARN: bibtex emitted warnings (rc=1) for ${out}; continuing (see ${out}.build.log)" >&2
    fi
    pdflatex -interaction=nonstopmode -jobname="${out}" "${MAIN}.tex" > /dev/null 2>&1
    pdflatex -interaction=nonstopmode -jobname="${out}" "${MAIN}.tex" > /dev/null 2>&1
}

build_variant() {
    local variant="$1" mode="$2" out="${MAIN}_nofig_${1}"
    echo "=== building ${out}.pdf  (revmode=${mode}, figures suppressed) ==="
    prepare_tex "${mode}"
    run_passes "${out}"
    [[ -f "${out}.pdf" ]] && echo "  -> ${out}.pdf"
}

case "${1:-both}" in
    rev|revised) build_variant revised true ;;
    clean)       build_variant clean   false ;;
    both|"")
        build_variant clean   false
        build_variant revised true
        ;;
    *) echo "Usage: $0 [rev|clean|both]"; exit 2 ;;
esac

echo
echo "=== output PDFs ==="
ls -la "${MAIN}_nofig_clean.pdf" "${MAIN}_nofig_revised.pdf" 2>/dev/null || true
