# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Research Paper Corpus Builder GUI.

Build with:
    pyinstaller build.spec

Produces a single-file executable on every platform, plus a proper
``.app`` bundle on macOS. Icon selection is automatic per OS.
"""

import sys
from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH)
assets_dir = project_root / "paper_app" / "assets"

if sys.platform == "win32":
    icon_path = assets_dir / "app_icon.ico"
elif sys.platform == "darwin":
    icon_path = assets_dir / "app_icon.icns"
else:
    icon_path = None
icon = str(icon_path) if icon_path and icon_path.exists() else None

a = Analysis(
    ["paper_app/main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(assets_dir), "paper_app/assets")],
    hiddenimports=[
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PaperCorpusBuilder",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="PaperCorpusBuilder.app",
        icon=icon,
        bundle_identifier="com.drunkenbot.papercorpusbuilder",
    )
