"""
AI Trip Planner.

Two things are applied on import, so that no entry point — CLI, Streamlit,
evaluation runner or demo script — has to remember to do them.

1. Logging defaults, so nothing can accidentally print the Gemini API key. It
   travels as a URL query parameter and is logged by the HTTP client at INFO
   level. See trip_planner/core/log_setup.py; override with
   TRIP_PLANNER_VERBOSE=1.

2. Google's API key copied to both names it is known by. LiteLLM reads
   GEMINI_API_KEY; most of the documentation says GOOGLE_API_KEY. They are the
   same credential, and a .env carrying only one used to look like a .env
   carrying none.

3. The Gemini message-shape shim, so the agent architectures can run on current
   models. Google withdrew the model this project's results were measured on,
   and its replacements reject requests ending with an assistant turn — which is
   exactly what a reasoning loop produces. See
   trip_planner/core/gemini_compat.py, which explains what it changes and counts
   how often it was needed.
"""

from trip_planner.core.gemini_compat import install as _install_gemini_shim
from trip_planner.core.gemini_compat import normalise_api_keys
from trip_planner.core.log_setup import configure_logging

configure_logging()
normalise_api_keys()
_install_gemini_shim()
