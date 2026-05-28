# Repository Guidelines

## Project Structure & Module Organization
- `lancet_draft.tex` is the main article entry point using the `elsarticle` class; section content is pulled via `\input{sections/...}`. Edit section files rather than the master file when possible.
- `sections/` holds the narrative (`abstract.tex`, `methods.tex`, etc.); `references.bib` stores all citations. Stick to natbib-friendly keys and avoid spaces in BibTeX IDs.
- `figures/` contains publication-ready assets linked by `\graphicspath`; `source/` keeps raw exports. Convert raws to compact PDFs before moving them into `figures/` to keep compile times small.
- The Elsevier class sources live at the repo root (`elsarticle.dtx`, `elsarticle.ins`, `*.bst`), while `doc/` has the official class documentation and a Makefile for regenerating `elsdoc.pdf`.

## Build, Test, and Development Commands
- Compile the manuscript locally:
  ```bash
  pdflatex lancet_draft.tex && bibtex lancet_draft && pdflatex lancet_draft.tex && pdflatex lancet_draft.tex
  ```
  This resolves bibliography, cross-references, and figure links.
- Fast rebuild (if `latexmk` is available): `latexmk -pdf lancet_draft.tex`.
- Regenerate the Elsevier class (rare): `latex elsarticle.ins` to emit `elsarticle.cls`.
- Rebuild the class documentation: `make -C doc all` (requires `makeindex`).

## Coding Style & Naming Conventions
- LaTeX-first workflow: keep prose in `sections/*.tex`; avoid duplicating text in the master file.
- Formatting: use two-space indents inside environments, keep lines under ~100 characters, and prefer `% TODO:` comments over inline notes.
- Figures: reference PDFs placed in `figures/`; follow existing numbering (`figure 1.pdf`, `figure 2.pdf`, …) unless a new naming scheme is agreed upon.
- Citations: maintain Vancouver/numeric style via `\cite`/`\citep`; do not switch to author-year options.

## Testing Guidelines
- A clean build means no `Undefined control sequence`, `Label(s) may have changed`, or missing citation warnings in `lancet_draft.log`.
- Verify bibliography coverage with `bibtex` output and skim the generated PDF for overfull/underfull hboxes, figure placement, and hyperlink targets.
- Before sharing, remove transient artifacts (`*.aux`, `*.log`, `*.out`, `*.bbl` if regenerated) or add them to `.gitignore` if you initialize Git.

## Commit & Pull Request Guidelines
- No Git history is tracked here yet; if you initialize one, use imperative, scoped messages (e.g., `feat: update methods cohort` or `docs: refresh elsarticle class`).
- Keep commits focused (one topic each) and avoid committing build artifacts unless a review requires the latest `lancet_draft.pdf` for context.
- Pull requests should summarize scope, list compile commands run, and mention any figure or bibliography updates. Link related issues or manuscripts when available and attach a fresh PDF snapshot for reviewers.
