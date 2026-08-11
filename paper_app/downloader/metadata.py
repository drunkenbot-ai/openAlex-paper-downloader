"""Metadata extraction, license resolution, and candidate filtering."""

from __future__ import annotations

import hashlib
from typing import Any

from paper_app.downloader.config import DownloadConfig

_REPOSITORY_DOMAINS: tuple[str, ...] = (
    "arxiv.org", "biorxiv.org", "medrxiv.org", "pmc.ncbi.nlm.nih.gov",
    "europepmc.org", "zenodo.org", "osf.io", "researchgate.net",
    "hal.science", "repository.", ".edu/", ".ac.uk/",
)
_OA_PUBLISHER_DOMAINS: tuple[str, ...] = (
    "plos.org", "frontiersin.org", "mdpi.com", "peerj.com",
    "biomedcentral.com",
)
_LOW_PRIORITY_PUBLISHER_DOMAINS: tuple[str, ...] = (
    "sciencedirect.com", "academic.oup.com", "wiley.com",
    "onlinelibrary.wiley.com", "springer.com", "link.springer.com",
    "aps.org", "link.aps.org", "karger.com",
)


def make_id(work: dict[str, Any]) -> str:
    """Derive a stable short ID for an OpenAlex work.

    Args:
        work: Raw OpenAlex "work" record.

    Returns:
        The OpenAlex ID suffix, or a hash of the DOI/title as a fallback.
    """
    openalex_id = work.get("id")
    if openalex_id:
        return openalex_id.rstrip("/").split("/")[-1]

    doi = work.get("doi")
    if doi:
        return hashlib.sha1(doi.encode("utf-8")).hexdigest()[:16]

    title = work.get("title", "")
    return hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]


def normalize_url(url: str | None) -> str | None:
    """Return ``url`` stripped and validated, or None if unusable.

    Args:
        url: Candidate URL string.

    Returns:
        The cleaned URL, or None if it is empty or not http(s).
    """
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return None
    return url


def get_license(work: dict[str, Any]) -> str | None:
    """Pick the most permissive license listed across a work's locations.

    Args:
        work: Raw OpenAlex "work" record.

    Returns:
        The preferred license string, or None if none is listed.
    """
    licenses: list[str] = []
    for location in work.get("locations") or []:
        name = location.get("license")
        if name:
            licenses.append(name.strip().lower())
    licenses = list(dict.fromkeys(licenses))
    if not licenses:
        return None

    for preferred in ("cc-by", "cc-by-sa", "cc0", "public-domain"):
        if preferred in licenses:
            return preferred
    return licenses[0]


def get_oa_locations(work: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract open-access download locations from an OpenAlex work.

    Args:
        work: Raw OpenAlex "work" record.

    Returns:
        A list of location dicts with normalized PDF/landing-page URLs.
    """
    results: list[dict[str, Any]] = []
    for location in work.get("locations") or []:
        pdf_url = normalize_url(location.get("pdf_url"))
        landing_url = normalize_url(location.get("landing_page_url"))
        if not pdf_url and not landing_url:
            continue

        source = location.get("source") or {}
        results.append({
            "pdf_url": pdf_url,
            "landing_page_url": landing_url,
            "source": source.get("display_name"),
            "source_type": source.get("type"),
            "is_oa": location.get("is_oa", False),
            "license": location.get("license"),
            "version": location.get("version"),
        })
    return results


def location_priority(location: dict[str, Any]) -> int:
    """Score a download location; higher is a better download candidate.

    Args:
        location: One entry from :func:`get_oa_locations`.

    Returns:
        The priority score (repositories and PDFs rank highest).
    """
    pdf_url = (location.get("pdf_url") or "").lower()
    landing_url = (location.get("landing_page_url") or "").lower()
    score = 0

    for domain in _REPOSITORY_DOMAINS:
        if domain in pdf_url:
            score += 100
        elif domain in landing_url:
            score += 80

    for domain in _OA_PUBLISHER_DOMAINS:
        if domain in pdf_url:
            score += 50

    if location.get("source_type") == "repository":
        score += 80
    if location.get("is_oa"):
        score += 20
    if pdf_url:
        score += 30

    for domain in _LOW_PRIORITY_PUBLISHER_DOMAINS:
        if domain in pdf_url:
            score -= 50

    return score


def sort_locations(locations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort download locations best-first by :func:`location_priority`."""
    return sorted(locations, key=location_priority, reverse=True)


def filter_paper(work: dict[str, Any], config: DownloadConfig) -> bool:
    """Decide whether an OpenAlex work is eligible for download.

    Args:
        work: Raw OpenAlex "work" record.
        config: Active download configuration.

    Returns:
        True if the work passes the OA, year, citation, location, and
        license checks.
    """
    if work.get("is_retracted"):
        return False
    if not (work.get("open_access") or {}).get("is_oa", False):
        return False

    year = work.get("publication_year")
    if year and year < config.min_year:
        return False
    if work.get("cited_by_count", 0) < config.min_citations:
        return False
    if not get_oa_locations(work):
        return False

    if config.allowed_licenses and get_license(work) not in config.allowed_licenses:
        return False

    return True


def create_metadata(work: dict[str, Any]) -> dict[str, Any]:
    """Build the persisted metadata record for a candidate paper.

    Args:
        work: Raw OpenAlex "work" record.

    Returns:
        A metadata dict ready to be saved and later updated by the
        download step.
    """
    authors = [
        {
            "name": (authorship.get("author") or {}).get("display_name"),
            "openalex_id": (authorship.get("author") or {}).get("id"),
        }
        for authorship in work.get("authorships") or []
        if authorship.get("author")
    ]
    source = (work.get("primary_location") or {}).get("source") or {}
    locations = sort_locations(get_oa_locations(work))

    return {
        "id": make_id(work),
        "openalex_id": work.get("id"),
        "title": work.get("title"),
        "authors": authors,
        "year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "doi": work.get("doi"),
        "type": work.get("type"),
        "language": work.get("language"),
        "citations": work.get("cited_by_count", 0),
        "journal": source.get("display_name"),
        "publisher": source.get("host_organization_name"),
        "open_access": True,
        "license": get_license(work),
        "oa_locations": locations,
        "attempted_urls": [],
        "successful_url": None,
        "download_source": None,
        "downloaded": False,
        "error": None,
    }
