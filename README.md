# Research Paper Corpus Builder GUI

Single PySide6 app combining OpenAlex download + paper_cleaner cleaning.

## Install
    pip install pymupdf PySide6 requests Pillow

## Run
    cd paper_app_project
    python -m paper_app

## What's new in this version

### Taskbar icon (Windows), take two
AUMID was already being set (confirmed) — the extra fix here is that
Windows' taskbar needs an .ico with several embedded resolutions to
render reliably; a single-res PNG often shows blank there even though
it's fine in the title bar. On top of that, `main.py` now also sends
`WM_SETICON` directly to the native window handle via `ctypes` right
after `show()`, as a stronger fallback in case Qt's own icon
propagation doesn't take on a given Windows setup. If it's *still* not
showing after this, the only 100%-guaranteed route left is packaging
with PyInstaller (`--icon app_icon.ico`), since a bundled `.exe` carries
its icon natively — happy to set that up if needed.

### Clean tab redesign — three panels
The Clean tab is now a three-way split (`QSplitter`):
- **Left** (`pdf_list_panel.py`) — pick a folder, see every `*.pdf` in it.
- **Middle** (`pdf_preview_panel.py`) — renders the raw PDF via `QtPdf`/`QtPdfWidgets`.
- **Right** (`cleaned_preview_panel.py`) — runs the cleaning pipeline on
  the selected PDF in a background thread (`single_clean_worker.py`) and
  shows the cleaned text, word/garbage stats, and pass/reject verdict.

Selecting a PDF on the left instantly refreshes both preview panels.
Cleaning thresholds (min chars/words, garbage ratio, etc.) moved into a
"Settings…" dialog (`clean_settings_dialog.py`) to keep the three panels
front and center; a "Start Cleaning (batch)" button still runs the full
folder through the same pipeline as before.

## Previous features
- Logs tab with full-height, timestamped (`dd-mm-yy-hh-mm`), red-on-failure log lines.
- Search terms: add new ones permanently (persisted via QSettings, checked on load).
- API key remembered across launches.

Settings are stored via `QSettings("DrunkenBot", "PaperCorpusBuilder")`,
which resolves to the Windows registry, a macOS plist, or an INI file
under `~/.config` on Linux — no extra setup needed on any platform.

## Layout
- `paper_app/downloader/` — download config, OpenAlex client,
  metadata/license/filter logic, per-paper download logic, state/JSONL
  persistence, and the `run_download()` orchestrator.
- `paper_app/settings.py` — QSettings-backed persistence (API key, custom search terms).
- `paper_app/download_tab.py` — Download tab UI.
- `paper_app/clean_tab.py` — Clean tab: toolbar + 3-panel splitter.
- `paper_app/pdf_list_panel.py` — left panel (PDF list).
- `paper_app/pdf_preview_panel.py` — middle panel (raw PDF viewer).
- `paper_app/cleaned_preview_panel.py` — right panel (cleaned text viewer).
- `paper_app/single_clean_worker.py` — background thread for one-PDF preview cleaning.
- `paper_app/clean_settings_dialog.py` — dialog exposing every CleanConfig field.
- `paper_app/logs_tab.py` — full-height, timestamped, colorized log panel.
- `paper_app/search_terms_widget.py` — checklist with add / Select All / Select None.
- `paper_app/assets/app_icon.png`, `app_icon.ico` — the DrunkenBot app icon.
- `paper_app/workers.py`, `main_window.py`, `main.py` — QThread workers,
  the combined window (Download / Clean / Logs tabs), and entry point
  (AppUserModelID + app/window/native icon handling).
- `paper_cleaner/` — unchanged cleaning pipeline package.
