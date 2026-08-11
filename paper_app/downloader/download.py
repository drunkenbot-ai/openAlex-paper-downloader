"""PDF validation and per-paper download logic."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import requests

from paper_app.downloader import metadata as meta
from paper_app.downloader.config import DownloadConfig
from paper_app.downloader.state import save_metadata

log = logging.getLogger("research-corpus")


def is_pdf_file(path: Path) -> bool:
    """Return True if ``path`` exists, is non-trivial, and starts with %PDF-.

    Args:
        path: File to check.

    Returns:
        True if the file looks like a real PDF.
    """
    try:
        if not path.exists() or path.stat().st_size < 10_000:
            return False
        with open(path, "rb") as handle:
            return handle.read(5) == b"%PDF-"
    except Exception:  # noqa: BLE001 - treat any read error as "not a PDF"
        return False


def classify_http_error(status_code: int) -> str:
    """Classify an HTTP status code as "permanent" or "retry".

    Args:
        status_code: HTTP response status code.

    Returns:
        ``"retry"`` for 5xx server errors, ``"permanent"`` otherwise.
    """
    if status_code in {400, 401, 403, 404, 405, 410, 451}:
        return "permanent"
    if status_code >= 500:
        return "retry"
    return "permanent"


def try_download_location(
    metadata_record: dict[str, Any],
    location: dict[str, Any],
    pdf_path: Path,
    config: DownloadConfig,
    session: requests.Session,
) -> dict[str, Any]:
    """Attempt to download one candidate PDF location, with retries.

    Args:
        metadata_record: The paper's metadata dict (mutated in place with
            attempted URLs).
        location: One download location from :func:`metadata.sort_locations`.
        pdf_path: Destination path for the downloaded PDF.
        config: Active download configuration.
        session: HTTP session to use for requests.

    Returns:
        A result dict with at least a ``success`` key.
    """
    pdf_url = meta.normalize_url(location.get("pdf_url"))
    if not pdf_url:
        return {"success": False, "reason": "no_pdf_url", "retryable": False}

    metadata_record["attempted_urls"].append(pdf_url)

    for attempt in range(1, config.max_retries + 1):
        try:
            log.info(
                "Downloading [%d/%d]: %s",
                attempt, config.max_retries, metadata_record["title"][:100],
            )
            response = session.get(
                pdf_url,
                timeout=config.request_timeout,
                stream=True,
                allow_redirects=True,
            )

            if response.status_code != 200:
                category = classify_http_error(response.status_code)
                if category == "permanent":
                    log.warning(
                        "Skipping URL (HTTP %d): %s", response.status_code, pdf_url
                    )
                    return {
                        "success": False,
                        "reason": f"http_{response.status_code}",
                        "retryable": False,
                    }
                log.warning("Temporary HTTP %d", response.status_code)
                if attempt < config.max_retries:
                    time.sleep(2 * attempt)
                    continue
                return {
                    "success": False,
                    "reason": f"http_{response.status_code}",
                    "retryable": True,
                }

            temp_path = pdf_path.with_suffix(".part")
            with open(temp_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)

            if not is_pdf_file(temp_path):
                temp_path.unlink(missing_ok=True)
                log.warning("Not a PDF, skipping URL: %s", pdf_url)
                return {"success": False, "reason": "not_a_pdf", "retryable": False}

            temp_path.replace(pdf_path)
            return {
                "success": True,
                "url": pdf_url,
                "landing_page": location.get("landing_page_url"),
                "download_source": location.get("source"),
                "file_size": pdf_path.stat().st_size,
            }

        except (requests.Timeout, requests.ConnectionError) as error:
            log.warning("Network error: %s", error)
            if attempt < config.max_retries:
                time.sleep(2 * attempt)
                continue
            return {"success": False, "reason": str(error), "retryable": True}

        except Exception as error:  # noqa: BLE001 - surfaced via logging
            log.warning("Download error: %s", error)
            return {"success": False, "reason": str(error), "retryable": False}

    return {"success": False, "reason": "unknown_failure", "retryable": False}


def download_paper(
    metadata_record: dict[str, Any], config: DownloadConfig, session: requests.Session
) -> dict[str, Any]:
    """Download one paper's PDF, trying its locations in priority order.

    Args:
        metadata_record: Metadata dict from :func:`metadata.create_metadata`.
        config: Active download configuration.
        session: HTTP session to use for requests.

    Returns:
        A dict with ``success``, ``new_download``, and ``metadata`` keys.
    """
    paper_id = metadata_record["id"]
    pdf_path = config.papers_dir / f"{paper_id}.pdf"
    metadata_path = config.metadata_dir / f"{paper_id}.json"

    if is_pdf_file(pdf_path):
        metadata_record["downloaded"] = True
        metadata_record["file"] = str(pdf_path)
        metadata_record["file_size"] = pdf_path.stat().st_size
        save_metadata(metadata_record, metadata_path)
        return {"success": True, "new_download": False, "metadata": metadata_record}

    locations = meta.sort_locations(metadata_record.get("oa_locations", []))
    if not locations:
        metadata_record["error"] = "No OA PDF locations"
        return {"success": False, "new_download": False, "metadata": metadata_record}

    for location in locations:
        result = try_download_location(
            metadata_record, location, pdf_path, config, session
        )
        if result["success"]:
            metadata_record.update({
                "downloaded": True,
                "successful_url": result["url"],
                "download_source": result.get("download_source"),
                "file": str(pdf_path),
                "file_size": result["file_size"],
                "landing_page": result.get("landing_page"),
            })
            save_metadata(metadata_record, metadata_path)
            log.info("SUCCESS: %s", metadata_record["title"][:100])
            return {"success": True, "new_download": True, "metadata": metadata_record}

    metadata_record["downloaded"] = False
    metadata_record["error"] = "All OA PDF locations failed"
    save_metadata(metadata_record, metadata_path)
    return {"success": False, "new_download": False, "metadata": metadata_record}
