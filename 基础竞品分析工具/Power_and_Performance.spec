# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Power_and_Performance.py'],
    pathex=[],
    binaries=[],
    datas=[('竞品分析基本测试项模板.xlsx', '.')],
    hiddenimports=[
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_tkagg',
        'openpyxl', 'pandas', 'PIL', 'PIL.Image',
        'GET_Data', 'GET_Data_HD_Tune',
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Power_and_Performance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
