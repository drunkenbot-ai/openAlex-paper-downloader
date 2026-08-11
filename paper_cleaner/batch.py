"""Batch-process a folder of PDFs through the cleaning pipeline."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from paper_cleaner.config import CleanConfig
from paper_cleaner.pipeline import CleanResult, process_pdf


@dataclass
class BatchProgress:
    """One progress update emitted while processing a folder.

    Attributes:
        index: 1-based position of ``pdf_path`` in the batch.
        total: Total number of PDFs in the batch.
        pdf_path: The file just processed.
        result: The cleaning outcome for that file, or None on error.
        error: The exception message, if processing raised.
    """

    index: int
    total: int
    pdf_path: Path
    result: CleanResult | None
    error: str | None = None


def process_folder(
    input_dir: Path, output_dir: Path, config: CleanConfig | None = None
) -> Iterator[BatchProgress]:
    """Clean every PDF in ``input_dir``, yielding progress as it goes.

    Args:
        input_dir: Folder containing source ``.pdf`` files.
        output_dir: Folder cleaned ``.txt`` files are written into.
        config: Cleaning options; defaults to :class:`CleanConfig`.

    Yields:
        A :class:`BatchProgress` update after each file is attempted.
    """
    config = config or CleanConfig()
    pdf_paths = sorted(input_dir.glob("*.pdf"))

    for index, pdf_path in enumerate(pdf_paths, start=1):
        try:
            result = process_pdf(pdf_path, output_dir, config)
            yield BatchProgress(index, len(pdf_paths), pdf_path, result)
        except Exception as error:  # noqa: BLE001 - surfaced to caller
            yield BatchProgress(
                index, len(pdf_paths), pdf_path, None, str(error)
            )
