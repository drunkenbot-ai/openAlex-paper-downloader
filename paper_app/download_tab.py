"""Download tab: exposes every :class:`DownloadConfig` field in the UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from paper_app import settings
from paper_app.downloader.config import DEFAULT_SEARCH_TERMS, DownloadConfig
from paper_app.search_terms_widget import SearchTermsWidget


class DownloadTab(QWidget):
    """Form for configuring and launching a download run."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build every input field, defaulted from :class:`DownloadConfig`.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        defaults = DownloadConfig()

        self.api_key_edit = QLineEdit(settings.load_api_key() or defaults.api_key)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.editingFinished.connect(self._save_api_key)

        self.output_dir_edit = QLineEdit(str(defaults.output_dir))
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._browse_output_dir)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_dir_edit)
        output_row.addWidget(browse_button)

        self.min_year_spin = _spin_box(1900, 2100, defaults.min_year)
        self.min_citations_spin = _spin_box(0, 100_000, defaults.min_citations)
        self.max_papers_per_term_spin = _spin_box(1, 10_000, defaults.max_papers_per_term)
        self.max_downloads_per_day_spin = _spin_box(1, 10_000, defaults.max_downloads_per_day)
        self.download_workers_spin = _spin_box(1, 64, defaults.download_workers)
        self.request_timeout_spin = _spin_box(1, 600, defaults.request_timeout)
        self.max_retries_spin = _spin_box(0, 10, defaults.max_retries)

        self.search_terms_widget = SearchTermsWidget(DEFAULT_SEARCH_TERMS)

        self.run_button = QPushButton("Start Download")

        form = QFormLayout()
        form.addRow("OpenAlex API key", self.api_key_edit)
        form.addRow("Output folder", output_row)
        form.addRow("Minimum year", self.min_year_spin)
        form.addRow("Minimum citations", self.min_citations_spin)
        form.addRow("Max papers per term", self.max_papers_per_term_spin)
        form.addRow("Max downloads per day", self.max_downloads_per_day_spin)
        form.addRow("Download workers", self.download_workers_spin)
        form.addRow("Request timeout (s)", self.request_timeout_spin)
        form.addRow("Max retries", self.max_retries_spin)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.search_terms_widget)
        layout.addWidget(self.run_button)
        self.setLayout(layout)

    def _save_api_key(self) -> None:
        """Persist the current API key field so it is remembered next launch."""
        settings.save_api_key(self.api_key_edit.text().strip())

    def _browse_output_dir(self) -> None:
        """Open a folder picker and fill in the output-directory field."""
        chosen = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if chosen:
            self.output_dir_edit.setText(chosen)

    def build_config(self) -> DownloadConfig:
        """Read every field and build a :class:`DownloadConfig`.

        Returns:
            The configuration to run the downloader with.
        """
        self._save_api_key()
        return DownloadConfig(
            api_key=self.api_key_edit.text().strip(),
            output_dir=Path(self.output_dir_edit.text().strip() or "research-corpus"),
            search_terms=tuple(self.search_terms_widget.selected_terms()),
            min_year=self.min_year_spin.value(),
            min_citations=self.min_citations_spin.value(),
            max_papers_per_term=self.max_papers_per_term_spin.value(),
            max_downloads_per_day=self.max_downloads_per_day_spin.value(),
            download_workers=self.download_workers_spin.value(),
            request_timeout=self.request_timeout_spin.value(),
            max_retries=self.max_retries_spin.value(),
        )


def _spin_box(minimum: int, maximum: int, value: int) -> QSpinBox:
    """Create a QSpinBox with the given range and initial value.

    Args:
        minimum: Lowest selectable value.
        maximum: Highest selectable value.
        value: Initial value.

    Returns:
        The configured spin box.
    """
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    return spin
