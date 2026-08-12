"""Main application window combining the Download, Clean, and Logs tabs."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QProgressBar, QTabWidget, QVBoxLayout, QWidget

from paper_app.clean_tab import CleanTab
from paper_app.download_tab import DownloadTab
from paper_app.logs_tab import LogsTab
from paper_app.workers import BatchProgress, CleanWorker, DownloadProgress, DownloadWorker


class MainWindow(QMainWindow):
    """Window with Download / Clean / Logs tabs and a shared progress bar."""

    def __init__(self) -> None:
        """Build the tabs, progress bar, and wire up the run buttons."""
        super().__init__()
        self.setWindowTitle("Research Paper Corpus Builder")
        self.resize(760, 640)

        self._download_tab = DownloadTab()
        self._clean_tab = CleanTab()
        self._logs_tab = LogsTab()
        self._download_worker: DownloadWorker | None = None
        self._clean_worker: CleanWorker | None = None

        self._tabs = QTabWidget()
        self._tabs.addTab(self._download_tab, "Download")
        self._tabs.addTab(self._clean_tab, "Clean")
        self._tabs.addTab(self._logs_tab, "Logs")

        self._progress_bar = QProgressBar()

        layout = QVBoxLayout()
        layout.addWidget(self._tabs, stretch=1)
        layout.addWidget(self._progress_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._download_tab.run_button.clicked.connect(self._start_download)
        self._clean_tab.run_button.clicked.connect(self._start_clean)
        self._clean_tab.log_message.connect(self._log_line)

    def _log_line(self, text: str) -> None:
        """Append one timestamped line to the Logs tab.

        Args:
            text: Line of text to append.
        """
        self._logs_tab.append_line(text)

    def _set_run_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable both run buttons while a job is active.

        Args:
            enabled: True to re-enable both buttons.
        """
        self._download_tab.run_button.setEnabled(enabled)
        self._clean_tab.run_button.setEnabled(enabled)

    def _start_download(self) -> None:
        """Validate the download form and launch the download worker."""
        config = self._download_tab.build_config()
        if not config.search_terms:
            self._log_line("Select at least one search term first.")
            return

        self._logs_tab.clear()
        self._tabs.setCurrentWidget(self._logs_tab)
        self._progress_bar.setRange(0, 0)
        self._set_run_buttons_enabled(False)

        self._download_worker = DownloadWorker(config)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished_all.connect(self._on_job_finished)
        self._download_worker.start()

    def _on_download_progress(self, update: DownloadProgress) -> None:
        """Log a download-progress update and advance the progress bar.

        Args:
            update: The latest progress emitted by the download worker.
        """
        if update.total:
            self._progress_bar.setRange(0, update.total)
            self._progress_bar.setValue(update.index)
        self._log_line(update.message)

    def _start_clean(self) -> None:
        """Validate the clean form and launch the clean worker."""
        input_dir = self._clean_tab.input_dir()
        if not input_dir.is_dir():
            self._log_line(f"Not a folder: {input_dir}")
            return

        output_dir = self._clean_tab.output_dir()
        if str(output_dir) in ("", "."):
            output_dir = input_dir / "cleaned_text"
        config = self._clean_tab.build_config()

        self._logs_tab.clear()
        self._tabs.setCurrentWidget(self._logs_tab)
        self._progress_bar.setRange(0, 0)
        self._set_run_buttons_enabled(False)

        self._clean_worker = CleanWorker(input_dir, output_dir, config)
        self._clean_worker.progress.connect(self._on_clean_progress)
        self._clean_worker.finished_all.connect(self._on_job_finished)
        self._clean_worker.start()

    def _on_clean_progress(self, update: BatchProgress) -> None:
        """Log a cleaning-progress update and advance the progress bar.

        Args:
            update: The latest progress emitted by the clean worker.
        """
        self._progress_bar.setRange(0, update.total)
        self._progress_bar.setValue(update.index)

        if update.error:
            self._log_line(f"ERROR  {update.pdf_path.name}: {update.error}")
        elif update.result and update.result.valid:
            words = update.result.stats.words
            self._log_line(f"OK     {update.pdf_path.name} ({words} words)")
        else:
            reasons = ", ".join(update.result.reject_reasons) if update.result else "?"
            self._log_line(f"REJECT {update.pdf_path.name}: {reasons}")

    def _on_job_finished(self) -> None:
        """Re-enable the run buttons once the active job completes."""
        self._log_line("Done.")
        self._set_run_buttons_enabled(True)
