"""Extract per-page text from a PDF file."""

from __future__ import annotations

from pathlib import Path


def extract_pdf_pages(pdf_path: Path) -> list[list[str]]:
    """Extract text from a PDF, one list of lines per page.

    Args:
        pdf_path: Path to the source PDF.

    Returns:
        A list with one entry per page; each entry is the list of raw
        text lines PyMuPDF extracted for that page.

    Raises:
        ValueError: If no pages could be read from the file.
    """
    import fitz  # PyMuPDF, imported lazily so the GUI can start without it.

    pages: list[list[str]] = []
    document = fitz.open(pdf_path)
    try:
        for page in document:
            pages.append(page.get_text("text").splitlines())
    finally:
        document.close()

    if not pages:
        raise ValueError(f"No pages extracted from {pdf_path.name}")
    return pages
