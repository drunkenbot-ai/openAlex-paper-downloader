"""Remove front matter and inline metadata noise from a flat line list."""

from __future__ import annotations

from dataclasses import dataclass, field

from paper_cleaner import line_filters as lf
from paper_cleaner.sections import find_article_start, is_section_heading


@dataclass
class CleanupCounts:
    """Diagnostic counts of how many lines each cleanup step removed."""

    front_matter: int = 0
    publisher_metadata: int = 0
    correspondence: int = 0
    author_blocks: int = 0
    graphics: int = 0
    references: int = 0
    other_noise: int = field(default=0)


def remove_front_matter(lines: list[str]) -> tuple[list[str], int]:
    """Drop everything before the detected Abstract/Introduction anchor.

    Publisher cover sheets (e.g. institutional repository pages) and
    author/affiliation blocks live before the scientific article proper,
    so once the anchor is found the simplest robust fix is to discard
    everything ahead of it rather than classify each front-matter line.

    Args:
        lines: Normalized document lines.

    Returns:
        A tuple of the remaining lines and the count of lines removed.
    """
    start = find_article_start(lines)
    if start is None:
        return lines, 0
    return lines[start:], start


def remove_noise_lines(lines: list[str]) -> tuple[list[str], CleanupCounts]:
    """Strip publisher metadata, correspondence blocks, and figure noise.

    Args:
        lines: Document lines with front matter already removed.

    Returns:
        A tuple of the cleaned lines and per-category removal counts.
    """
    counts = CleanupCounts()
    result: list[str] = []
    in_correspondence = False

    for line in lines:
        if not line:
            result.append(line)
            continue

        if in_correspondence:
            if is_section_heading(line):
                in_correspondence = False
                result.append(line)
            elif (
                lf.looks_like_email(line)
                or lf.affiliation_score(line) >= 1
                or lf.is_url_or_doi(line)
                or len(line) < 100
            ):
                counts.correspondence += 1
            else:
                in_correspondence = False
                result.append(line)
            continue

        if lf.is_correspondence_start(line):
            in_correspondence = True
            counts.correspondence += 1
            continue
        if lf.is_url_or_doi(line) or lf.is_publisher_metadata(line):
            counts.publisher_metadata += 1
            continue
        if lf.is_license_line(line):
            counts.publisher_metadata += 1
            continue
        if lf.is_graphical_garbage(line):
            counts.graphics += 1
            continue
        if lf.looks_like_author_list(line):
            counts.author_blocks += 1
            continue
        result.append(line)

    return result, counts


def remove_references_section(lines: list[str]) -> tuple[list[str], int]:
    """Optionally drop the References/Bibliography section and beyond.

    Args:
        lines: Document lines (front matter already removed).

    Returns:
        A tuple of the remaining lines and the count of lines dropped.
    """
    for index, line in enumerate(lines):
        normalized = line.strip().lower().strip(" .:-")
        if normalized in ("references", "bibliography", "literature cited"):
            return lines[:index], len(lines) - index
    return lines, 0
