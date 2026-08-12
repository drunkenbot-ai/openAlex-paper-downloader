"""PySide6 desktop GUI for running the paper-cleaning pipeline."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from paper_cleaner.batch import BatchProgress, process_folder
from paper_cleaner.config import CleanConfig


class CleaningWorker(QThread):
    """Runs :func:`process_folder` on a background thread."""

    progress = Signal(object)
    finished_all = Signal()

    def __init__(self, input_dir: Path, output_dir: Path) -> None:
        """Store the folders to process.

        Args:
            input_dir: Folder containing source PDFs.
            output_dir: Folder cleaned text files are written into.
        """
        super().__init__()
        self._input_dir = input_dir
        self._output_dir = output_dir

    def run(self) -> None:
        """Process the folder, emitting one signal per file."""
        for update in process_folder(
            self._input_dir, self._output_dir, CleanConfig()
        ):
            self.progress.emit(update)
        self.finished_all.emit()


class MainWindow(QMainWindow):
    """Simple window: pick a PDF folder, run cleanup, watch the log."""

    def __init__(self) -> None:
        """Build the window layout."""
        super().__init__()
        self.setWindowTitle("Paper Cleaner")
        self.resize(640, 480)

        self._input_dir: Path | None = None
        self._worker: CleaningWorker | None = None

        self._status_label = QLabel("Choose a folder of PDFs to clean.")
        self._choose_button = QPushButton("Choose Folder…")
        self._run_button = QPushButton("Run Cleanup")
        self._progress_bar = QProgressBar()
        self._log = QTextEdit(readOnly=True)

        self._run_button.setEnabled(False)
        self._choose_button.clicked.connect(self._choose_folder)
        self._run_button.clicked.connect(self._run_cleanup)

        layout = QVBoxLayout()
        layout.addWidget(self._status_label)
        layout.addWidget(self._choose_button)
        layout.addWidget(self._run_button)
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._log)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _choose_folder(self) -> None:
        """Prompt for the input folder and enable the run button."""
        chosen = QFileDialog.getExistingDirectory(self, "Select PDF Folder")
        if not chosen:
            return
        self._input_dir = Path(chosen)
        self._status_label.setText(f"Selected: {self._input_dir}")
        self._run_button.setEnabled(True)

    def _run_cleanup(self) -> None:
        """Start the background worker over the chosen folder."""
        if self._input_dir is None:
            return
        output_dir = self._input_dir / "cleaned_text"
        self._log.clear()
        self._run_button.setEnabled(False)

        self._worker = CleaningWorker(self._input_dir, output_dir)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_all.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, update: BatchProgress) -> None:
        """Log one processed file and advance the progress bar."""
        self._progress_bar.setMaximum(update.total)
        self._progress_bar.setValue(update.index)

        if update.error:
            self._log.append(f"ERROR  {update.pdf_path.name}: {update.error}")
        elif update.result and update.result.valid:
            words = update.result.stats.words
            self._log.append(f"OK     {update.pdf_path.name} ({words} words)")
        else:
            reasons = ", ".join(update.result.reject_reasons) if update.result else "?"
            self._log.append(f"REJECT {update.pdf_path.name}: {reasons}")

    def _on_finished(self) -> None:
        """Re-enable the run button once the batch completes."""
        self._status_label.setText("Done.")
        self._run_button.setEnabled(True)
