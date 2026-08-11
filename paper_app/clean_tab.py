"""Clean tab: PDF list, raw preview, and cleaned-text preview side by side."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from paper_app.clean_settings_dialog import CleanSettingsDialog
from paper_app.cleaned_preview_panel import CleanedPreviewPanel
from paper_app.pdf_list_panel import PdfListPanel
from paper_app.pdf_preview_panel import PdfPreviewPanel
from paper_cleaner.config import CleanConfig


class CleanTab(QWidget):
    """Three-way split: PDF list | raw PDF | cleaned text, plus batch controls."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the toolbar and the three-panel splitter.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._clean_config = CleanConfig()

        self._output_dir_edit = QLineEdit()
        self._output_dir_edit.setPlaceholderText("Cleaned text output folder…")
        output_browse_button = QPushButton("Browse…")
        output_browse_button.clicked.connect(self._browse_output_dir)
        settings_button = QPushButton("Settings…")
        settings_button.clicked.connect(self._open_settings)
        self.run_button = QPushButton("Start Cleaning (batch)")

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._output_dir_edit)
        toolbar.addWidget(output_browse_button)
        toolbar.addWidget(settings_button)
        toolbar.addWidget(self.run_button)

        self._list_panel = PdfListPanel()
        self._raw_panel = PdfPreviewPanel()
        self._cleaned_panel = CleanedPreviewPanel()
        self._list_panel.pdf_selected.connect(self._on_pdf_selected)

        splitter = QSplitter()
        splitter.addWidget(self._list_panel)
        splitter.addWidget(self._raw_panel)
        splitter.addWidget(self._cleaned_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)

        layout = QVBoxLayout()
        layout.addLayout(toolbar)
        layout.addWidget(splitter, stretch=1)
        self.setLayout(layout)

    def _browse_output_dir(self) -> None:
        """Open a folder picker and fill in the output-directory field."""
        chosen = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if chosen:
            self._output_dir_edit.setText(chosen)

    def _open_settings(self) -> None:
        """Open the cleaning-thresholds dialog and store the result."""
        dialog = CleanSettingsDialog(self._clean_config, self)
        if dialog.exec():
            self._clean_config = dialog.build_config()

    def _on_pdf_selected(self, pdf_path: Path) -> None:
        """Refresh both preview panels for the newly selected PDF.

        Args:
            pdf_path: The PDF the user just clicked.
        """
        self._raw_panel.show_pdf(pdf_path)
        self._cleaned_panel.show_cleaned(pdf_path, self._clean_config)

    def input_dir(self) -> Path:
        """Return the configured PDF input folder."""
        return self._list_panel.folder()

    def output_dir(self) -> Path:
        """Return the configured cleaned-text output folder."""
        return Path(self._output_dir_edit.text().strip())

    def build_config(self) -> CleanConfig:
        """Return the currently configured cleaning thresholds.

        Returns:
            The :class:`CleanConfig` last set via the Settings dialog.
        """
        return self._clean_config

    def set_input_dir(self, folder: Path) -> None:
        """Point the PDF list panel at ``folder`` and reload it.

        Args:
            folder: Folder to list ``*.pdf`` files from.
        """
        self._list_panel.set_folder(folder)
