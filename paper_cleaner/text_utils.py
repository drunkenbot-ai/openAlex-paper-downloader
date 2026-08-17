"""Low-level, stateless text-normalization helpers."""

from __future__ import annotations

import re
import unicodedata

_UNICODE_REPLACEMENTS: dict[str, str] = {
    "\u00a0": " ",
    "\u200b": "",
    "\u200c": "",
    "\u200d": "",
    "\ufeff": "",
    "\u00ad": "",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb00": "ff",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
}

# Unicode "bracket extension piece" characters (Miscellaneous Technical
# block) used to render tall, multi-row parenthesis/bracket/brace
# delimiters around matrices and piecewise-function definitions. PDF
# text extraction has no notion of the 2D layout that gave these pieces
# meaning, so once flattened to a single line they become unreadable
# bracket soup (e.g. "⎛ ⎝ ⎜ ⎜ ⎜ ... ⎞ ⎠ ⎟ ⎟ ⎟"). Unlike a full equation,
# which can still be partly legible as flattened text, these specific
# pieces carry no content on their own -- they only ever encode the
# *shape* of a delimiter that spanned several original lines -- so
# removing the characters (not the whole line, which often has real
# prose merged onto it by join_wrapped_lines) is unambiguous.
for _bracket_piece in (
    "\u239b\u239c\u239d\u239e\u239f\u23a0"  # parenthesis pieces
    "\u23a1\u23a2\u23a3\u23a4\u23a5\u23a6"  # square bracket pieces
    "\u23a7\u23a8\u23a9\u23aa\u23ab\u23ac\u23ad"  # curly brace pieces
    "\u23ae\u23af\u23b0\u23b1"  # additional extension pieces
):
    _UNICODE_REPLACEMENTS[_bracket_piece] = " "

# Some math fonts map the same kind of bracket/brace extension pieces
# into the Private Use Area instead of the standard Miscellaneous
# Technical block above (e.g. a piecewise-definition brace rendered as
# "V (φ) = \uf8f1 \uf8f4 \uf8f2 \uf8f4 \uf8f3 V0 ..."). PUA codepoints
# have no fixed meaning in general, so only the specific range observed
# serving this exact role is blanked out here, not the whole PUA block.
for _pua_bracket_piece in "\uf8ee\uf8ef\uf8f0\uf8f1\uf8f2\uf8f3\uf8f4\uf8f9\uf8fa\uf8fb":
    _UNICODE_REPLACEMENTS[_pua_bracket_piece] = " "

_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_HYPHEN_LINEBREAK_RE = re.compile(r"(?<=[A-Za-z])-\n(?=[a-z])")
_HYPHEN_SPACE_RE = re.compile(r"\b([a-z]{4,})-\s+([a-z]{2,})\b")

# C0 control characters (0x00-0x1F) other than the whitespace ones we
# actually want to keep (\t, \n, \r). These show up when a PDF's math
# font maps bracket/operator glyphs (e.g. summation limits, angle
# brackets) to raw control-code positions instead of proper Unicode
# codepoints, and PyMuPDF extracts the byte value as-is. Unlike garbled
# math symbols elsewhere in a paper, these carry no recoverable meaning
# and have zero legitimate use in text, so stripping them is unambiguous.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Some layouts (e.g. Nature) place a "Received:/Accepted:/Published
# online:" submission-history block plus numbered author affiliations
# in a side column that PDF text extraction interleaves into the main
# column's paragraph, rather than as lines of their own. That makes it
# invisible to line-level filters, so it is matched and removed as a
# single span of raw text instead, bounded by its two clearest anchors:
# the "Received:" marker and the email address that closes the
# affiliation list.
_INLINE_SUBMISSION_METADATA_RE = re.compile(
    r"\bReceived:\s*\d{1,2}\s+\w+\s+\d{4}\b.{0,1500}?"
    r"[\w.+-]+@[\w-]+\.[\w.-]+",
    re.DOTALL,
)


def normalize_unicode(text: str) -> str:
    """Normalize Unicode form and strip invisible/control characters.

    Args:
        text: Raw text extracted from a PDF.

    Returns:
        Text with NFKC normalization, ligatures expanded, zero-width or
        non-breaking characters replaced with plain equivalents, stray
        C0 control characters removed, and matrix/bracket-extension
        pieces blanked out.
    """
    text = unicodedata.normalize("NFKC", text)
    for old, new in _UNICODE_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = _CONTROL_CHAR_RE.sub("", text)
    return text


def normalize_line(line: str) -> str:
    """Collapse tabs and repeated spaces, then strip the line.

    Args:
        line: A single line of text.

    Returns:
        The normalized line, or an empty string if it was blank.
    """
    line = line.replace("\t", " ")
    line = _MULTI_SPACE_RE.sub(" ", line)
    return line.strip()


def repair_hyphenation(text: str) -> str:
    """Rejoin words that were split by PDF line-wrapping hyphenation.

    Handles both ``treat-\\nment`` (line-break hyphens) and ``treat- ment``
    (same-line hyphens introduced by column extraction).

    Args:
        text: Full document text.

    Returns:
        Text with hyphenated word breaks rejoined.
    """
    text = _HYPHEN_LINEBREAK_RE.sub("", text)
    text = _HYPHEN_SPACE_RE.sub(r"\1\2", text)
    return text


def join_wrapped_lines(lines: list[str]) -> list[str]:
    """Merge lines that are really one wrapped paragraph.

    A line is joined to the previous one unless the previous line ends in
    sentence-final punctuation, the previous line is blank (paragraph
    break), or the current line looks like a heading.

    Args:
        lines: Cleaned, normalized lines (headings/blank lines preserved).

    Returns:
        A new list of lines with wrapped paragraphs merged.
    """
    from paper_cleaner.sections import is_section_heading

    result: list[str] = []
    end_punctuation = (".", ":", ";", "?", "!", ")", "]", "}")

    for line in lines:
        if not line or not result or not result[-1]:
            result.append(line)
            continue
        if is_section_heading(line) or is_section_heading(result[-1]):
            result.append(line)
            continue
        if result[-1].endswith(end_punctuation):
            result.append(line)
            continue
        result[-1] = f"{result[-1]} {line}"

    return result


def strip_inline_submission_metadata(text: str) -> str:
    """Remove an embedded Received/Accepted/affiliations/email span.

    Args:
        text: Full document text, already paragraph-joined.

    Returns:
        Text with the first matching submission-metadata span removed.
        Bounded to a 1500-character span so a missing/odd email address
        elsewhere in the document can't cause runaway deletion.
    """
    return _INLINE_SUBMISSION_METADATA_RE.sub(" ", text)


def collapse_blank_lines(text: str) -> str:
    """Collapse three or more consecutive blank lines down to one.

    Args:
        text: Full document text.

    Returns:
        Text with excess blank lines removed and outer whitespace trimmed.
    """
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
