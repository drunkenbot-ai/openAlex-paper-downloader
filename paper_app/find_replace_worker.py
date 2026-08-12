"""Background worker applying find/replace across cleaned text files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from paper_app.text_replace import apply_replacement, compile_pattern


class FindReplaceWorker(QThread):
    """Runs a find/replace pass over one or more ``.txt`` files, saving each."""

    file_done = Signal(str, int)
    failed = Signal(str, str)
    finished_all = Signal(int, int)

    def __init__(
        self,
        files: list[Path],
        find_text: str,
        replace_text: str,
        use_regex: bool,
        case_sensitive: bool,
    ) -> None:
        """Store the target files and replacement settings.

        Args:
            files: Cleaned ``.txt`` files to process.
            find_text: Pattern to search for.
            replace_text: Replacement text (regex backreferences honored
                when ``use_regex`` is True).
            use_regex: Whether ``find_text`` is a regular expression.
            case_sensitive: Whether matching should be case sensitive.
        """
        super().__init__()
        self._files = files
        self._find_text = find_text
        self._replace_text = replace_text
        self._use_regex = use_regex
        self._case_sensitive = case_sensitive

    def run(self) -> None:
        """Compile the pattern once, then replace-and-save each file."""
        try:
            compiled = compile_pattern(
                self._find_text, self._use_regex, self._case_sensitive
            )
        except Exception as error:  # noqa: BLE001 - surfaced to the UI
            self.failed.emit("", str(error))
            self.finished_all.emit(0, 0)
            return

        files_changed = 0
        total_replacements = 0

        for path in self._files:
            try:
                text = path.read_text(encoding="utf-8")
                new_text, count = apply_replacement(
                    text, compiled, self._replace_text, self._use_regex
                )
                if count:
                    path.write_text(new_text, encoding="utf-8", newline="\n")
                    files_changed += 1
                    total_replacements += count
                self.file_done.emit(path.name, count)
            except Exception as error:  # noqa: BLE001 - surfaced to the UI
                self.failed.emit(path.name, str(error))

        self.finished_all.emit(files_changed, total_replacements)
