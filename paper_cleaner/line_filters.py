"""Per-line classifiers used to strip non-scientific-prose noise."""

from __future__ import annotations

import re

_PAGE_NUMBER_RES = (
    re.compile(r"\A\d{1,4}\Z"),
    re.compile(r"\Apage\s+\d{1,4}\Z", re.IGNORECASE),
    re.compile(r"\A[-\u2013\u2014]?\s*\d{1,4}\s*[-\u2013\u2014]?\Z"),
    re.compile(r"\Apage\s+\d+\s+of\s+\d+\Z", re.IGNORECASE),
)

_PDF_ARTIFACT_EXACT = {"1234567890():,;", "1234567890", "OPEN", "Open"}
_PDF_ARTIFACT_SUBSTRINGS = (
    "endobj", "startxref", "/type /page", "/type /font",
    "/fontname", "xref", "trailer", "cid:",
)

_GRAPHICAL_CHARS = set("Gg\u2022\u00b7\u25cf\u25cb|")

# Tables that list citations per row/category (e.g. a "Related work"
# column) get flattened by PDF text extraction into standalone lines
# with no surrounding prose, since text extraction has no concept of
# table cells. A line dominated by "[8], [9], [15], ..." citation
# markers, once the markers themselves are stripped away, leaves
# essentially nothing behind — unlike a real sentence such as
# "SGD [181] and Adam [182] are well-suited...", which still has plenty
# of prose left after the same strip.
_CITATION_MARKER_RE = re.compile(r"\[\d{1,4}(?:[-\u2013,]\s*\d{1,4})*\]")

_PUBLISHER_METADATA_PATTERNS = (
    "version of record", "accepted manuscript", "accepted version",
    "author manuscript", "publisher's pdf", "publisher pdf",
    "link to published version", "link to publication record",
    "research portal", "institutional repository", "terms of use",
    "copyright and terms", "for personal use only",
    "for non-commercial use only", "not for redistribution",
    "downloaded from", "downloaded via", "research online",
    "coversheet", "available in", "available at the repository",
)

_LICENSE_PATTERNS = (
    "creative commons", "cc by", "cc-by", "attribution 3.0",
    "attribution 4.0", "licensed under", "license under",
)

_CORRESPONDENCE_RE = re.compile(
    r"\*?\s*correspond(?:ence|ing author)\s*(?:to)?\s*:", re.IGNORECASE
)

_AFFILIATION_TERMS = (
    "university", "institute", "department", "school", "college",
    "faculty", "hospital", "medical center", "medical centre",
    "laboratory", "laboratories", "research center", "research centre",
    "academy", "centre for", "center for",
)

_EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
)
_URL_RE = re.compile(r"\Ahttps?://\S+\Z")
_WWW_RE = re.compile(r"\Awww\.\S+\Z")
_DOI_RE = re.compile(r"\A(?:doi:\s*)?10\.\d{4,9}/\S+\Z", re.IGNORECASE)
_AUTHOR_NAME_RE = re.compile(
    r"\b[A-Z][a-zA-Z\u00c0-\u00ff]+(?:\s+[A-Z]\.)?"
    r"(?:\s+[A-Z][a-zA-Z\u00c0-\u00ff]+){1,2}\b"
)

# Large-collaboration papers (LIGO/Virgo-style) list dozens to hundreds of
# affiliations as "<index><Institution>, <City>, <Country>" tokens. PDF
# extraction often fuses several of these per raw line with no space
# between the index and the institution name (e.g. "125NCBJ, 05-400
# Swierk-Otwock, Poland 126Institute of Mathematics..."). This pattern
# almost never occurs in ordinary prose, so it is a reliable signal even
# before :func:`looks_like_author_list`'s person-name heuristic applies.
#
# Two constraints keep this from matching common scientific shorthand
# that has the same "digit immediately followed by capital letter"
# shape: generation/dimension tags ("5G", "6G", "2D", "3D") and isotope
# notation ("16O", "56Ni") are always exactly one or two letters long,
# so requiring at least 3 letters (`[A-Z][a-zA-Z]{2,}`) excludes them
# while still matching real institution names and acronyms ("14LIGO",
# "13Nikhef", "125NCBJ"). The trailing `(?=[,\s]|\Z)` boundary further
# excludes grant/award codes ("18KK0090", "80NSSC20K0527"), which keep
# fusing on more digits instead of ending at a comma/space/end.
_NUMBERED_AFFILIATION_RE = re.compile(r"(?:\A|\s)\d{1,3}[A-Z][a-zA-Z]{2,}(?=[,\s]|\Z)")

