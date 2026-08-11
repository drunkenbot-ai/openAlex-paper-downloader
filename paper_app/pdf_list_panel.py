"""Left panel: pick a folder and list the PDFs found in it."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_PATH_ROLE = Qt.ItemDataRole.UserRole


class PdfListPanel(QWidget):
    """Shows every ``*.pdf`` in a chosen folder; emits the selected path."""

    pdf_selected = Signal(Path)
    folder_changed = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the folder picker and the PDF list.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("PDF folder…")
        self._folder_edit.editingFinished.connect(self._on_folder_edited)
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._browse_folder)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self._folder_edit)
        folder_row.addWidget(browse_button)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)

        layout = QVBoxLayout()
        layout.addLayout(folder_row)
        layout.addWidget(refresh_button)
        layout.addWidget(self._list, stretch=1)
        self.setLayout(layout)

    def set_folder(self, folder: Path) -> None:
        """Point the panel at a new folder and reload its PDF list.

        Args:
            folder: Folder to list ``*.pdf`` files from.
        """
        self._folder_edit.setText(str(folder))
        self.refresh()

    def folder(self) -> Path:
        """Return the currently configured folder."""
        return Path(self._folder_edit.text().strip())

    def refresh(self) -> None:
        """Reload the PDF list from the current folder."""
        self._list.clear()
        folder = self.folder()
        if not folder.is_dir():
            return
        for pdf_path in sorted(folder.glob("*.pdf")):
            item = QListWidgetItem(pdf_path.name)
            item.setData(_PATH_ROLE, str(pdf_path))
            self._list.addItem(item)

    def _browse_folder(self) -> None:
        """Open a folder picker and load PDFs from the chosen folder."""
        chosen = QFileDialog.getExistingDirectory(self, "Select PDF Folder")
        if chosen:
            self.set_folder(Path(chosen))
            self.folder_changed.emit(Path(chosen))

    def _on_folder_edited(self) -> None:
        """Reload the list after the folder path is typed manually."""
        self.refresh()
        self.folder_changed.emit(self.folder())

    def _on_selection_changed(self, current: QListWidgetItem | None) -> None:
        """Emit :attr:`pdf_selected` for the newly highlighted PDF.

        Args:
            current: The newly selected list item, or None if cleared.
        """
        if current is None:
            return
        self.pdf_selected.emit(Path(current.data(_PATH_ROLE)))



