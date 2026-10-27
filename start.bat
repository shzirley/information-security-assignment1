@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
if errorlevel 1 goto use_python
py -3 launcher.py
if errorlevel 1 pause
exit /b
:use_python
python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.11 or newer and enable Add Python to PATH.
  pause
  exit /b 1
)
python launcher.py
if errorlevel 1 pause
