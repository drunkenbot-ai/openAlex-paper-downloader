"""Orchestrates search -> filter -> download, yielding progress updates."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from paper_app.downloader import client, metadata as meta
from paper_app.downloader.config import DownloadConfig
from paper_app.downloader.download import download_paper, is_pdf_file
from paper_app.downloader.state import (
    append_jsonl,
    load_existing_ids,
    load_state,
    save_state,
)


@dataclass
class DownloadProgress:
    """One human-readable status line emitted while a run proceeds.

    Attributes:
        message: Short description of what just happened.
        index: Papers processed so far in the download phase (0 while
            still searching).
        total: Total papers selected for download this run.
        done: True on the final update of the run.
    """

    message: str
    index: int = 0
    total: int = 0
    done: bool = False


def _search_candidates(
    config: DownloadConfig, existing_ids: set[str]
) -> Iterator[DownloadProgress | dict[str, Any]]:
    """Search every configured term, yielding progress and metadata dicts."""
    session = client.build_session(config)
    seen: dict[str, dict[str, Any]] = {}

    for term in config.search_terms:
        yield DownloadProgress(message=f"Searching: {term}")
        for work in client.search_openalex(term, config, session):
            if not meta.filter_paper(work, config):
                continue
            paper_id = meta.make_id(work)
            seen[paper_id] = work

    yield DownloadProgress(message=f"Unique candidate papers: {len(seen)}")

    for paper_id, work in seen.items():
        if paper_id in existing_ids:
            continue
        if is_pdf_file(config.papers_dir / f"{paper_id}.pdf"):
            continue
        yield meta.create_metadata(work)


def run_download(config: DownloadConfig) -> Iterator[DownloadProgress]:
    """Run one full download pass and yield progress as it proceeds.

    Args:
        config: Active download configuration.

    Yields:
        A :class:`DownloadProgress` update after each notable step.
    """
    config.ensure_directories()
    state = load_state(config)
    remaining = config.max_downloads_per_day - state.get("downloads", 0)

    yield DownloadProgress(
        message=f"Downloads today: {state.get('downloads', 0)}/"
        f"{config.max_downloads_per_day}"
    )
    if remaining <= 0:
        yield DownloadProgress(message="Daily download limit reached.", done=True)
        return

    existing_ids = load_existing_ids(config.manifest_file)
    candidates: list[dict[str, Any]] = []
    for item in _search_candidates(config, existing_ids):
        if isinstance(item, DownloadProgress):
            yield item
        else:
            candidates.append(item)

    candidates.sort(key=lambda record: record.get("citations", 0), reverse=True)
    candidates = candidates[:remaining]
    total = len(candidates)
    yield DownloadProgress(message=f"Selected for download: {total}", total=total)

    if not candidates:
        yield DownloadProgress(message="Nothing new to download.", done=True)
        return

    session = client.build_session(config)
    successful = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=config.download_workers) as executor:
        futures = {
            executor.submit(download_paper, record, config, session): record
            for record in candidates
        }
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            record = result["metadata"]

            if result["success"] and result["new_download"]:
                successful += 1
                state["downloads"] += 1
                save_state(config, state)
                append_jsonl(config.manifest_file, record)
                message = f"Downloaded: {record['title'][:80]}"
            elif result["success"]:
                append_jsonl(config.manifest_file, record)
                message = f"Already had: {record['title'][:80]}"
            else:
                failed += 1
                append_jsonl(config.failed_file, record)
                message = f"Failed: {record['title'][:80]} ({record.get('error')})"

            yield DownloadProgress(message=message, index=index, total=total)

    yield DownloadProgress(
        message=f"Done. Downloaded {successful}, failed {failed}.",
        index=total,
        total=total,
        done=True,
    )
