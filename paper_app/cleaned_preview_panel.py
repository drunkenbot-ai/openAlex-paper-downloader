"""Right panel: shows the cleaned-text version of the selected PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from paper_app.single_clean_worker import SingleCleanWorker
from paper_cleaner.config import CleanConfig
from paper_cleaner.pipeline import CleanResult


class CleanedPreviewPanel(QWidget):
    """Runs the cleaning pipeline on the selected PDF and shows the result."""

    cleaned_ready = Signal(Path, object)  # source pdf path, CleanResult

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
        # Bind pdf_path as a default argument so a late-arriving signal
        # from a superseded request can't report against the wrong file.
        self._worker.finished_clean.connect(
            lambda result, path=pdf_path: self._on_finished(result, path)
        )
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def show_saved_text(self, path: Path) -> None:
        """Load and display an already-cleaned ``.txt`` file directly.

        Used to reflect on-disk edits (e.g. from Find & Replace) without
        re-running the cleaning pipeline.

        Args:
            path: Cleaned ``.txt`` file to display.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as error:  # noqa: BLE001 - shown to the user
            self._status_label.setText(f"Could not reload {path.name}: {error}")
            return
        self._status_label.setText(f"Showing saved file: {path.name}")
        self._text.setPlainText(text)

    def selected_text(self) -> str:
        """Return the text currently highlighted in the cleaned preview.

        Returns:
            The selection with paragraph separators normalized to ``\\n``,
            or "" if nothing is selected.
        """
        return self._text.textCursor().selectedText().replace("\u2029", "\n")

    def _on_finished(self, result: CleanResult, pdf_path: Path) -> None:
        """Render a completed :class:`CleanResult` and notify listeners.

        Args:
            result: Output of the cleaning pipeline for ``pdf_path``.
            pdf_path: The PDF this result belongs to.
        """
        stats = result.stats
        verdict = "PASSES quality checks" if result.valid else "REJECTED"
        reasons = f" ({', '.join(result.reject_reasons)})" if result.reject_reasons else ""
        self._status_label.setText(
            f"{verdict}{reasons} — {stats.words} words, "
            f"{stats.garbage_ratio:.1%} garbage ratio"
        )
        self._text.setPlainText(result.text or "(document rejected; no cleaned text)")
        self.cleaned_ready.emit(pdf_path, result)

    def _on_failed(self, error: str) -> None:
        """Show an error message if extraction/cleaning raised.

        Args:
            error: The exception message from the worker thread.
        """
        self._status_label.setText(f"Failed to clean: {error}")
