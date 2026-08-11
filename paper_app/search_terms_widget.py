"""Checkable list widget for choosing OpenAlex search terms.

Lets the user add new terms at runtime; anything added is persisted via
:mod:`paper_app.settings` so it reappears (checked) on the next launch.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from paper_app import settings

_LIST_MIN_HEIGHT = 260


class SearchTermsWidget(QWidget):
    """A checklist of search terms with add / select-all / select-none."""

    def __init__(self, terms: tuple[str, ...], parent: QWidget | None = None) -> None:
        """Build the checklist, pre-checking every default and saved term.

        Args:
            terms: Built-in default search terms, in display order.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self._list = QListWidget()
        self._list.setMinimumHeight(_LIST_MIN_HEIGHT)
        self._list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        existing = {term.lower() for term in terms}
        for term in terms:
            self._add_item(term)
        for term in settings.load_custom_search_terms():
            if term.lower() not in existing:
                self._add_item(term)
                existing.add(term.lower())

        self._new_term_edit = QLineEdit()
        self._new_term_edit.setPlaceholderText("Add a new search term…")
        self._new_term_edit.returnPressed.connect(self._add_new_term)
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_new_term)

        add_row = QHBoxLayout()
        add_row.addWidget(self._new_term_edit)
        add_row.addWidget(add_button)

        select_all_button = QPushButton("Select All")
        select_none_button = QPushButton("Select None")
        select_all_button.clicked.connect(lambda: self._set_all(True))
        select_none_button.clicked.connect(lambda: self._set_all(False))

        button_row = QHBoxLayout()
        button_row.addWidget(select_all_button)
        button_row.addWidget(select_none_button)

        layout = QVBoxLayout()
        layout.addLayout(add_row)
        layout.addLayout(button_row)
        layout.addWidget(self._list, stretch=1)
        self.setLayout(layout)

    def _add_item(self, term: str, checked: bool = True) -> None:
        """Append one checkable term to the list.

        Args:
            term: Search term text.
            checked: Initial check state.
        """
        item = QListWidgetItem(term)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._list.addItem(item)

    def _add_new_term(self) -> None:
        """Add the typed term to the list (checked) and persist it."""
        term = self._new_term_edit.text().strip()
        if not term:
            return

        existing_terms = {
            self._list.item(row).text().lower() for row in range(self._list.count())
        }
        if term.lower() in existing_terms:
            self._new_term_edit.clear()
            return

        self._add_item(term, checked=True)
        self._new_term_edit.clear()

        custom_terms = settings.load_custom_search_terms()
        custom_terms.append(term)
        settings.save_custom_search_terms(custom_terms)

    def _set_all(self, checked: bool) -> None:
        """Check or uncheck every term in the list.

        Args:
            checked: True to check every item, False to uncheck.
        """
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self._list.count()):
            self._list.item(row).setCheckState(state)

    def selected_terms(self) -> list[str]:
        """Return the search terms currently checked.

        Returns:
            The list of checked term strings, in display order.
        """
        terms = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                terms.append(item.text())
        return terms
