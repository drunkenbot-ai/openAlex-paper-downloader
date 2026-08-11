"""Modal dialog exposing every :class:`CleanConfig` field."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
)

from paper_cleaner.config import CleanConfig


class CleanSettingsDialog(QDialog):
    """Small modal form for adjusting cleaning thresholds."""

    def __init__(self, config: CleanConfig, parent=None) -> None:
        """Build the form, pre-filled from the current configuration.

        Args:
            config: The configuration currently in effect.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Cleaning Settings")

        self.min_characters_spin = QSpinBox()
        self.min_characters_spin.setRange(0, 10_000_000)
        self.min_characters_spin.setValue(config.min_characters)

        self.min_words_spin = QSpinBox()
        self.min_words_spin.setRange(0, 1_000_000)
        self.min_words_spin.setValue(config.min_words)

        self.max_garbage_ratio_spin = QDoubleSpinBox()
        self.max_garbage_ratio_spin.setRange(0.0, 1.0)
        self.max_garbage_ratio_spin.setSingleStep(0.01)
        self.max_garbage_ratio_spin.setValue(config.max_garbage_ratio)

        self.repeated_line_ratio_spin = QDoubleSpinBox()
        self.repeated_line_ratio_spin.setRange(0.0, 1.0)
        self.repeated_line_ratio_spin.setSingleStep(0.01)
        self.repeated_line_ratio_spin.setValue(config.repeated_line_ratio)

        self.remove_references_check = QCheckBox("Remove References section")
        self.remove_references_check.setChecked(config.remove_references)

        form = QFormLayout()
        form.addRow("Minimum characters", self.min_characters_spin)
        form.addRow("Minimum words", self.min_words_spin)
        form.addRow("Max garbage ratio", self.max_garbage_ratio_spin)
        form.addRow("Repeated line ratio", self.repeated_line_ratio_spin)
        form.addRow(self.remove_references_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def build_config(self) -> CleanConfig:
        """Read the form and build a :class:`CleanConfig`.

        Returns:
            The configuration reflecting the current form values.
        """
        return CleanConfig(
            min_characters=self.min_characters_spin.value(),
            min_words=self.min_words_spin.value(),
            max_garbage_ratio=self.max_garbage_ratio_spin.value(),
            remove_references=self.remove_references_check.isChecked(),
            repeated_line_ratio=self.repeated_line_ratio_spin.value(),
        )
