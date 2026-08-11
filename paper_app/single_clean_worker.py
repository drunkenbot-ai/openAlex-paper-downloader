"""Background worker that runs the clean pipeline on a single PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from paper_cleaner.config import CleanConfig
from paper_cleaner.pdf_extract import extract_pdf_pages
from paper_cleaner.pipeline import CleanResult, clean_pages


class SingleCleanWorker(QThread):
    """Extracts and cleans one PDF on a background thread."""

    finished_clean = Signal(object)  # CleanResult
    failed = Signal(str)

    def __init__(self, pdf_path: Path, config: CleanConfig) -> None:
        """Store the PDF and cleaning settings to run.

        Args:
            pdf_path: Source PDF to clean.
            config: Cleaning thresholds and options.
        """
        super().__init__()
        self._pdf_path = pdf_path
        self._config = config

    def run(self) -> None:
        """Extract, clean, and emit the resulting :class:`CleanResult`."""
        try:
            pages = extract_pdf_pages(self._pdf_path)
            result: CleanResult = clean_pages(pages, self._config)
            self.finished_clean.emit(result)
        except Exception as error:  # noqa: BLE001 - surfaced to the UI
            self.failed.emit(str(error))
