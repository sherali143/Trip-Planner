"""
AI Trip Planner.

Logging defaults are applied on import so that no entry point — CLI, Streamlit,
comparison runner or demo script — can accidentally print the Gemini API key,
which travels as a URL query parameter and is logged by httpx at INFO level.
See trip_planner/core/log_setup.py; override with TRIP_PLANNER_VERBOSE=1.
"""

from trip_planner.core.log_setup import configure_logging

configure_logging()
