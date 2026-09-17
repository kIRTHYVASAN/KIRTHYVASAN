# PyInstaller spec for the Options Controller desktop app.
# Build on Windows with:  pyinstaller desktop/options_controller.spec
#
# Streamlit needs its static/frontend assets and a handful of dynamically
# imported modules included explicitly, or the frozen exe boots to a blank
# window / import error.
from pathlib import Path

import streamlit
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path.cwd()
STREAMLIT_DIR = Path(streamlit.__file__).parent

datas = [
    (str(ROOT / "app.py"), "."),
    (str(ROOT / "assets" / "icon.ico"), "assets"),
    (str(STREAMLIT_DIR / "static"), "streamlit/static"),
    (str(STREAMLIT_DIR / "runtime"), "streamlit/runtime"),
]
datas += collect_data_files("streamlit")

hidden_imports = (
    collect_submodules("streamlit")
    + collect_submodules("plotly")
    + [
        "pyotp", "growwapi", "keyring",
        "keyring.backends", "keyring.backends.Windows",
        "plyer.platforms.win.notification",
        "streamlit_autorefresh",
    ]
)

a = Analysis(
    [str(ROOT / "desktop" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

# Onefile build: everything bundled directly into the EXE.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="OptionsController",
    icon=str(ROOT / "assets" / "icon.ico"),
    console=False,
    upx=False,
)
