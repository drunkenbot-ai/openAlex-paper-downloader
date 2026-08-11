"""OpenAlex search API client."""

from __future__ import annotations

import logging
from typing import Any

import requests

from paper_app.downloader.config import DownloadConfig

log = logging.getLogger("research-corpus")

OPENALEX_URL = "https://api.openalex.org/works"


def build_session(config: DownloadConfig) -> requests.Session:
    """Create a ``requests`` session with the configured User-Agent.

    Args:
        config: Active download configuration.

    Returns:
        A ready-to-use HTTP session.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": config.user_agent,
        "Accept": "application/pdf,application/octet-stream,*/*",
    })
    return session


def search_openalex(
    query: str, config: DownloadConfig, session: requests.Session
) -> list[dict[str, Any]]:
    """Search OpenAlex for works matching ``query``, paging as needed.

    Args:
        query: Free-text search term.
        config: Active download configuration.
        session: HTTP session to use for requests.

    Returns:
        Up to ``config.max_papers_per_term`` raw OpenAlex work records.
    """
    params: dict[str, Any] = {
        "api_key": config.api_key,
        "search": query,
        "filter": ",".join([
            "open_access.is_oa:true",
            f"publication_year:>{config.min_year - 1}",
            "type:article",
            f"cited_by_count:>{config.min_citations - 1}",
        ]),
        "sort": "cited_by_count:desc",
        "per_page": 100,
        "cursor": "*",
    }

    papers: list[dict[str, Any]] = []
    while len(papers) < config.max_papers_per_term:
        try:
            response = session.get(
                OPENALEX_URL, params=params, timeout=config.request_timeout
            )
            if response.status_code != 200:
                log.error("OpenAlex HTTP %d for '%s'", response.status_code, query)
                break
            data = response.json()
        except Exception as error:  # noqa: BLE001 - surfaced via logging
            log.error("OpenAlex request failed for '%s': %s", query, error)
            break

        results = data.get("results", [])
        if not results:
            break

        papers.extend(results)
        log.info("Search '%s': %d candidates", query, len(papers))

        next_cursor = (data.get("meta") or {}).get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor

    return papers[: config.max_papers_per_term]
