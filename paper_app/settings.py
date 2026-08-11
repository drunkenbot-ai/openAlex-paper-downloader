"""Persistent app settings: OpenAlex API key and custom search terms.

Backed by :class:`QSettings`, which stores data in the platform-native
location (Windows registry, macOS plist, or a Linux config file), so
values survive across app restarts with no extra setup.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

ORGANIZATION_NAME = "DrunkenBot"
APPLICATION_NAME = "PaperCorpusBuilder"

_API_KEY_SETTING = "openalex/api_key"
_CUSTOM_TERMS_SETTING = "search/custom_terms"


def _settings() -> QSettings:
    """Return the shared :class:`QSettings` instance for this app."""
    return QSettings(ORGANIZATION_NAME, APPLICATION_NAME)


def load_api_key() -> str:
    """Return the previously saved OpenAlex API key, or "" if none."""
    return str(_settings().value(_API_KEY_SETTING, ""))


def save_api_key(api_key: str) -> None:
    """Persist the OpenAlex API key for future runs.

    Args:
        api_key: The key to remember.
    """
    _settings().setValue(_API_KEY_SETTING, api_key)


def load_custom_search_terms() -> list[str]:
    """Return search terms the user has added, in the order they were added."""
    stored = _settings().value(_CUSTOM_TERMS_SETTING, [])
    if isinstance(stored, str):
        return [stored] if stored else []
    return list(stored)


def save_custom_search_terms(terms: list[str]) -> None:
    """Persist the full list of user-added search terms.

    Args:
        terms: All custom terms to remember (defaults are not included).
    """
    _settings().setValue(_CUSTOM_TERMS_SETTING, terms)
