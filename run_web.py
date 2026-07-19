"""
Web UI Entry Point for AI Trip Planner
Usage: python run_web.py
Opens Streamlit web interface at http://localhost:8501
"""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/ui/app.py"])
