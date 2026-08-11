"""Right panel: shows the cleaned-text version of the selected PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from paper_app.single_clean_worker import SingleCleanWorker
from paper_cleaner.config import CleanConfig
from paper_cleaner.pipeline import CleanResult


class CleanedPreviewPanel(QWidget):
    """Runs the cleaning pipeline on the selected PDF and shows the result."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the status label and the read-only cleaned-text view.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self._status_label = QLabel("Select a PDF to see its cleaned text.")
        self._text = QTextEdit(readOnly=True)
        self._worker: SingleCleanWorker | None = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._status_label)
        layout.addWidget(self._text, stretch=1)
        self.setLayout(layout)

    def show_cleaned(self, pdf_path: Path, config: CleanConfig) -> None:
        """Clean ``pdf_path`` on a background thread and display the result.

        Args:
            pdf_path: Source PDF to clean.
            config: Cleaning thresholds and options to use.
        """
        self._text.clear()
        self._status_label.setText(f"Cleaning {pdf_path.name}…")

        self._worker = SingleCleanWorker(pdf_path, config)
        self._worker.finished_clean.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_finished(self, result: CleanResult) -> None:
        """Render a completed :class:`CleanResult`.

        Args:
            result: Output of the cleaning pipeline for the selected PDF.
        """
        stats = result.stats
        verdict = "PASSES quality checks" if result.valid else "REJECTED"
        reasons = f" ({', '.join(result.reject_reasons)})" if result.reject_reasons else ""
        self._status_label.setText(
            f"{verdict}{reasons} — {stats.words} words, "
            f"{stats.garbage_ratio:.1%} garbage ratio"
        )
        self._text.setPlainText(result.text or "(document rejected; no cleaned text)")

    def _on_failed(self, error: str) -> None:
        """Show an error message if extraction/cleaning raised.

        Args:
            error: The exception message from the worker thread.
        """
        self._status_label.setText(f"Failed to clean: {error}")
