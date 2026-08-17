# Research Paper Corpus Builder GUI

Single PySide6 app combining OpenAlex download + paper_cleaner cleaning.

## Install
    pip install -r requirements.txt

## Run
    python -m paper_app

## Cleaning-pipeline fix: matrix/bracket-extension soup (this update)

The user flagged a worrying passage: a matrix equation from a real
astrophysics paper (Riess et al.-style SN Ia/Cepheid calibration) that
had been flattened into unreadable symbol soup —
`"⎛ ⎝ ⎜ ⎜ ⎜ ... ⎞ ⎠ ⎟ ⎟ ⎟ ... ⎫ ⎬⎭"`.

### Root cause
These are legitimate Unicode "bracket extension piece" characters
(U+239B–U+23B1, Miscellaneous Technical block) that PDF typesetting uses
to draw tall, multi-row parenthesis/bracket/brace delimiters around
matrices and piecewise-function definitions. They only have meaning
given the original 2D layout; once PDF text extraction flattens
everything to linear text, the row/column structure is gone and only
meaningless bracket-piece soup remains. This is the same fundamental
"extraction destroys equation structure" issue documented as a known
limitation earlier, but this specific manifestation is common and
detectable enough to safely fix.

A second, related pattern was also found: some math fonts map the same
kind of bracket/brace pieces into the Private Use Area instead
(`"V (φ) = \uf8f1\uf8f4\uf8f2\uf8f4\uf8f3 V0 ..."`) — same problem,
different codepoint range.

### Fix: character-level removal, not line removal
Critically, these bracket-piece characters are very often merged by
`join_wrapped_lines` onto the *same line* as substantial, legitimate
prose (confirmed in one real example: a full paragraph of real
discussion text ending with a small embedded equation fragment). A
line-level filter would have deleted real content. Instead,
`text_utils.normalize_unicode()` now blanks out just the bracket-piece
characters themselves (à la the existing zero-width-character
handling), leaving everything else on the line untouched. The resulting
extra whitespace is cleaned up automatically by the existing
`normalize_line()` step later in the pipeline; a line that was *purely*
bracket soup collapses to empty and disappears via `collapse_blank_lines`.

**Verified:** tested against the exact flagged passage and 2 other real
mixed prose+equation lines — real content fully preserved, bracket
soup gone. Scanned the entire accumulated 18-file corpus: 9 files were
affected (up to 372 stray characters in one file), all now fully
eliminated (before/after counts confirmed per file). Re-ran the full
`clean_pages()` pipeline end-to-end plus the complete regression suite
for every previous fix (numbered affiliations, citation clusters,
5G/6G false-positive avoidance) — all still passing.

**Still a known, unfixable limitation:** the equation *content* itself
(e.g. "v Y n s c 1 2 1 2 lm l lm l lm I lm 2 1 4 4") remains unreadable
even after this fix, since the subscript/superscript/matrix-position
information was already lost at extraction time — removing the bracket
soup cleans up the visual noise but can't reconstruct the actual math.

## Cleaning-pipeline fixes: two new leaks found (previous update)
1. **Space-separated numbered affiliations** — SDSS-collaboration-style
   ("66 AURA Observatory in Chile, ..."), as opposed to the fused
   LIGO-style format. New `looks_like_indexed_affiliation_line()`,
   gated on a genuine institution keyword to avoid catching numbered
   section headings, footnotes, and equations that share the same
   "digit + capital letter" shape.
2. **Stray C0 control-byte characters** (`\x00`-`\x15`) embedded in
   equations from another PDF math-font encoding quirk — stripped in
   `normalize_unicode()`.

Investigated but left alone: a dense GW-detection statistics table
flattened into number-soup — real data, not a PDF artifact;
`is_pdf_artifact()` is deliberately metric-only to avoid destroying
legitimate numeric content.

## Previous fix: numbered-affiliation filter was over-triggering
A prior version had a 178-false-positive regression (ordinary
"5G"/"6G"/"2D" prose misclassified as affiliation noise). Fixed by
requiring 3+ letters after the digit in the fused pattern.

## Cleaning-pipeline fix: citation-cluster table remnants
`is_citation_cluster()` strips flattened table cells like
`"[8], [9], [15], ..."` while leaving real inline citations like
`"SGD [181] and Adam [182]..."` untouched.

## CI workflow fixes
Bumped actions to Node-24-native majors. Release tags must start with
`v` (e.g. `v1.0.0`) to match the workflow's `refs/tags/v*` condition.

## Cleaning-pipeline fixes (earlier updates)
1. Stray page numbers glued onto paragraphs — now stripped.
2. CRLF instead of LF in every output file — fixed with `newline="\n"`.

## Find & Replace fixes
Non-modal dialog, plain-text default search, "Use Selection" button,
every valid preview auto-saves, all actions log to the main Logs tab.

## Previous features
- Regex/plain-text search & replace across cleaned documents.
- Cross-platform PyInstaller builds via `.github/workflows/build.yml`,
  auto-attaches to GitHub Releases on version tags.
- Taskbar icon on Windows: AppUserModelID, multi-resolution `.ico`, and a
  direct `WM_SETICON` WinAPI fallback.
- Clean tab: three-way split — PDF list | raw PDF preview | cleaned-text
  preview, with a Settings dialog and a batch "Start Cleaning" button.
- Logs tab: full-height, timestamped (`dd-mm-yy-hh-mm`), red-on-failure log lines.
- Search terms: add new ones permanently (persisted via QSettings).
- API key remembered across launches.

Settings are stored via `QSettings("DrunkenBot", "PaperCorpusBuilder")`.

## Layout
- `paper_cleaner/` — cleaning pipeline. `text_utils.py`:
  `normalize_unicode()` now strips both Miscellaneous-Technical-block
  and PUA-range bracket/brace-extension pieces, plus C0 control chars,
  and writes with `newline="\n"`. `line_filters.py`:
  `looks_like_numbered_affiliation_line()` (fused format),
  `looks_like_indexed_affiliation_line()` (space-separated format),
  `is_citation_cluster()`; `body_cleanup.py` strips all of these plus
  bare page numbers.
- `paper_app/` — the GUI (downloader, Clean tab 3-panel splitter, Find &
  Replace, Logs tab, settings persistence, icon/taskbar handling).
- `build.spec`, `.github/workflows/build.yml` — cross-platform PyInstaller CI.
