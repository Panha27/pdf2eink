@echo off
title Build MatePad PDF Converter
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.9+ from https://www.python.org/downloads/
  echo IMPORTANT: tick "Add python.exe to PATH" during install, then run this file again.
  pause
  exit /b 1
)

echo Installing build tools...
python -m pip install --upgrade pip pymupdf pyinstaller
if errorlevel 1 goto :fail

echo Building EXE...
python -m PyInstaller --onefile --windowed --clean --name MatePadPDF matepad_pdf_converter.py
if errorlevel 1 goto :fail

echo.
echo SUCCESS: dist\MatePadPDF.exe
echo Optional: open installer.iss with Inno Setup to make a Setup installer.
pause
exit /b 0

:fail
echo Build failed. Please check the messages above.
pause
exit /b 1
