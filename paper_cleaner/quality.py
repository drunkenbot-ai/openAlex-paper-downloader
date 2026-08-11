"""Compute document statistics and decide whether text is training-ready."""

from __future__ import annotations

import re
from dataclasses import dataclass

from paper_cleaner.config import CleanConfig
from paper_cleaner.line_filters import is_graphical_garbage, is_pdf_artifact

_WORD_RE = re.compile(r"\b[\w'-]+\b")


@dataclass
class DocumentStats:
    """Basic size and quality metrics for a cleaned document."""

    characters: int
    words: int
    garbage_ratio: float


def calculate_statistics(text: str) -> DocumentStats:
    """Compute character/word counts and the extraction-garbage ratio.

    Args:
        text: Cleaned document text.

    Returns:
        The computed :class:`DocumentStats`.
    """
    lines = text.splitlines()
    nonempty = [line for line in lines if line.strip()]
    garbage = sum(
        is_graphical_garbage(line) or is_pdf_artifact(line)
        for line in nonempty
    )
    return DocumentStats(
        characters=len(text),
        words=len(_WORD_RE.findall(text)),
        garbage_ratio=garbage / max(1, len(nonempty)),
    )


def validate(stats: DocumentStats, config: CleanConfig) -> list[str]:
    """Check statistics against the configured quality thresholds.

    Args:
        stats: Output of :func:`calculate_statistics`.
        config: Active :class:`CleanConfig`.

    Returns:
        A list of failure reason codes; empty if the document passes.
    """
    reasons: list[str] = []
    if stats.characters < config.min_characters:
        reasons.append("too_short")
    if stats.words < config.min_words:
        reasons.append("too_few_words")
    if stats.garbage_ratio > config.max_garbage_ratio:
        reasons.append("high_garbage_ratio")
    return reasons
