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

REM The comment above said "3.10+ is required" and nothing checked it, so a
REM Python 3.9 user got a SyntaxError from a type annotation several minutes into
REM the install and no clue why. Checked here instead.
python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,10) else 1)"
if errorlevel 1 (
    echo.
    echo  [X] Python %PYVER% is too old. This project needs 3.10 or newer.
    echo      Install from https://www.python.org/downloads/ and TICK
    echo      "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Upper bound is a WARNING, not a stop. requirements.txt is pinned to the exact
REM versions the published results were produced with, and some of those pins
REM predate the newest interpreters, so pip may fail to build a wheel. That is a
REM dependency problem, not a code problem, and naming it here saves an hour of
REM reading a compiler traceback. The evaluation was produced and verified on
REM 3.11.
python -c "import sys; sys.exit(1 if sys.version_info[:2] > (3,12) else 0)"
if errorlevel 1 (
    echo.
    echo  [!] Python %PYVER% is newer than this project was tested on.
    echo      Dependencies are pinned to the versions the published results were
    echo      measured with, and pip may fail to build one of them on a very new
    echo      interpreter.
    echo.
    echo      If the install fails, install Python 3.11 alongside this one and
    echo      run:   py -3.11 -m venv .venv
    echo      then start this script again.
    echo.
    set /p ignore="   Press Enter to continue anyway: "
    echo.
)

REM Windows refuses paths longer than 260 characters unless long-path support
REM is enabled. Installing creates deeply nested files inside .venv, so if this
REM folder already sits deep the install fails with a confusing
REM "No such file or directory" OSError that reads like a corrupt download.
REM Verified: a clean install from a short path succeeds and all tests pass; the
REM same install from a deeply nested path fails on a jedi stub file. Checked
REM here so the cause is named before it costs anyone an afternoon.
python -c "import os,sys; sys.exit(1 if len(os.path.abspath('.'))>90 else 0)"
if errorlevel 1 (
    echo.
    echo  [!] WARNING: this folder is nested deeply:
    echo      %CD%
    echo.
    echo      Windows limits paths to 260 characters and the install creates
    echo      long paths inside .venv, so it may fail with a confusing
    echo      "No such file or directory" error.
    echo.
    echo      FIX: move this whole folder somewhere short, such as
    echo           C:\trip_planner
    echo.
    set /p ignore="   Press Enter to try anyway, or close this window to move it: "
    echo.
)

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
    echo        Options 1 to 11 below work fine without them.
    echo        Only options 12 and 13 need keys - open .env in Notepad and
    echo        paste them in. See README.md for where to get each one.
    echo.
) else (
    echo  [4/4] .env found.
)

REM ---------------------------------------------------------------- 5/5
REM One self-check, so a broken install is reported here rather than inside
REM whichever menu option happens to be chosen first.
echo  [5/5] Checking the install...
REM Every third-party module the project imports, not a sample of them. This
REM checked six of eleven, so a failed python-pptx install passed setup and
REM then broke the slides option several menus later.
"%PY%" -c "import crewai, litellm, streamlit, matplotlib, docx, pptx, dotenv, requests, pydantic, mcp, pytest" 2>nul
if errorlevel 1 (
    echo.
    echo  [X] Some dependencies are missing. Delete the .venv folder and run
    echo      this file again to reinstall from scratch.
    echo.
    pause
    exit /b 1
)
"%PY%" -c "import sys; sys.path.insert(0,'.'); import trip_planner.evaluation.measured as m; m.results()" 2>nul
if errorlevel 1 (
    echo        WARNING: measured results are missing. Demos and the report
    echo        need trip_planner/evaluation/results/ - check the folder was copied.
) else (
    echo        Everything present.
)

echo.
echo  Setup complete.
echo.

:menu
echo  ==================================================================
echo    WHAT WOULD YOU LIKE TO DO?
echo  ==================================================================
echo.
echo    NEW HERE? Read PROJECT_OVERVIEW.docx first - six pages, plain English.
echo.
echo    DEMONSTRATIONS - free, no keys, no internet, no quota
echo      1. Compare all four approaches       ^(show this first^)
echo      2. Approach A - single LLM, no tools
echo      3. Approach B - six agents, naive
echo      4. Approach C - six agents, tuned
echo      5. Approach D - three agents, direct ^(what ships^)
echo.
echo    THE PROJECT - free
echo      6. Run the test suite
echo      7. Run the evaluation experiments    ^(protocol + budget gate^)
echo      8. Rebuild the figures               ^(8 diagrams, 6 charts^)
echo      9. Rebuild the dissertation          ^(report/*.docx^)
echo     10. Rebuild the project overview      ^(PROJECT_OVERVIEW.docx^)
echo     11. Rebuild the viva presentation     ^(CMP7200_Viva_Presentation.pptx^)
echo.
echo    PLAN A REAL TRIP - needs API keys in .env
echo     12. In the browser                    ^(web app^)
echo     13. In this window                    ^(command line^)
echo.
echo     14. Exit
echo.
set /p choice="   Enter a number (1-14): "
echo.

if "%choice%"=="1"  goto demo_all
if "%choice%"=="2"  goto demo_a
if "%choice%"=="3"  goto demo_b
if "%choice%"=="4"  goto demo_c
if "%choice%"=="5"  goto demo_d
if "%choice%"=="6"  goto tests
if "%choice%"=="7"  goto experiments
if "%choice%"=="8"  goto figures
if "%choice%"=="9"  goto report
if "%choice%"=="10" goto overview
if "%choice%"=="11" goto deck
if "%choice%"=="12" goto web
if "%choice%"=="13" goto cli
if "%choice%"=="14" goto end
echo  Please enter a number from 1 to 14.
echo.
goto menu

:demo_all
"%PY%" trip_planner/demos/compare_all_approaches.py
echo.
pause
goto menu

:demo_a
"%PY%" trip_planner/demos/approach_a_single_llm.py
echo.
pause
goto menu

:demo_b
"%PY%" trip_planner/demos/approach_b_six_agent_naive.py
echo.
pause
goto menu

:demo_c
"%PY%" trip_planner/demos/approach_c_six_agent_tuned.py
echo.
pause
goto menu

:demo_d
"%PY%" trip_planner/demos/approach_d_three_agent_direct.py
echo.
pause
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
"%PY%" -m trip_planner.evaluation.exp_protocol
echo.
"%PY%" -m trip_planner.evaluation.exp_budget_gate
echo.
pause
goto menu

:figures
echo  Regenerating every figure from the measured results...
echo.
"%PY%" submission/build/make_diagrams.py
"%PY%" submission/build/make_charts.py
echo.
pause
goto menu

:report
echo  Rebuilding the dissertation. This regenerates the figures, runs the
echo  test suite, rebuilds the document and reports the word count.
echo.
"%PY%" -m submission.build.build_dissertation --figures
echo.
pause
goto menu

:overview
echo  Rebuilding PROJECT_OVERVIEW.docx - the plain-English guide to this
echo  project. Every number in it is read from the measured results, so it
echo  stays correct after the experiments are re-run.
echo.
"%PY%" submission/build/make_handover.py
echo.
pause
goto menu

:deck
echo  Rebuilding CMP7200_Viva_Presentation.pptx - the viva slides. Every
echo  number on a slide is read from the measured results, and the detail
echo  for each one is in that slide's speaker notes.
echo.
"%PY%" submission/build/make_viva_deck.py
echo.
pause
goto menu

:end
echo  Goodbye.
echo.
endlocal
exit /b 0
