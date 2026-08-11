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