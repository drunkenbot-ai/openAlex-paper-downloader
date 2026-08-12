# Research Paper Corpus Builder GUI

Single PySide6 app combining OpenAlex download + paper_cleaner cleaning.

## Install
    pip install -r requirements.txt

## Run
    python -m paper_app

## Cleaning-pipeline fix: citation-cluster table remnants (this update)

Reviewed 6 more real cleaned `.txt` samples and found lines like:
```
[8], [9], [15], [21], [31], [32], [34], [35] , [22], [26], [62], [63], ...
```
These are the "Related work"/"Refs" column of a table (e.g. a survey
paper's "summary of attention categories" table), which PDF text
extraction flattens into a standalone line with no surrounding prose —
since text extraction has no concept of table cells or columns.

New `line_filters.is_citation_cluster()` detects lines dominated by
`[n]`-style citation markers: it strips every marker out and checks
whether anything meaningful is left. A real sentence like
`"SGD [181] and Adam [182] are well-suited for optimizing..."` still has
plenty of prose left after that strip and is correctly left alone;
`"[8], [9], [15], ..."` with nothing else does not, and gets dropped.
Verified against 8 real/synthetic cases (4 should-strip, 4 should-keep)
and a full `remove_noise_lines` run confirming the surrounding real
table-row descriptions (which *are* legitimate sentences) survive intact.

## CI workflow fixes (previous update)
- `actions/checkout@v4` → `@v5`, `actions/setup-python@v5` → `@v6`,
  `actions/upload-artifact@v4` → `@v6`, `actions/download-artifact@v4` → `@v7`
  (all now Node-24-native, clearing the deprecation warnings).
- "Attach builds to GitHub Release" only runs on version tags
  (`refs/tags/v*`) — showing as skipped on a plain push to `main` is
  expected, not a bug.

## Cleaning-pipeline fixes (previous update)
1. **Stray page numbers glued onto paragraphs** — `body_cleanup` now
   actually drops lines matching `is_page_number()` instead of only
   excluding them from header/footer repetition counting.
2. **Huge numbered-affiliation blocks** (LIGO/Virgo-style, e.g.
   `"13Nikhef, ... 14LIGO, ..."`) — new
   `looks_like_numbered_affiliation_line()` catches the fused-token
   pattern before `join_wrapped_lines` can merge survivors into one
   giant paragraph.
3. **CRLF instead of LF** in every output file — every write site now
   passes `newline="\n"`.

**Known, not fixed:** corrupted math/symbol glyphs from the original
PDF's equation font encoding — extraction-time information loss, not
safely repairable via text filters.

## Find & Replace fixes (previous update)
1. Dialog is non-modal (`.show()` not `.exec()`).
2. Defaults to plain-text search; "Use Selection" button added.
3. Every valid preview auto-saves to the output folder; all actions log
   to the main Logs tab.

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
- `paper_cleaner/` — cleaning pipeline. `line_filters.py` now includes
  `is_citation_cluster()` alongside `looks_like_numbered_affiliation_line()`;
  `body_cleanup.py` strips both, plus bare page numbers; `pipeline.py`
  writes with `newline="\n"`.
- `paper_app/` — the GUI (downloader, Clean tab 3-panel splitter, Find &
  Replace, Logs tab, settings persistence, icon/taskbar handling).
- `build.spec`, `.github/workflows/build.yml` — cross-platform PyInstaller CI.
