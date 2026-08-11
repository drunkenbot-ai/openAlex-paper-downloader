"""Middle panel: renders the raw, un-cleaned PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PdfPreviewPanel(QWidget):
    """Displays one PDF at a time via :class:`QPdfView`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the PDF viewer and its status label.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self._document = QPdfDocument(self)
        self._view = QPdfView()
        self._view.setDocument(self._document)
        self._view.setPageMode(QPdfView.PageMode.MultiPage)
        self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

        self._status_label = QLabel("Select a PDF from the list.")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._status_label)
        layout.addWidget(self._view, stretch=1)
        self.setLayout(layout)

    def show_pdf(self, pdf_path: Path) -> None:
        """Load and render ``pdf_path``.

        Args:
            pdf_path: PDF file to display.
        """
        status = self._document.load(str(pdf_path))
        if status != QPdfDocument.Error.None_:
            self._status_label.setText(f"Could not open {pdf_path.name}: {status.name}")
            return
        self._status_label.setText(f"{pdf_path.name} ({self._document.pageCount()} pages)")
