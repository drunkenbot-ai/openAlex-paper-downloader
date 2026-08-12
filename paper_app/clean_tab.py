"""Clean tab: PDF list, raw preview, and cleaned-text preview side by side."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
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
from paper_app.find_replace_dialog import FindReplaceDialog
from paper_app.pdf_list_panel import PdfListPanel
from paper_app.pdf_preview_panel import PdfPreviewPanel
from paper_cleaner.config import CleanConfig
from paper_cleaner.pipeline import CleanResult


class CleanTab(QWidget):
    """Three-way split: PDF list | raw PDF | cleaned text, plus batch controls."""

    log_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the toolbar and the three-panel splitter.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._clean_config = CleanConfig()
        self._current_pdf_path: Path | None = None
        self._find_replace_dialog: FindReplaceDialog | None = None

        self._output_dir_edit = QLineEdit()
        self._output_dir_edit.setPlaceholderText("Cleaned text output folder…")
        output_browse_button = QPushButton("Browse…")
        output_browse_button.clicked.connect(self._browse_output_dir)
        settings_button = QPushButton("Settings…")
        settings_button.clicked.connect(self._open_settings)
        find_replace_button = QPushButton("Find && Replace…")
        find_replace_button.clicked.connect(self._open_find_replace)
        self.run_button = QPushButton("Start Cleaning (batch)")

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._output_dir_edit)
        toolbar.addWidget(output_browse_button)
        toolbar.addWidget(settings_button)
        toolbar.addWidget(find_replace_button)
        toolbar.addWidget(self.run_button)

        self._list_panel = PdfListPanel()
        self._raw_panel = PdfPreviewPanel()
        self._cleaned_panel = CleanedPreviewPanel()
        self._list_panel.pdf_selected.connect(self._on_pdf_selected)
        self._cleaned_panel.cleaned_ready.connect(self._on_cleaned_ready)

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

    def _open_find_replace(self) -> None:
        """Open the (non-modal) Find & Replace dialog.

        Non-modal so the main window stays interactive — the person can
        click into the cleaned-preview panel, select text, and pull it
        into the dialog's Find field via "Use Selection" while it's open.
        """
        selected_txt_path = None
        if self._current_pdf_path is not None:
            selected_txt_path = self.output_dir() / f"{self._current_pdf_path.stem}.txt"

        dialog = FindReplaceDialog(
            self.output_dir(),
            selected_txt_path,
            get_selected_text=self._cleaned_panel.selected_text,
            log_callback=self.log_message.emit,
            parent=self,
        )
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.finished.connect(lambda _result, path=selected_txt_path: self._on_find_replace_closed(path))
        self._find_replace_dialog = dialog  # keep alive while non-modal and open
        dialog.show()

    def _on_find_replace_closed(self, selected_txt_path: Path | None) -> None:
        """Reload the cleaned preview from disk if it was just edited.

        Args:
            selected_txt_path: The ``.txt`` path Find & Replace targeted
                for "selected document only", if any.
        """
        if selected_txt_path is not None and selected_txt_path.exists():
            self._cleaned_panel.show_saved_text(selected_txt_path)

    def _on_pdf_selected(self, pdf_path: Path) -> None:
        """Refresh both preview panels for the newly selected PDF.

        Args:
            pdf_path: The PDF the user just clicked.
        """
        self._current_pdf_path = pdf_path
        self._raw_panel.show_pdf(pdf_path)
        self._cleaned_panel.show_cleaned(pdf_path, self._clean_config)

    def _on_cleaned_ready(self, pdf_path: Path, result: CleanResult) -> None:
        """Auto-save a valid preview to the output folder.

        Find & Replace operates on saved ``.txt`` files, so a preview
        that never gets batch-cleaned would otherwise have nothing to
        search. Saving valid previews as soon as they're produced keeps
        the output folder in sync with whatever's on screen.

        Args:
            pdf_path: The PDF that was just cleaned.
            result: The cleaning outcome.
        """
        if not result.valid:
            self.log_message.emit(
                f"Preview rejected for {pdf_path.name}: {', '.join(result.reject_reasons)}"
            )
            return

        output_dir = self.output_dir()
        if str(output_dir) in ("", "."):
            return

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{pdf_path.stem}.txt"
            output_path.write_text(result.text, encoding="utf-8")
            self.log_message.emit(
                f"Saved cleaned preview: {output_path.name} ({result.stats.words} words)"
            )
        except OSError as error:
            self.log_message.emit(f"Could not save preview for {pdf_path.name}: {error}")

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
