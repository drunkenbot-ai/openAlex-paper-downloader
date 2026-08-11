"""Logs tab: a single timestamped, colorized log panel filling the tab."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

_TIMESTAMP_FORMAT = "%d-%m-%y-%H-%M"
_ERROR_KEYWORDS = ("error", "failed", "reject")
_ERROR_COLOR = "#d64545"
_NORMAL_COLOR = "#dddddd"


class LogsTab(QWidget):
    """Read-only log panel that stretches to fill the whole tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the log text area.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self._log = QTextEdit(readOnly=True)
        self._log.setStyleSheet(f"background-color: #1e1e1e; color: {_NORMAL_COLOR};")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._log)
        self.setLayout(layout)

    def clear(self) -> None:
        """Clear all log output."""
        self._log.clear()

    def append_line(self, message: str) -> None:
        """Append one timestamped log line, colored red if it looks like a failure.

        Args:
            message: The log message (without a timestamp).
        """
        timestamp = datetime.now().strftime(_TIMESTAMP_FORMAT)
        color = _ERROR_COLOR if _looks_like_failure(message) else _NORMAL_COLOR
        self._log.append(f'<span style="color:{color}">[{timestamp}] {message}</span>')


def _looks_like_failure(message: str) -> bool:
    """Return True if ``message`` reports an error, rejection, or failure.

    Args:
        message: The log message to inspect.

    Returns:
        True if the message should be rendered in red.
    """
    lower = message.lower()
    return any(keyword in lower for keyword in _ERROR_KEYWORDS)
