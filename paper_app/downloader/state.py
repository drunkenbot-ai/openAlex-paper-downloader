"""Daily download-counter state and JSONL persistence helpers."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from paper_app.downloader.config import DownloadConfig

log = logging.getLogger("research-corpus")


def load_state(config: DownloadConfig) -> dict[str, Any]:
    """Load today's download counter, resetting it if the day changed.

    Args:
        config: Active download configuration.

    Returns:
        A dict with ``date`` and ``downloads`` keys.
    """
    today = str(date.today())

    if not config.state_file.exists():
        state = {"date": today, "downloads": 0}
        save_state(config, state)
        return state

    try:
        with open(config.state_file, "r", encoding="utf-8") as handle:
            state = json.load(handle)
    except Exception as error:  # noqa: BLE001 - fall back to a fresh state
        log.warning("Unable to read state file: %s", error)
        state = {"date": today, "downloads": 0}

    if state.get("date") != today:
        log.info("New day detected. Resetting daily download counter.")
        state = {"date": today, "downloads": 0}
        save_state(config, state)

    return state


def save_state(config: DownloadConfig, state: dict[str, Any]) -> None:
    """Atomically write the download-counter state to disk.

    Args:
        config: Active download configuration.
        state: State dict to persist.
    """
    config.state_dir.mkdir(parents=True, exist_ok=True)
    temp_path = config.state_file.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    temp_path.replace(config.state_file)


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    """Append one JSON object as a line to ``path``.

    Args:
        path: File to append to.
        data: JSON-serializable object to write.
    """
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def save_metadata(metadata: dict[str, Any], path: Path) -> None:
    """Atomically write one paper's metadata JSON to disk.

    Args:
        metadata: Metadata dict to persist.
        path: Destination ``.json`` file.
    """
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def load_existing_ids(manifest_file: Path) -> set[str]:
    """Return the set of paper IDs already recorded in the manifest.

    Args:
        manifest_file: Path to the ``manifest.jsonl`` file.

    Returns:
        The set of previously downloaded paper IDs.
    """
    ids: set[str] = set()
    if not manifest_file.exists():
        return ids

    with open(manifest_file, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            paper_id = data.get("id")
            if paper_id:
                ids.add(paper_id)

    return ids