# Some collaboration papers (SDSS-style, as opposed to LIGO/Virgo-style)
# render numbered affiliations with a space between the index and the
# institution name ("66 AURA Observatory in Chile, ...") instead of
# fusing them ("66AURA..."). That shape alone is indistinguishable from
# numbered section headings ("1 Introduction"), footnotes ("84 See
# https://..."), or equations ("0 Ez = 0,"), all of which also start
# with "<digit(s)> <Capital letter>". It is only treated as reliable
# once corroborated by a genuine institution keyword via
# :func:`affiliation_score`.
_INDEXED_LINE_START_RE = re.compile(r"\A\d{1,3}\s+[A-Z][a-zA-Z]")

# Common math/notation symbols. Real affiliation address lines never
# contain these, but stray equation fragments (subscripts, deltas,
# summations) can otherwise slip past the single-token branch's comma
# check.
_MATH_SYMBOLS = set("∆Σ∈×±√∇∂∞≈≤≥∑∏∫")


def is_page_number(line: str) -> bool:
    """Return True if ``line`` is only a page number or "Page N" marker."""
    stripped = line.strip()
    return any(pattern.match(stripped) for pattern in _PAGE_NUMBER_RES)


def is_pdf_artifact(line: str) -> bool:
    """Return True if ``line`` looks like a raw PDF/text-extraction artifact."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped in _PDF_ARTIFACT_EXACT:
        return True
    lower = stripped.lower()
    if any(pattern in lower for pattern in _PDF_ARTIFACT_SUBSTRINGS):
        return True
    compact = re.sub(r"\s+", "", stripped)
    return bool(
        len(compact) >= 6 and re.fullmatch(r"[\d():,;|./\\]+", compact)
    )


def is_graphical_garbage(line: str) -> bool:
    """Return True if ``line`` is leftover figure/chart drawing noise."""
    stripped = line.strip()
    if not stripped:
        return False
    tokens = stripped.split()
    if tokens:
        graphical = sum(
            1 for token in tokens if set(token) <= _GRAPHICAL_CHARS
        )
        if len(tokens) >= 3 and graphical / len(tokens) >= 0.7:
            return True
    compact = re.sub(r"\s+", "", stripped)
    if len(compact) >= 8 and set(compact) <= _GRAPHICAL_CHARS:
        return True
    return bool(re.fullmatch(r"[-_=~\u2022\u00b7.]+", stripped))


def is_citation_cluster(line: str) -> bool:
    """Return True if ``line`` is just a run of bracketed citation markers.

    Detects flattened table cells (typically a "Related work"/"Refs"
    column) that PDF text extraction turns into a standalone line of
    ``"[8], [9], [15], ..."`` with no actual sentence around it. Real
    prose with inline citations, such as ``"SGD [181] and Adam [182]
    are well-suited..."``, still has substantial text left after the
    citation markers are stripped out and is not flagged.

    Args:
        line: A single, already-normalized line of text.

    Returns:
        True if the line is citation markers and little else.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if len(_CITATION_MARKER_RE.findall(stripped)) < 2:
        return False
    remainder = _CITATION_MARKER_RE.sub("", stripped)
    remainder = re.sub(r"[,;:.\s]+", "", remainder)
    return len(remainder) <= 2


def is_url_or_doi(line: str) -> bool:
    """Return True if ``line`` consists only of a URL or DOI."""
    stripped = line.strip()
    return bool(
        _URL_RE.match(stripped)
        or _WWW_RE.match(stripped)
        or _DOI_RE.match(stripped)
    )


def is_license_line(line: str) -> bool:
    """Return True if ``line`` states a Creative Commons / reuse license."""
    lower = line.lower()
    return any(pattern in lower for pattern in _LICENSE_PATTERNS)


def is_publisher_metadata(line: str) -> bool:
    """Return True if ``line`` is repository/publisher boilerplate."""
    lower = line.lower().strip()
    return any(pattern in lower for pattern in _PUBLISHER_METADATA_PATTERNS)


def is_correspondence_start(line: str) -> bool:
    """Return True if ``line`` opens or contains a "Corresponding author" marker.

    Uses a search rather than a prefix match because PDF text extraction
    frequently merges a preceding heading (e.g. "SURVEY PAPER") onto the
    same line as the "*Correspondence:" marker.
    """
    return bool(_CORRESPONDENCE_RE.search(line))


def looks_like_email(line: str) -> bool:
    """Return True if ``line`` contains an email address."""
    return bool(_EMAIL_RE.search(line))


