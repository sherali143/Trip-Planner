@echo off
title Trip Planner Setup
echo ========================================
echo  Trip Planner - Quick Setup
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)
echo [OK] Python detected

:: Create virtual environment
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

:: Activate and install dependencies
echo Installing dependencies...
call .venv\Scripts\activate.bat && pip install --prefer-binary -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)
echo [OK] Dependencies installed

:: Install crewai[google-genai] extra
echo Installing CrewAI Google GenAI support...
call .venv\Scripts\activate.bat && pip install "crewai[google-genai]" >nul 2>&1
echo [OK] CrewAI Google GenAI support installed

:: Check .env
if not exist ".env" (
    echo.
    echo [ACTION REQUIRED] Create a .env file with your API keys
    echo.
    echo Copy this into .env:
    echo ----------------------------------------
    echo GOOGLE_API_KEY=your_gemini_api_key_here
    echo GEMINI_API_KEY=your_gemini_api_key_here
    echo SERPER_API_KEY=your_serper_api_key_here
    echo RAPIDAPI_KEY=your_rapidapi_key_here
    echo GEMINI_MODEL=gemini/gemini-2.5-flash
    echo ----------------------------------------
    echo.
    echo Get keys from:
    echo   Gemini: https://aistudio.google.com/apikey
    echo   Serper: https://serper.dev
    echo   RapidAPI: https://rapidapi.com
    echo.
    pause
    exit /b 1
)
echo [OK] .env file found

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Run these demos:
echo   python demo_6agent_explained.py  - 6-Agent architecture (explained)
echo   python demo_3agent_explained.py  - 3-Agent architecture (explained)
echo   python demo_comparison.py        - Side-by-side comparison
echo   python run_6agent.py             - 6-Agent live execution
echo   python run_3agent.py             - 3-Agent live execution
echo.
pause
