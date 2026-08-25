"""
Package setup, run once on import.

Quiets the third-party loggers that would otherwise print the model API key,
and copies the Gemini key to both of the names the libraries look for.
"""

from trip_planner.core.gemini_compat import install as _install_gemini_shim
from trip_planner.core.gemini_compat import normalise_api_keys
from trip_planner.core.log_setup import configure_logging

configure_logging()
normalise_api_keys()
_install_gemini_shim()
