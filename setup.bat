@echo off
setlocal
title AI Trip Planner - Setup
cd /d "%~dp0"

echo ============================================================
echo   AI Trip Planner  -  Setup
echo ============================================================
echo.

:: ---------------------------------------------------------- Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH. Install Python 3.11+ and re-run.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [1/5] Python %PYVER% detected

:: ---------------------------------------------------------- venv
if not exist ".venv" (
    echo [2/5] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/5] Virtual environment already present
)

:: ---------------------------------------------------------- dependencies
echo [3/5] Installing dependencies ^(this can take a few minutes^)...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
python -m pip install --prefer-binary -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. Re-run without --quiet to see why:
    echo         .venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)
echo       Dependencies installed from pinned requirements.txt

:: ---------------------------------------------------------- .env
if not exist ".env" (
    echo [4/5] Creating .env from the template...
    copy /y ".env.example" ".env" >nul
    echo.
    echo       ------------------------------------------------------------
    echo       ACTION REQUIRED: open .env and paste in your API keys.
    echo.
    echo         GOOGLE_API_KEY / GEMINI_API_KEY   https://aistudio.google.com/apikey
    echo         SERPER_API_KEY                    https://serper.dev
    echo         RAPIDAPI_KEY                      https://rapidapi.com
    echo                                           subscribe to BOTH:
    echo                                             fly-scraper    ^(flights^)
    echo                                             booking-com15  ^(hotels^)
    echo       ------------------------------------------------------------
    echo.
    echo       The evaluation can be re-run WITHOUT any keys - recorded API
    echo       responses are committed. See the replay command below.
    echo.
) else (
    echo [4/5] .env already present - not overwritten
)

:: ---------------------------------------------------------- verify
echo [5/5] Verifying the installation...
python -m pytest -q
if errorlevel 1 (
    echo.
    echo [WARNING] Some tests failed. The install completed, but check the output above.
) else (
    echo       All tests passed.
)

echo.
echo ============================================================
echo   Setup complete
echo ============================================================
echo.
echo   Activate the environment first, in every new terminal:
echo       .venv\Scripts\activate
echo.
echo   Then:
echo.
echo     Plan a trip ^(terminal^)      python run_cli.py
echo     Plan a trip ^(web^)           python run_web.py
echo     Demo all four approaches    python demos\demo_comparison.py
echo     Run the evaluation          python -m comparison.run_comparison
echo     Run the tests               python -m pytest
echo.
echo   IMPORTANT - the flight and hotel APIs allow only 30 and 50 calls
echo   PER MONTH. Replay the recorded responses instead of spending them:
echo.
echo       set TRIP_PLANNER_API_MODE=replay
echo.
echo   And cap live usage whenever you do go live:
echo.
echo       set TRIP_PLANNER_MAX_LIVE_CALLS=10
echo.
pause
endlocal