def affiliation_score(line: str) -> int:
    """Count how many affiliation keywords (university, dept, ...) appear."""
    lower = line.lower()
    return sum(term in lower for term in _AFFILIATION_TERMS)


def author_name_score(line: str) -> int:
    """Count substrings shaped like "Firstname Lastname" author names."""
    return len(_AUTHOR_NAME_RE.findall(line))


def looks_like_author_list(line: str) -> bool:
    """Return True if ``line`` is a dense author/collaborator list.

    Requires several detected names together with either affiliation
    keywords or list separators, so ordinary prose is not misclassified.
    """
    stripped = line.strip()
    if not stripped:
        return False
    names = author_name_score(stripped)
    affiliations = affiliation_score(stripped)
    separators = stripped.count(";") + stripped.count("\u00b7")
    if names >= 6 and (affiliations >= 2 or separators >= 4):
        return True
    return len(stripped) > 300 and names >= 8


def looks_like_numbered_affiliation_line(line: str) -> bool:
    """Return True if ``line`` is a run of numbered author affiliations.

    Two or more fused ``<index><Capitalized word>`` tokens (e.g.
    ``"13Nikhef"``, ``"14LIGO"``) is a starting signal, but on its own it
    is not reliable enough: common scientific shorthand like "5G", "6G",
    "2D", "3D", or isotope notation like "16O" is exactly the same shape
    (digit immediately followed by a capitalized letter) and appears
    constantly in ordinary technical prose. A line is only treated as
    affiliation noise if it *also* carries a corroborating signal that
    real affiliation entries have and shorthand tokens don't: a known
    institution keyword (university, institute, department, ...) or a
    dense run of address-style commas.

    A single fused token is only treated as noise if it opens the line
    and the rest still looks like an affiliation (short, and containing
    a comma or a known affiliation keyword), so a line that merely
    starts with a number (e.g. a numbered list item) is not misclassified.

    Args:
        line: A single, already-normalized line of text.

    Returns:
        True if the line is (or starts) a numbered affiliation block.
    """
    stripped = line.strip()
    if not stripped:
        return False

    matches = _NUMBERED_AFFILIATION_RE.findall(stripped)
    if len(matches) >= 2:
        # Comma count alone is not a safe signal here: an ordinary
        # multi-sentence paragraph can easily rack up 3+ commas without
        # being anything like an address list. A known institution
        # keyword is far more specific to genuine affiliations, and the
        # length cap guards against a long paragraph that happens to
        # contain two unrelated digit+capital tokens far apart.
        return affiliation_score(stripped) >= 1 and len(stripped) <= 500

    starts_with_index = bool(
        re.match(r"\A\d{1,3}[A-Z][a-zA-Z]{2,}(?=[,\s]|\Z)", stripped)
    )
    if len(matches) == 1 and starts_with_index:
        # Equations that happen to start with a subscript-shaped token
        # (e.g. "2S +2 X j=1 ∆i jWj, (97)") can still slip past a bare
        # comma check, so also require the line be free of common math
        # notation symbols before trusting the comma as a real address
        # separator.
        if any(symbol in stripped for symbol in _MATH_SYMBOLS):
            return False
        return len(stripped) < 250 and (
            "," in stripped or affiliation_score(stripped) >= 1
        )
    return False


def looks_like_indexed_affiliation_line(line: str) -> bool:
    """Return True if ``line`` opens with "<index> <Institution...>".

    Catches the space-separated numbered-affiliation format (e.g. "66
    AURA Observatory in Chile, ...") that
    :func:`looks_like_numbered_affiliation_line` doesn't, since that one
    only matches indices *fused* directly onto the institution name with
    no space. Because "<digit(s)> <Capitalized word>" alone is also the
    shape of numbered section headings, footnotes, and equations, this
    additionally requires a genuine institution keyword and a modest
    length cap before treating the line as noise.

    Args:
        line: A single, already-normalized line of text.

    Returns:
        True if the line looks like a numbered, space-separated
        affiliation entry.
    """
    stripped = line.strip()
    if not stripped or not _INDEXED_LINE_START_RE.match(stripped):
        return False
    if "http://" in stripped or "https://" in stripped:
        # A URL substring can coincidentally contain an affiliation
        # keyword (e.g. ".../nyc-cityschools/..." contains "school"),
        # but a genuine affiliation address line never itself contains
        # a URL — that shape belongs to a numbered footnote instead.
        return False
    return affiliation_score(stripped) >= 1 and len(stripped) <= 300