@echo off
setlocal
cd /d "%~dp0"

echo This builds OptionsController.exe (dist\OptionsController.exe).
echo Run this once per machine you want to build on. End users just get the .exe.
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.12+ from python.org and try again.
    pause
    exit /b 1
)

if not exist ".venv-build" (
    echo Creating build virtual environment...
    python -m venv .venv-build
)

call .venv-build\Scripts\activate.bat

echo Installing build dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements-build.txt

echo Building OptionsController.exe with PyInstaller...
python -m PyInstaller --noconfirm --clean desktop\options_controller.spec

if exist "dist\OptionsController.exe" (
    echo.
    echo Build succeeded: dist\OptionsController.exe
    echo Copy that single file anywhere and double-click to run -- no Python install needed.
) else (
    echo.
    echo Build did not produce dist\OptionsController.exe -- check the PyInstaller output above.
)

pause
