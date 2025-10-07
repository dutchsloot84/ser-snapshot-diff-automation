# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller spec for the SER Diff GUI one-file binary."""

import os

block_cipher = None

app_name = os.environ.get("SERDIFF_GUI_NAME", "ser-diff-gui")

a = Analysis(
    ["src/serdiff/gui_runner.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "serdiff.cli",
        "serdiff.config",
        "serdiff.diff",
        "serdiff.detect",
        "serdiff.report_html",
        "serdiff.report_xlsx",
        "openpyxl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

