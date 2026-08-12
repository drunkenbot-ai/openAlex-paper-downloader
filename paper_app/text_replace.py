"""Regex or plain-text search-and-replace helpers for cleaned documents."""

from __future__ import annotations

import re


def compile_pattern(pattern: str, use_regex: bool, case_sensitive: bool) -> re.Pattern[str]:
    """Compile a find pattern, escaping it first if not using regex.

    Args:
        pattern: The raw find text typed by the user.
        use_regex: Whether to treat ``pattern`` as a regular expression.
        case_sensitive: Whether the match should be case sensitive.

    Returns:
        A compiled regular expression.

    Raises:
        re.error: If ``use_regex`` is True and ``pattern`` is invalid.
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    source = pattern if use_regex else re.escape(pattern)
    return re.compile(source, flags)


def count_matches(text: str, compiled: re.Pattern[str]) -> int:
    """Return how many times ``compiled`` matches within ``text``.

    Args:
        text: Text to search.
        compiled: Compiled find pattern.

    Returns:
        The number of matches found.
    """
    return len(compiled.findall(text))


def apply_replacement(
    text: str, compiled: re.Pattern[str], replacement: str, use_regex: bool
) -> tuple[str, int]:
    """Replace every match of ``compiled`` in ``text``.

    Args:
        text: Source text to search.
        compiled: Compiled find pattern.
        replacement: Replacement text. Regex backreferences (``\\1``, etc.)
            are honored only when ``use_regex`` is True, so literal
            backslashes in plain-text mode are inserted as-is.
        use_regex: Whether the find pattern is a regular expression.

    Returns:
        A tuple of the new text and the number of replacements made.
    """
    count = 0

    def _sub(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return match.expand(replacement) if use_regex else replacement

    new_text = compiled.sub(_sub, text)
    return new_text, count
