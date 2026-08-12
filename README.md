# Research Paper Corpus Builder GUI

Single PySide6 app combining OpenAlex download + paper_cleaner cleaning.

## Install
    pip install -r requirements.txt

## Run
    python -m paper_app

## Find & Replace fixes (this version)

Three real bugs, fixed:

1. **Dialog was blocking everything.** It's now opened with `.show()`
   instead of `.exec()`, so it's non-modal — you can click back into the
   main window, select text in the cleaned preview, and keep the dialog
   open at the same time.
2. **Selecting/searching text found nothing.** Two causes:
   - The dialog defaulted to **regex mode**, so plain prose containing
     `.`, `(`, `+`, etc. silently failed to match as literal text. It now
     defaults to **plain-text mode** (regex is still available via the
     "Use regex" checkbox).
   - The target `.txt` file frequently didn't exist yet — the preview
     panel only cleaned text *in memory*, it never wrote it to the output
     folder unless you'd run the full batch "Start Cleaning". **Every
     valid preview is now auto-saved** to the output folder the moment
     it finishes cleaning, so Find & Replace always has something to
     search once you've selected a document. A new **"Use Selection"**
     button also lets you highlight text in the cleaned preview and pull
     it straight into the Find field instead of retyping it.
3. **No visibility in the Logs tab.** Every Find & Replace action
   (preview run, per-file match/replacement counts, errors, final tally)
   now also gets pushed to the app's main Logs tab, prefixed
   `Find & Replace:`, alongside the dialog's own local log.

## Previous features
- Regex/plain-text search & replace across cleaned documents, scoped to
  one document or all of them, with a dry-run preview before saving.
- Cross-platform PyInstaller builds via `.github/workflows/build.yml`
  (Windows/macOS/Linux, auto-attaches to GitHub Releases on version tags).
- Taskbar icon on Windows: AppUserModelID, multi-resolution `.ico`, and a
  direct `WM_SETICON` WinAPI fallback.
- Clean tab: three-way split — PDF list | raw PDF preview | cleaned-text
  preview (background-threaded), with a Settings dialog for cleaning
  thresholds and a batch "Start Cleaning" button.
- Logs tab: full-height, timestamped (`dd-mm-yy-hh-mm`), red-on-failure log lines.
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
- `paper_app/clean_tab.py` — Clean tab: toolbar + 3-panel splitter, owns
  the auto-save-on-valid-preview logic and forwards a `log_message`
  signal up to the main Logs tab.
- `paper_app/pdf_list_panel.py` — left panel (PDF list).
- `paper_app/pdf_preview_panel.py` — middle panel (raw PDF viewer).
- `paper_app/cleaned_preview_panel.py` — right panel (cleaned text
  viewer); emits `cleaned_ready(pdf_path, result)` and exposes
  `selected_text()` for the "Use Selection" button.
- `paper_app/single_clean_worker.py` — background thread for one-PDF preview cleaning.
- `paper_app/clean_settings_dialog.py` — dialog exposing every CleanConfig field.
- `paper_app/text_replace.py` — regex/plain-text find-replace core logic.
- `paper_app/find_replace_worker.py` — background thread for bulk find/replace.
- `paper_app/find_replace_dialog.py` — non-modal Find & Replace dialog UI.
- `paper_app/logs_tab.py` — full-height, timestamped, colorized log panel.
- `paper_app/search_terms_widget.py` — checklist with add / Select All / Select None.
- `paper_app/assets/` — `app_icon.png`, `app_icon.ico`, `app_icon.icns`.
- `paper_app/workers.py`, `main_window.py`, `main.py` — QThread workers,
  the combined window (Download / Clean / Logs tabs), and entry point
  (AppUserModelID + app/window/native icon handling, frozen-path fixes).
- `paper_cleaner/` — unchanged cleaning pipeline package.
- `build.spec` — PyInstaller spec (per-OS icon, includes `paper_app/assets`).
- `.github/workflows/build.yml` — CI build for Windows/macOS/Linux.
