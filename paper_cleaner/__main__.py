"""Entry point: ``python -m paper_cleaner [input_dir] [output_dir]``.

With no arguments, launches the PySide6 GUI. With two path arguments,
runs the cleaning pipeline over a folder from the command line.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _run_cli(input_dir: Path, output_dir: Path) -> None:
    """Clean every PDF in ``input_dir`` and print a one-line summary each.

    Args:
        input_dir: Folder containing source ``.pdf`` files.
        output_dir: Folder cleaned ``.txt`` files are written into.
    """
    from paper_cleaner.batch import process_folder

    for update in process_folder(input_dir, output_dir):
        if update.error:
            print(f"ERROR  {update.pdf_path.name}: {update.error}")
        elif update.result and update.result.valid:
            print(f"OK     {update.pdf_path.name} ({update.result.stats.words} words)")
        else:
            reasons = ", ".join(update.result.reject_reasons) if update.result else "?"
            print(f"REJECT {update.pdf_path.name}: {reasons}")


def _run_gui() -> None:
    """Launch the PySide6 GUI window."""
    from PySide6.QtWidgets import QApplication

    from paper_cleaner.gui import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def main() -> None:
    """Dispatch to the CLI or GUI based on argument count."""
    if len(sys.argv) == 3:
        _run_cli(Path(sys.argv[1]), Path(sys.argv[2]))
    else:
        _run_gui()


if __name__ == "__main__":
    main()
