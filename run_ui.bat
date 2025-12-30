@echo off
echo ========================================
echo Installing Streamlit...
echo ========================================
pip install streamlit

echo.
echo ========================================
echo Starting AI Trip Planner UI...
echo ========================================
echo.
echo The browser will open automatically at http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

streamlit run app.py
