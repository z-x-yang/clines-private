#!/usr/bin/env bash
# Build BMJ upload figure files WITH the caption rendered beneath each image.
#
# ScholarOne R3 requirement (2026-06-05): each separately-uploaded Figure_N.pdf
# must itself contain the figure caption (e.g. the Figure 3 image followed by
# the rendered "Figure 3: ..." legend), and the caption typography must match
# the in-document rendering.
#
# Mechanism: compile each live figure wrapper (figures/figureN.tex, which holds
# the canonical \includegraphics + \caption) as a standalone one-page document
# under the SAME class/preamble as the manuscript (elsarticle
# review,12pt,times,nopreprintline + the \new revision macro with
# \revmodefalse, i.e. clean black), with the figure counter preset so the
# label reads "Figure N". The single page is then tight-cropped with
# Ghostscript (pdfcrop is not installed on O2).
#
# Numbering note (same as build_overleaf_zip.sh / Figure_Captions file):
# main-text Figure 4 is rendered from wrapper figure5.tex (source figure5.pdf);
# the supplement-only figure4.tex/pdf is NOT a main-manuscript upload.
#
# Usage:  bash build_captioned_figures.sh
# Output: BMJ_R2_Resubmission/Figure_{1..4}.pdf  (old files backed up once to
#         BMJ_R2_Resubmission/_pre_caption_backup/)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PAPER="$(cd "$HERE/.." && pwd)"
LIVE="$PAPER/Submission/CLINES latex bmj"
OUT="$HERE/BMJ_R2_Resubmission"
BACKUP="$OUT/_pre_caption_backup"
MARGIN=12   # crop margin in PostScript points

command -v pdflatex >/dev/null || { echo "ERROR: pdflatex not found"; exit 1; }
command -v gs       >/dev/null || { echo "ERROR: ghostscript (gs) not found"; exit 1; }
command -v pdfinfo  >/dev/null || { echo "ERROR: pdfinfo not found"; exit 1; }
[[ -d "$LIVE" ]] || { echo "ERROR: live source not found at $LIVE"; exit 1; }
[[ -d "$OUT"  ]] || { echo "ERROR: output dir not found at $OUT"; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/figures" "$BACKUP"

# Stage figure PDFs: 1-3 from live, figure5 from Major Revision (latest), same
# source-of-truth convention as build_overleaf_zip.sh.
cp "$LIVE/figures/figure1.pdf" "$LIVE/figures/figure2.pdf" "$LIVE/figures/figure3.pdf" "$STAGE/figures/"
cp "$HERE/figures/figure5.pdf" "$STAGE/figures/figure5.pdf"
for w in figure1 figure2 figure3 figure5; do
    cp "$LIVE/figures/${w}.tex" "$STAGE/figures/${w}.tex"
done

# crop_pdf <in> <out>: tight-crop single-page PDF with $MARGIN pt margin.
crop_pdf() {
    local in="$1" out="$2"
    local bbox
    bbox="$(gs -dBATCH -dNOPAUSE -dQUIET -sDEVICE=bbox "$in" 2>&1 | grep '%%HiResBoundingBox' | head -1)"
    [[ -n "$bbox" ]] || { echo "ERROR: gs bbox failed for $in"; exit 1; }
    read -r W H XOFF YOFF <<<"$(awk -v m="$MARGIN" '{x0=$2-m; y0=$3-m; x1=$4+m; y1=$5+m;
        printf "%.2f %.2f %.2f %.2f", x1-x0, y1-y0, -x0, -y0}' <<<"$bbox")"
    gs -q -sDEVICE=pdfwrite -o "$out" \
       -dDEVICEWIDTHPOINTS="$W" -dDEVICEHEIGHTPOINTS="$H" -dFIXEDMEDIA \
       -c "<</PageOffset [$XOFF $YOFF]>> setpagedevice" -f "$in"
    [[ -f "$out" ]] || { echo "ERROR: gs crop produced no output for $in"; exit 1; }
}

# build_one <upload-N> <wrapper-name>
build_one() {
    local n="$1" wrapper="$2" job="Figure_${1}_captioned"
    echo "=== Figure_${n}.pdf  (wrapper ${wrapper}.tex, counter -> Figure ${n}) ==="
    cat > "$STAGE/${job}.tex" <<EOF
\\documentclass[review,12pt,times,nopreprintline]{elsarticle}
\\usepackage{amsmath,amssymb}
\\usepackage[hidelinks]{hyperref}
\\usepackage{float}
\\usepackage{xcolor}
\\usepackage{microtype}
% Tall page, SAME 390pt text width as the manuscript (elsarticle review,12pt):
% caption line breaks/typography stay byte-identical to the in-document
% rendering, while no figure+caption can ever spill to a second page (Figure 3
% fills a manuscript page almost exactly; the standalone [H] float adds ~15pt
% of page-top spacing and would otherwise overflow). The page is tight-cropped
% afterwards, so the extra height never reaches the uploaded file.
\\usepackage[paperwidth=612pt,paperheight=1600pt,textwidth=390pt,textheight=1500pt,hcentering,top=36pt]{geometry}
\\graphicspath{{figures/}}
\\newif\\ifrevmode
\\revmodefalse   % uploaded figure files are the clean (black) version
\\makeatletter
\\long\\def\\new#1{\\ifrevmode{\\color{blue}#1}\\else#1\\fi}
\\makeatother
\\pagestyle{empty}
\\begin{document}
\\setcounter{figure}{$((n - 1))}
\\input{figures/${wrapper}.tex}
\\end{document}
EOF
    (cd "$STAGE" && pdflatex -interaction=nonstopmode "${job}.tex" > "${job}.build.log" 2>&1) \
        || { tail -30 "$STAGE/${job}.build.log"; echo "ERROR: pdflatex failed for ${job}"; exit 1; }
    local pages
    pages="$(pdfinfo "$STAGE/${job}.pdf" | awk '/^Pages:/{print $2}')"
    [[ "$pages" == "1" ]] || { echo "ERROR: ${job}.pdf has $pages pages (expected 1)"; exit 1; }
    # Refuse to ship a figure whose caption did not render.
    pdftotext "$STAGE/${job}.pdf" - | grep -q "Figure ${n}:" \
        || { echo "ERROR: rendered page lacks 'Figure ${n}:' caption label"; exit 1; }
    # One-time backup of the pre-caption upload file.
    if [[ -f "$OUT/Figure_${n}.pdf" && ! -f "$BACKUP/Figure_${n}.pdf" ]]; then
        cp "$OUT/Figure_${n}.pdf" "$BACKUP/Figure_${n}.pdf"
    fi
    crop_pdf "$STAGE/${job}.pdf" "$OUT/Figure_${n}.pdf"
    echo "  -> $OUT/Figure_${n}.pdf  ($(pdfinfo "$OUT/Figure_${n}.pdf" | awk -F': *' '/Page size/{print $2}'))"
}

build_one 1 figure1
build_one 2 figure2
build_one 3 figure3
build_one 4 figure5

echo
echo "=== done ==="
ls -la "$OUT"/Figure_{1,2,3,4}.pdf
