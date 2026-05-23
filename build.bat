@echo off
REM ════════════════════════════════════════════════════════════════════════
REM  PDF Compressor — Build Script
REM  Builds a standalone Windows .exe using PyInstaller
REM ════════════════════════════════════════════════════════════════════════

setlocal EnableDelayedExpansion

echo.
echo  ██████╗ ██████╗ ███████╗
echo  ██╔══██╗██╔══██╗██╔════╝
echo  ██████╔╝██║  ██║█████╗
echo  ██╔═══╝ ██║  ██║██╔══╝
echo  ██║     ██████╔╝██║
echo  ╚═╝     ╚═════╝ ╚═╝
echo.
echo  PDF Compressor ^| Build Script
echo  ════════════════════════════════
echo.

REM ── Check Python ─────────────────────────────────────────────────────
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Python not found. Install Python 3.11+ from https://python.org
    exit /b 1
)

python --version
echo.

REM ── Check pip ────────────────────────────────────────────────────────
where pip >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] pip not found. Re-install Python with pip included.
    exit /b 1
)

REM ── Install dependencies ─────────────────────────────────────────────
echo  [1/4] Installing Python dependencies...
pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Dependency installation failed.
    exit /b 1
)
echo  [OK] Dependencies installed.
echo.

REM ── Check PyInstaller ────────────────────────────────────────────────
echo  [2/4] Verifying PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  Installing PyInstaller...
    pip install pyinstaller --quiet
)
echo  [OK] PyInstaller ready.
echo.

REM ── Clean previous build ─────────────────────────────────────────────
echo  [3/4] Cleaning previous build...
if exist dist\pdf_compressor.exe del /f /q dist\pdf_compressor.exe
if exist build rmdir /s /q build
if exist pdf_compressor.spec del /f /q pdf_compressor.spec
echo  [OK] Clean complete.
echo.

REM ── Build EXE ────────────────────────────────────────────────────────
echo  [4/4] Building standalone EXE...
echo.

pyinstaller ^
    --onefile ^
    --name pdf_compressor ^
    --console ^
    --clean ^
    --add-data "compressor;compressor" ^
    --hidden-import pikepdf ^
    --hidden-import fitz ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageFilter ^
    --collect-all pikepdf ^
    --collect-all fitz ^
    main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] PyInstaller build failed.
    exit /b 1
)

echo.
echo  ════════════════════════════════════════════════════════════════════
echo  [SUCCESS] Build complete!
echo.
echo  Executable: dist\pdf_compressor.exe
echo.
echo  Usage examples:
echo    dist\pdf_compressor.exe compress input.pdf --preset ultra
echo    dist\pdf_compressor.exe batch .\pdfs --preset extreme
echo    dist\pdf_compressor.exe presets
echo  ════════════════════════════════════════════════════════════════════
echo.

endlocal
