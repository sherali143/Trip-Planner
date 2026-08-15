@echo off
REM ===================================================================
REM  AI Trip Planner - one file that sets everything up and runs it.
REM
REM  Just double-click this file, or run:  run.bat
REM
REM  First run: creates the virtual environment, installs everything,
REM  and creates .env for your API keys. Later runs skip straight to
REM  the menu.
REM ===================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title AI Trip Planner

echo.
echo  ==================================================================
echo    AI TRIP PLANNER
echo    Multi-agent travel planning on MCP and a typed A2A protocol
echo  ==================================================================
echo.

REM ---------------------------------------------------------------- 1/4
REM Python must be present and recent enough. 3.10+ is required because
REM the code uses match-free but 3.10-era typing syntax throughout.
where python >nul 2>&1
if errorlevel 1 (
    echo  [X] Python is not installed, or not on PATH.
    echo.
    echo      Install Python 3.10 or newer from https://www.python.org/downloads/
    echo      During installation, TICK "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [1/4] Python %PYVER% found.

REM ---------------------------------------------------------------- 2/4
REM The virtual environment keeps this project's pinned dependencies
REM away from anything else on the machine.
if not exist ".venv\Scripts\python.exe" (
    echo  [2/4] Creating the virtual environment ^(one-off, ~20 seconds^)...
    python -m venv .venv
    if errorlevel 1 (
        echo  [X] Could not create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo  [2/4] Virtual environment already present.
)
set PY=.venv\Scripts\python.exe

REM ---------------------------------------------------------------- 3/4
REM Dependencies are PINNED in requirements.txt to the versions the
REM published results were produced with. A marker file records that the
REM install succeeded, so later runs do not reinstall every time.
if not exist ".venv\.installed" (
    echo  [3/4] Installing dependencies ^(one-off, 2-5 minutes^)...
    "%PY%" -m pip install --quiet --upgrade pip
    "%PY%" -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo  [X] Installation failed. Scroll up for the reason.
        pause
        exit /b 1
    )
    echo installed > ".venv\.installed"
    echo        Done.
) else (
    echo  [3/4] Dependencies already installed.
)

REM ---------------------------------------------------------------- 4/4
REM API keys. Everything except a live plan works without them, because
REM the recorded API responses in .api_cache are committed.
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo  [4/4] Created .env from the template.
    echo.
    echo        NOTE: .env has no API keys in it yet.
    echo        Options 3, 4, 5 and 6 below work fine without them.
    echo        Options 1 and 2 need keys - open .env in Notepad and paste
    echo        them in. See README.md for where to get each one.
    echo.
) else (
    echo  [4/4] .env found.
)

echo.
echo  Setup complete.
echo.

:menu
echo  ==================================================================
echo    WHAT WOULD YOU LIKE TO DO?
echo  ==================================================================
echo.
echo    NEEDS API KEYS
echo      1. Plan a trip in the browser        ^(Streamlit web app^)
echo      2. Plan a trip in this window        ^(command line^)
echo.
echo    FREE - no keys, no internet, replays recorded data
echo      3. Run the test suite
echo      4. Run the evaluation experiments    ^(protocol + budget gate^)
echo      5. Rebuild the figures               ^(8 diagrams, 6 charts^)
echo      6. Rebuild the dissertation          ^(report/*.docx^)
echo.
echo      7. Exit
echo.
set /p choice="   Enter a number (1-7): "
echo.

if "%choice%"=="1" goto web
if "%choice%"=="2" goto cli
if "%choice%"=="3" goto tests
if "%choice%"=="4" goto experiments
if "%choice%"=="5" goto figures
if "%choice%"=="6" goto report
if "%choice%"=="7" goto end
echo  Please enter a number from 1 to 7.
echo.
goto menu

:web
echo  Starting the web app. It opens at http://localhost:8501
echo  Press Ctrl+C in this window to stop it.
echo.
"%PY%" run_web.py
echo.
goto menu

:cli
echo  Starting the command-line planner.
echo.
"%PY%" run_cli.py
echo.
pause
goto menu

:tests
echo  Running the test suite...
echo.
"%PY%" -m pytest -q
echo.
pause
goto menu

:experiments
echo  Running the quota-free experiments. These touch no network and
echo  cost nothing, so they can be run as often as you like.
echo.
"%PY%" -m comparison.exp_protocol
echo.
"%PY%" -m comparison.exp_budget_gate
echo.
pause
goto menu

:figures
echo  Regenerating every figure from the measured results...
echo.
"%PY%" scripts/make_diagrams.py
"%PY%" scripts/make_charts.py
echo.
pause
goto menu

:report
echo  Rebuilding the dissertation. This regenerates the figures, runs the
echo  test suite, rebuilds the document and reports the word count.
echo.
"%PY%" -m report.build.build_report --figures
echo.
pause
goto menu

:end
echo  Goodbye.
echo.
endlocal
exit /b 0
