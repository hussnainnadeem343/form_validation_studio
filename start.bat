@echo off
title QA Form Validation Studio

echo =====================================================================
echo              QA FORM VALIDATION AUTOMATION STUDIO
echo           Zero-Code Web Form Testing for QA Engineers
echo =====================================================================
echo.

cd /d "%~dp0"

:: 1. Detect Python
set "PYTHON_EXE="
where py.exe >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py"
    goto :PYTHON_FOUND
)

where python.exe >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

echo [ERROR] Python was not found on your system!
echo Please install Python 3.11+ from https://www.python.org/downloads/
echo Make sure to check the box "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:PYTHON_FOUND
echo [INFO] Using Python: %PYTHON_EXE%

:: 2. Check if required packages already exist in current Python
%PYTHON_EXE% -c "import playwright, yaml, faker" >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Framework dependencies are verified and ready.
    goto :LAUNCH
)

:: 3. Setup Virtual Environment if packages are not in global Python
echo [INFO] Framework packages not detected globally. Setting up environment...
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment (.venv)...
    %PYTHON_EXE% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
set "PYTHON_EXE=python"

echo [INFO] Installing dependencies from requirements.txt...
%PYTHON_EXE% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Please check your internet connection.
    pause
    exit /b 1
)

echo [INFO] Ensuring Chromium browser is installed for automation...
%PYTHON_EXE% -m playwright install chromium
if errorlevel 1 (
    echo [WARNING] Playwright browser setup returned a warning, attempting to proceed...
)

:LAUNCH
echo.
echo =====================================================================
echo  [READY] QA Studio is launching...
echo  Dashboard URL: http://127.0.0.1:5000
echo  Please keep this terminal window open while testing.
echo =====================================================================
echo.

%PYTHON_EXE% web_ui\server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server encountered an unexpected issue.
)

pause
