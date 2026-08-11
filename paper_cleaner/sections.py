"""Scientific section-heading detection and article-start finding."""

from __future__ import annotations

import re

SECTION_NAMES: frozenset[str] = frozenset({
    "abstract", "summary", "introduction", "background",
    "methods", "method", "methodology", "materials and methods",
    "results", "discussion", "conclusion", "conclusions", "limitations",
    "future work", "related work", "literature review",
    "data availability", "code availability", "funding",
    "acknowledgements", "acknowledgments", "author contributions",
    "competing interests", "conflicts of interest", "conflict of interest",
    "ethics statement", "references", "bibliography", "appendix",
    "appendices", "supplementary material", "supplementary materials",
    "supplementary information", "supporting information",
})

_ARTICLE_START_NAMES = ("abstract", "summary", "introduction", "background")
_NUMBERED_HEADING_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+(.+)$")


def _normalize_heading(line: str) -> str:
    return line.strip().lower().strip(" .:-")


def is_section_heading(line: str) -> bool:
    """Return True if ``line`` is a standalone scientific section heading.

    Matches known section names (e.g. "Abstract", "References") as well
    as numbered headings such as "2.1 Methods".

    Args:
        line: A single, already-normalized line of text.

    Returns:
        True if the line looks like a section heading.
    """
    normalized = _normalize_heading(line)
    if not normalized:
        return False
    if normalized in SECTION_NAMES:
        return True
    match = _NUMBERED_HEADING_RE.match(line.strip())
    if match and len(match.group(1).strip()) <= 120:
        return True
    return False


def section_name(line: str) -> str:
    """Return the canonical section name for a heading line.

    Args:
        line: A line already confirmed to be a section heading.

    Returns:
        The lower-cased section name, or the heading title for numbered
        headings whose text is not in :data:`SECTION_NAMES`.
    """
    normalized = _normalize_heading(line)
    if normalized in SECTION_NAMES:
        return normalized
    match = _NUMBERED_HEADING_RE.match(line.strip())
    return match.group(1).strip() if match else line.strip()


def find_article_start(lines: list[str]) -> int | None:
    """Locate the first line that begins the real scientific article.

    Prefers "Abstract"/"Summary" over "Introduction"/"Background" because
    publisher cover sheets and author metadata usually precede the
    abstract but rarely precede the introduction as well.

    Args:
        lines: Normalized document lines.

    Returns:
        The index of the article-start line, or None if no anchor was
        found (in which case front matter should not be trimmed).
    """
    for index, line in enumerate(lines):
        if _normalize_heading(line) in ("abstract", "summary"):
            return index
    for index, line in enumerate(lines):
        if _normalize_heading(line) in ("introduction", "background"):
            return index
    return None
