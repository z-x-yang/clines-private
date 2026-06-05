#!/usr/bin/env bash
# Repackage CLINES BMJ R2 Overleaf zip from current live source files.
# Source of truth:
#   - overleaf_template/  -> wrapper TeX (master.tex, Manuscript.tex,
#     Supplement.tex, Cover_Letter.tex, Response_to_Reviewers.tex),
#     bibstyles (*.bst), author_template.tsv, README.md
#   - Submission/CLINES latex bmj/sections/                -> main-text bodies
#   - Submission/CLINES latex bmj/supplement_sections/     -> supplement bodies
#   - Submission/CLINES latex bmj/references.bib           -> bib
#   - Submission/CLINES latex bmj/figures/*.tex            -> figure wrappers
#   - Submission/CLINES latex bmj/figures/figure{1,2,3}.pdf -> figure 1/2/3 PDFs
#   - Major Revision/figures/figure{4,5}.pdf               -> updated figure 4 & 5 PDFs
#   - Major Revision/response/Cover_Letter.tex             -> body for Cover Letter
#   - Major Revision/response/Response_to_Reviewers.tex    -> body for Response

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PAPER="$(cd "$HERE/.." && pwd)"
LIVE="$PAPER/Submission/CLINES latex bmj"
TEMPLATE="$HERE/overleaf_template"
OUT_ZIP="$HERE/CLINES_BMJ_R2_Overleaf.zip"

[[ -d "$LIVE"     ]] || { echo "ERROR: live source not found at $LIVE";    exit 1; }
[[ -d "$TEMPLATE" ]] || { echo "ERROR: template dir not found at $TEMPLATE"; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
DEST="$STAGE/clines-bmj-r2-overleaf"

echo "[1/5] Stage Overleaf wrapper (template) + bib + bibstyles..."
mkdir -p "$DEST"
cp "$TEMPLATE/master.tex"                 "$DEST/master.tex"
cp "$TEMPLATE/Manuscript.tex"             "$DEST/Manuscript.tex"
cp "$TEMPLATE/Supplement.tex"             "$DEST/Supplement.tex"
cp "$TEMPLATE/Cover_Letter.tex"           "$DEST/Cover_Letter.tex"
cp "$TEMPLATE/Response_to_Reviewers.tex"  "$DEST/Response_to_Reviewers.tex"
cp "$TEMPLATE/README.md"                  "$DEST/README.md"
cp "$TEMPLATE/author_template.tsv"        "$DEST/author_template.tsv"
cp "$TEMPLATE"/elsarticle-*.bst           "$DEST/"

echo "[2/5] Refresh sections, supplement_sections (canonical .tex only), references.bib..."
mkdir -p "$DEST/sections" "$DEST/supplement_sections"
for f in "$LIVE/sections"/*.tex; do
    base="$(basename "$f")"
    [[ "$base" == "cover letter.tex" ]] && continue   # stray, not in master.tex
    cp "$f" "$DEST/sections/$base"
done
for f in "$LIVE/supplement_sections"/*.tex; do
    cp "$f" "$DEST/supplement_sections/$(basename "$f")"
done
cp "$LIVE/references.bib" "$DEST/references.bib"

echo "[3/5] Stage figures (PDFs + LaTeX wrappers)..."
mkdir -p "$DEST/figures"
for fig in figure1 figure2 figure3; do
    cp "$LIVE/figures/${fig}.pdf" "$DEST/figures/${fig}.pdf"
done
cp "$HERE/figures/figure4.pdf"             "$DEST/figures/figure4.pdf"   # latest figure 4 (IAA + hallucination)
cp "$HERE/figures/figure5.pdf"             "$DEST/figures/figure5.pdf"   # latest figure 5 (robustness + cost)
for fig in figure1 figure2 figure3 figure4 figure5; do
    cp "$LIVE/figures/${fig}.tex" "$DEST/figures/${fig}.tex"
done

echo "[4/5] Rebuild body files from live Cover_Letter / Response..."
# Extract content between \begin{document} and \end{document}.
extract_body() {
    local src="$1"
    local dst="$2"
    sed -n '/\\begin{document}/,/\\end{document}/p' "$src" \
        | sed -e '1d' -e '$d' > "$dst"
}
extract_body "$HERE/response/Cover_Letter.tex"          "$DEST/cover_letter_body.tex"
extract_body "$HERE/response/Response_to_Reviewers.tex" "$DEST/response_body.tex"

echo "[5/5] Repack..."
rm -f "$OUT_ZIP"
(cd "$STAGE" && zip -qr "$OUT_ZIP" clines-bmj-r2-overleaf)

echo "Done. $OUT_ZIP"
ls -lh "$OUT_ZIP"
