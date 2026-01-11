# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# List of assets to include: (source_path, destination_folder)
# Note: For folders, PyInstaller handles ('folder', 'folder') differently on some platforms,
# ('folder/*', 'folder') is often safer for globbing.
added_files = [
    ('assets', 'assets'),
    ('levels', 'levels'),
    ('dialog_intro.xml', '.'),
]

# Platform-specific binaries or adjustments
binaries = []
if sys.platform.startswith('linux'):
    # Try to locate glfw libs in the environment
    binaries += [
        ('venv/lib/python3.13/site-packages/glfw/wayland/libglfw.so', '.'),
        ('venv/lib/python3.13/site-packages/glfw/x11/libglfw.so', '.')
    ]
elif sys.platform == 'win32':
    binaries += [('glwf3.dll', '.')]
elif sys.platform == 'darwin':
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=added_files,
    hiddenimports=['moderngl', 'skia', 'glfw', 'numpy', 'miniaudio', 'pygame'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='memory_parasite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/guide.png' if os.path.exists('assets/guide.png') else None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='MemoryParasite.app',
        icon='assets/guide.png' if os.path.exists('assets/guide.png') else None,
        bundle_identifier=None,
    )
