"""Starts the web page. Run: python run_web.py"""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run",
                    "trip_planner/frontend/app.py"])
