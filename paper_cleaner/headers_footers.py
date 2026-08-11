"""Detect and strip running headers/footers repeated across many pages."""

from __future__ import annotations

from collections import Counter

from paper_cleaner.line_filters import is_page_number
from paper_cleaner.text_utils import normalize_line

_MIN_LINE_LENGTH = 4
_MIN_PAGES_TO_CHECK = 3


def find_repeated_lines(
    pages: list[list[str]], repeated_ratio: float
) -> set[str]:
    """Find lines (lower-cased) that repeat on many pages.

    These are typically running headers such as a journal name, the
    article title, or a footer with the article's DOI.

    Args:
        pages: One list of raw lines per PDF page.
        repeated_ratio: Minimum fraction of pages a line must appear on
            (at most once per page) to count as repeated.

    Returns:
        The set of lower-cased lines considered running headers/footers.
    """
    if len(pages) < _MIN_PAGES_TO_CHECK:
        return set()

    counts: Counter[str] = Counter()
    for page in pages:
        seen_this_page: set[str] = set()
        for raw_line in page:
            line = normalize_line(raw_line)
            if len(line) < _MIN_LINE_LENGTH or is_page_number(line):
                continue
            key = line.lower()
            if key not in seen_this_page:
                counts[key] += 1
                seen_this_page.add(key)

    threshold = max(2, int(len(pages) * repeated_ratio))
    return {line for line, count in counts.items() if count >= threshold}


def strip_repeated_lines(
    pages: list[list[str]], repeated_lines: set[str]
) -> list[list[str]]:
    """Remove previously detected repeated header/footer lines.

    Args:
        pages: One list of raw lines per PDF page.
        repeated_lines: Output of :func:`find_repeated_lines`.

    Returns:
        A new list of pages with the matching lines dropped.
    """
    cleaned_pages: list[list[str]] = []
    for page in pages:
        cleaned_page: list[str] = []
        for raw_line in page:
            line = normalize_line(raw_line)
            if line and line.lower() in repeated_lines:
                continue
            cleaned_page.append(line)
        cleaned_pages.append(cleaned_page)
    return cleaned_pages
