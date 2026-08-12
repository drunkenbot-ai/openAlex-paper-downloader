"""Entry point: ``python -m paper_app`` launches the combined GUI."""

from __future__ import annotations

import sys
from pathlib import Path

_APP_USER_MODEL_ID = "DrunkenBot.PaperCorpusBuilder.GUI.1"


def _assets_dir() -> Path:
    """Return the folder ``app_icon.*`` lives in, in source or frozen builds.

    PyInstaller extracts bundled data files to a temp folder exposed as
    ``sys._MEIPASS``; a plain ``python -m paper_app`` run instead resolves
    the assets folder relative to this file.

    Returns:
        The folder containing the app icon files.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "paper_app" / "assets"
    return Path(__file__).parent / "assets"


_ASSETS_DIR = _assets_dir()
# .ico carries multiple embedded resolutions, which Windows' taskbar and
# Alt-Tab switcher need to render a crisp icon; a single-resolution .png
# is fine for the title bar but often shows blank/blurry on the taskbar.
_ICON_PATH = _ASSETS_DIR / "app_icon.ico"
if not _ICON_PATH.exists():
    _ICON_PATH = _ASSETS_DIR / "app_icon.png"


def _set_windows_app_user_model_id() -> None:
    """Give the app its own taskbar identity on Windows.

    Without this, Windows groups the window under the generic Python
    icon instead of the app's own icon. No-op on non-Windows platforms.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            _APP_USER_MODEL_ID
        )
    except Exception:  # noqa: BLE001 - purely cosmetic, never fatal
        pass


def _force_windows_icon(window) -> None:
    """Directly set the HWND's big/small icons via WinAPI as a fallback.

    Qt normally sets these through ``setWindowIcon``, but some Windows
    setups (notably running via ``python.exe`` instead of a packaged
    ``.exe``) don't reliably propagate that to the taskbar. Sending
    ``WM_SETICON`` directly to the native window handle is a stronger
    guarantee. No-op on non-Windows platforms or if anything fails.

    Args:
        window: The top-level window to set icons on.
    """
    if sys.platform != "win32" or not _ICON_PATH.exists():
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = int(window.winId())
        image_icon, lr_loadfromfile = 1, 0x00000010
        big_icon = user32.LoadImageW(0, str(_ICON_PATH), image_icon, 32, 32, lr_loadfromfile)
        small_icon = user32.LoadImageW(0, str(_ICON_PATH), image_icon, 16, 16, lr_loadfromfile)
        wm_seticon, icon_big, icon_small = 0x0080, 1, 0
        if big_icon:
            user32.SendMessageW(hwnd, wm_seticon, icon_big, big_icon)
        if small_icon:
            user32.SendMessageW(hwnd, wm_seticon, icon_small, small_icon)
    except Exception:  # noqa: BLE001 - purely cosmetic, never fatal
        pass


def main() -> None:
    """Start the Qt application and show the main window."""
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from paper_app.main_window import MainWindow
    from paper_app.settings import APPLICATION_NAME, ORGANIZATION_NAME

    _set_windows_app_user_model_id()

    app = QApplication(sys.argv)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setApplicationName(APPLICATION_NAME)

    if _ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(_ICON_PATH)))

    window = MainWindow()
    if _ICON_PATH.exists():
        window.setWindowIcon(QIcon(str(_ICON_PATH)))
    window.show()
    _force_windows_icon(window)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
