"""Find & Replace dialog for cleaned ``.txt`` documents (supports regex).

Non-modal by design: it's opened with ``show()`` rather than ``exec()``
so the person can still click into the main window and select text
while the dialog stays open.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from paper_app.find_replace_worker import FindReplaceWorker
from paper_app.text_replace import compile_pattern


class FindReplaceDialog(QDialog):
    """Search and replace (plain text or regex) across cleaned documents."""

    def __init__(
        self,
        output_dir: Path,
        selected_txt_path: Path | None,
        get_selected_text: Callable[[], str] | None = None,
        log_callback: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Build the form, defaulted to the currently selected document.

        Args:
            output_dir: Folder containing cleaned ``.txt`` files.
            selected_txt_path: Cleaned ``.txt`` path for the PDF currently
                selected in the Clean tab, if any.
            get_selected_text: Callable returning the text currently
                highlighted in the cleaned-preview panel, used by the
                "Use Selection" button.
            log_callback: Called with each status line so the app's main
                Logs tab can mirror what this dialog is doing.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Find & Replace")
        self.resize(560, 460)

        self._output_dir = output_dir
        self._selected_txt_path = selected_txt_path
        self._get_selected_text = get_selected_text
        self._log_callback = log_callback
        self._worker: FindReplaceWorker | None = None

        self.find_edit = QLineEdit()
        use_selection_button = QPushButton("Use Selection")
        use_selection_button.setToolTip(
            "Copy the text highlighted in the cleaned preview into Find"
        )
        use_selection_button.clicked.connect(self._use_selected_text)
        find_row = QHBoxLayout()
        find_row.addWidget(self.find_edit)
        find_row.addWidget(use_selection_button)

        self.replace_edit = QLineEdit()

        # Plain-text search is the safer default: regex-special characters
        # like ".", "(", "+" in ordinary prose otherwise cause searches
        # that look correct but silently match nothing (or too much).
        self.regex_check = QCheckBox("Use regex")
        self.regex_check.setChecked(False)
        self.case_check = QCheckBox("Case sensitive")

        self.scope_selected_radio = QRadioButton()
        self.scope_all_radio = QRadioButton("All cleaned documents in output folder")
        scope_group = QButtonGroup(self)
        scope_group.addButton(self.scope_selected_radio)
        scope_group.addButton(self.scope_all_radio)

        if selected_txt_path is not None:
            self.scope_selected_radio.setText(
                f"Selected document only ({selected_txt_path.name})"
            )
            self.scope_selected_radio.setChecked(True)
        else:
            self.scope_selected_radio.setText("Selected document only (none selected)")
            self.scope_selected_radio.setEnabled(False)
            self.scope_all_radio.setChecked(True)

        self.preview_button = QPushButton("Preview Matches")
        self.preview_button.clicked.connect(self._preview)
        self.replace_button = QPushButton("Replace && Save")
        self.replace_button.clicked.connect(self._replace_and_save)

        self.status_label = QLabel("Nothing replaced yet.")
        self.log = QTextEdit(readOnly=True)

        form = QFormLayout()
        form.addRow("Find", find_row)
        form.addRow("Replace with", self.replace_edit)
        form.addRow(self.regex_check)
        form.addRow(self.case_check)
        form.addRow(self.scope_selected_radio)
        form.addRow(self.scope_all_radio)

        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(
            self.accept
        )

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.preview_button)
        layout.addWidget(self.replace_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log, stretch=1)
        layout.addWidget(close_buttons)
        self.setLayout(layout)

    def _log(self, text: str) -> None:
        """Append one line to this dialog's log and mirror it upstream.

        Args:
            text: Message to record.
        """
        self.log.append(text)
        if self._log_callback is not None:
            self._log_callback(f"Find & Replace: {text}")

    def _use_selected_text(self) -> None:
        """Copy the cleaned-preview text selection into the Find field."""
        if self._get_selected_text is None:
            return
        selected = self._get_selected_text()
        if not selected:
            self.status_label.setText(
                "No text is selected in the cleaned preview panel."
            )
            return
        self.find_edit.setText(selected)

    def _target_files(self) -> list[Path]:
        """Return the ``.txt`` files this dialog's current scope covers.

        Returns:
            The list of cleaned text files to search or replace in.
        """
        if self.scope_selected_radio.isChecked() and self._selected_txt_path is not None:
            return [self._selected_txt_path] if self._selected_txt_path.exists() else []
        if not self._output_dir.is_dir():
            return []
        return sorted(self._output_dir.glob("*.txt"))

    def _explain_missing_files(self) -> str:
        """Return a helpful message for why no target files were found.

        Returns:
            A message pointing at the likely cause (usually that the
            selected document hasn't been saved to the output folder yet).
        """
        if self.scope_selected_radio.isChecked() and self._selected_txt_path is not None:
            return (
                f"{self._selected_txt_path.name} isn't in the output folder yet — "
                "select it in the PDF list (a valid preview auto-saves it) or "
                "run 'Start Cleaning (batch)' first."
            )
        return f"No .txt files found in {self._output_dir}."

    def _preview(self) -> None:
        """Count matches per target file without modifying anything."""
        find_text = self.find_edit.text()
        if not find_text:
            self.status_label.setText("Enter a find pattern first.")
            return
        try:
            compiled = compile_pattern(
                find_text, self.regex_check.isChecked(), self.case_check.isChecked()
            )
        except Exception as error:  # noqa: BLE001 - shown to the user
            self.status_label.setText(f"Invalid pattern: {error}")
            self._log(f"Invalid pattern '{find_text}': {error}")
            return

        files = self._target_files()
        if not files:
            message = self._explain_missing_files()
            self.status_label.setText(message)
            self._log(message)
            return

        self.log.clear()
        total = 0
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except Exception as error:  # noqa: BLE001 - shown to the user
                self._log(f"{path.name}: read error ({error})")
                continue
            count = len(compiled.findall(text))
            if count:
                self._log(f"{path.name}: {count} match(es)")
            total += count

        summary = f"{total} total match(es) across {len(files)} file(s). Nothing saved yet."
        self.status_label.setText(summary)
        self._log(f"Preview '{find_text}': {summary}")

    def _replace_and_save(self) -> None:
        """Run the replacement on a background thread and save each file."""
        find_text = self.find_edit.text()
        if not find_text:
            self.status_label.setText("Enter a find pattern first.")
            return
        files = self._target_files()
        if not files:
            message = self._explain_missing_files()
            self.status_label.setText(message)
            self._log(message)
            return

        self.log.clear()
        self.status_label.setText("Replacing…")
        self._log(f"Starting replace '{find_text}' -> '{self.replace_edit.text()}' "
                   f"across {len(files)} file(s)")
        self.replace_button.setEnabled(False)
        self.preview_button.setEnabled(False)

        self._worker = FindReplaceWorker(
            files,
            find_text,
            self.replace_edit.text(),
            self.regex_check.isChecked(),
            self.case_check.isChecked(),
        )
        self._worker.file_done.connect(self._on_file_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished_all.connect(self._on_finished_all)
        self._worker.start()

    def _on_file_done(self, filename: str, count: int) -> None:
        """Log one processed file's replacement count.

        Args:
            filename: Name of the file that was processed.
            count: Number of replacements made in that file.
        """
        if count:
            self._log(f"Saved {filename}: {count} replacement(s)")

    def _on_failed(self, filename: str, error: str) -> None:
        """Log a failure for one file, or for the overall pattern.

        Args:
            filename: Name of the file that failed, or "" for a
                pattern-compile failure.
            error: The error message.
        """
        self._log(f"ERROR {filename or 'pattern'}: {error}")

    def _on_finished_all(self, files_changed: int, total_replacements: int) -> None:
        """Report the final tally and re-enable the action buttons.

        Args:
            files_changed: Number of files that had at least one replacement.
            total_replacements: Total replacements made across all files.
        """
        summary = (
            f"Done. {total_replacements} replacement(s) saved across "
            f"{files_changed} file(s)."
        )
        self.status_label.setText(summary)
        self._log(summary)
        self.replace_button.setEnabled(True)
        self.preview_button.setEnabled(True)
