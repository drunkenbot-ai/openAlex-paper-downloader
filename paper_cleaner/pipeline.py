"""Single-pass pipeline turning a research PDF into training-ready text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from paper_cleaner import body_cleanup, headers_footers, quality
from paper_cleaner.config import CleanConfig
from paper_cleaner.pdf_extract import extract_pdf_pages
from paper_cleaner.text_utils import (
    collapse_blank_lines,
    join_wrapped_lines,
    normalize_unicode,
    repair_hyphenation,
)


@dataclass
class CleanResult:
    """Outcome of cleaning a single document.

    Attributes:
        text: The cleaned text (empty if the document was rejected).
        valid: Whether the document passed the quality thresholds.
        reject_reasons: Quality-check failure codes, if any.
        stats: Character/word/garbage statistics for the cleaned text.
        cleanup: Per-category counts of lines removed during cleaning.
    """

    text: str
    valid: bool
    reject_reasons: list[str]
    stats: quality.DocumentStats
    cleanup: body_cleanup.CleanupCounts


def clean_pages(
    pages: list[list[str]], config: CleanConfig
) -> CleanResult:
    """Run the full cleaning pipeline over already-extracted PDF pages.

    Args:
        pages: One list of raw lines per PDF page, as returned by
            :func:`paper_cleaner.pdf_extract.extract_pdf_pages`.
        config: Cleaning thresholds and options.

    Returns:
        The :class:`CleanResult` for this document.
    """
    pages = [[normalize_unicode(line) for line in page] for page in pages]

    repeated = headers_footers.find_repeated_lines(
        pages, config.repeated_line_ratio
    )
    pages = headers_footers.strip_repeated_lines(pages, repeated)

    lines: list[str] = []
    for page in pages:
        lines.extend(page)
        if lines and lines[-1] != "":
            lines.append("")

    lines, front_matter_removed = body_cleanup.remove_front_matter(lines)
    lines, counts = body_cleanup.remove_noise_lines(lines)
    counts.front_matter = front_matter_removed

    if config.remove_references:
        lines, removed = body_cleanup.remove_references_section(lines)
        counts.references = removed

    lines = join_wrapped_lines(lines)
    text = collapse_blank_lines(repair_hyphenation("\n".join(lines)))

    stats = quality.calculate_statistics(text)
    reasons = quality.validate(stats, config)
    return CleanResult(
        text=text if not reasons else "",
        valid=not reasons,
        reject_reasons=reasons,
        stats=stats,
        cleanup=counts,
    )


def process_pdf(
    pdf_path: Path, output_dir: Path, config: CleanConfig | None = None
) -> CleanResult:
    """Extract, clean, and (if valid) write out one PDF as training text.

    Args:
        pdf_path: Source PDF file.
        output_dir: Directory the cleaned ``.txt`` file is written into.
        config: Cleaning options; defaults to :class:`CleanConfig`.

    Returns:
        The :class:`CleanResult` describing the outcome.
    """
    config = config or CleanConfig()
    pages = extract_pdf_pages(pdf_path)
    result = clean_pages(pages, config)

    if result.valid:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{pdf_path.stem}.txt"
        output_path.write_text(result.text, encoding="utf-8")

    return result
