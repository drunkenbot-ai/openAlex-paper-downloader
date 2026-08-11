"""Background QThread workers for the download and clean pipelines."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from paper_app.downloader.config import DownloadConfig
from paper_app.downloader.runner import DownloadProgress, run_download
from paper_cleaner.batch import BatchProgress, process_folder
from paper_cleaner.config import CleanConfig


class DownloadWorker(QThread):
    """Runs :func:`run_download` on a background thread."""

    progress = Signal(object)
    finished_all = Signal()

    def __init__(self, config: DownloadConfig) -> None:
        """Store the download configuration to run.

        Args:
            config: Settings gathered from the Download tab.
        """
        super().__init__()
        self._config = config

    def run(self) -> None:
        """Execute the download pass, emitting one signal per update."""
        for update in run_download(self._config):
            self.progress.emit(update)
        self.finished_all.emit()


class CleanWorker(QThread):
    """Runs :func:`process_folder` on a background thread."""

    progress = Signal(object)
    finished_all = Signal()

    def __init__(
        self, input_dir: Path, output_dir: Path, config: CleanConfig
    ) -> None:
        """Store the folders and settings to clean with.

        Args:
            input_dir: Folder containing source PDFs.
            output_dir: Folder cleaned ``.txt`` files are written into.
            config: Cleaning thresholds gathered from the Clean tab.
        """
        super().__init__()
        self._input_dir = input_dir
        self._output_dir = output_dir
        self._config = config

    def run(self) -> None:
        """Execute the cleaning pass, emitting one signal per file."""
        for update in process_folder(self._input_dir, self._output_dir, self._config):
            self.progress.emit(update)
        self.finished_all.emit()


__all__ = ["DownloadWorker", "CleanWorker", "DownloadProgress", "BatchProgress"]
