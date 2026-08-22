"""
Logging defaults — primarily to keep API keys out of the console.

Why this exists
---------------
Gemini is called over a URL that carries the key as a query parameter, and
httpx logs every request line at INFO. With INFO enabled (CrewAI/LiteLLM turn
it on), a normal run prints:

    INFO:httpx:HTTP Request: POST
    https://generativelanguage.googleapis.com/v1beta/models/...:generateContent?key=AIzaSy... "HTTP/1.1 200 OK"

— the live API key, in plaintext, in output that gets pasted into terminals,
screenshots, CI logs and handover notes. RapidAPI keys travel in headers rather
than URLs so they do not leak this way, but the Gemini one does.

This raises the level of the third-party loggers responsible. It deliberately
does not call basicConfig or touch this project's own loggers, so application
logging is unaffected.
"""

import io
import logging
import os

# Loggers that emit full request URLs or otherwise very chatty third-party noise.
_NOISY = (
    "httpx",           # logs the Gemini URL, key included
    "httpcore",
    "LiteLLM",
    "litellm",
    "openai",
    "urllib3",
    # The agent framework and its tracing. "Overriding of current TracerProvider
    # is not allowed" appears mid-run and tells the reader nothing they can act on.
    "opentelemetry",
    "opentelemetry.trace",
    "crewai",
    "chromadb",
    # Our own protocol layer. It logs every message twice at INFO — once on
    # enqueue and once on send — and the orchestrator then prints the same
    # message a third time in a form a person can read. Three lines per message
    # buried the parts of the run that matter. The log is still there at DEBUG,
    # which is where an audit trail belongs.
    "trip_planner.comms.protocol",
)


def configure_logging(level: int = logging.WARNING) -> None:
    """
    Quieten third-party loggers that would otherwise print secrets.

    Set TRIP_PLANNER_VERBOSE=1 to skip this when genuinely debugging HTTP —
    but be aware the console will then contain the Gemini API key.
    """
    if os.getenv("TRIP_PLANNER_VERBOSE", "").strip() in ("1", "true", "yes"):
        return

    for name in _NOISY:
        logging.getLogger(name).setLevel(level)

    try:
        import litellm
        litellm.suppress_debug_info = True
        # LiteLLM re-enables INFO on its own logger during import in some
        # versions; pin it back down after the module is loaded.
        logging.getLogger("LiteLLM").setLevel(level)
    except Exception:  # pragma: no cover - litellm always present in practice
        pass


class TeeStream(io.StringIO):
    """
    Collect what a run prints, and let it reach the real console as well.

    The web interface captures the run's narration so it can be shown on the
    page, and `redirect_stdout` at a plain StringIO does exactly that and nothing
    more: the four steps, the route, the budget and what each search returned all
    went into the page, and the terminal running `streamlit run` stayed silent for
    the whole plan. A demonstration is usually watched from that console.

    So this is a StringIO that also forwards. `getvalue()` still returns
    everything for the page.

    Mirroring is deliberately unable to break the run. A Windows console on a
    legacy code page raises UnicodeEncodeError on the arrows and symbols in the
    A2A summary — losing a line of narration is not a reason to lose a plan, and
    that exact failure has already cost one run in this project when a `→` was
    printed from inside the flight call.

    Lives here rather than in the interface because a Streamlit script runs on
    import: anything importing it from there would draw a whole page as a side
    effect, which is how six page tests were once broken by an import.
    """

    def __init__(self, mirror):
        super().__init__()
        self._mirror = mirror

    def write(self, text):
        try:
            self._mirror.write(text)
            self._mirror.flush()
        except Exception:                      # noqa: BLE001 - narration only
            pass
        return super().write(text)
