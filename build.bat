@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo Installing dependencies...
pip install pyinstaller -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    exit /b 1
)

for %%f in (*.pyw) do (
    echo.
    echo Building %%~nf.exe from %%f...
    python -m PyInstaller --onefile --windowed --name %%~nf "%%f"
    if errorlevel 1 (
        echo Failed to build %%f
        exit /b 1
    )
)

echo.
echo Moving executables to %~dp0...
move /Y dist\*.exe "%~dp0" >nul
if errorlevel 1 (
    echo Failed to move executables.
    exit /b 1
)

echo.
echo Done. Executables are in %~dp0.
endlocal
