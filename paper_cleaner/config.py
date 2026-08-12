"""Configuration options for the cleaning pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CleanConfig:
    """Tunable options for :func:`paper_cleaner.pipeline.clean_document`.

    Attributes:
        min_characters: Minimum cleaned character count to keep a document.
        min_words: Minimum cleaned word count to keep a document.
        max_garbage_ratio: Maximum share of non-empty lines that may be
            classified as extraction garbage before a document is rejected.
        remove_references: Whether to drop the References/Bibliography
            section and everything after it.
        repeated_line_ratio: Share of pages a line must appear on (fuzzy
            matched, ignoring embedded page numbers) to be treated as a
            running header or footer. Kept low (rather than e.g. 0.30)
            because many journals alternate the header text between
            odd/even pages, so any single variant may only appear on
            around half of the article's pages; supplementary/appendix
            pages often carry no running head at all, further diluting
            the fraction of the *whole* PDF any one header variant
            covers. The absolute floor of 2 occurrences (applied in
            headers_footers.find_repeated_lines) still guards short
            documents.
    """

    min_characters: int = 1500
    min_words: int = 250
    max_garbage_ratio: float = 0.10
    remove_references: bool = False
    repeated_line_ratio: float = 0.08
