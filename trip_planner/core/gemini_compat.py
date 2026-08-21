"""
WHAT THIS FILE DOES
===================
Makes the agent architectures runnable on current Gemini models.

The problem
-----------
Google withdrew gemini-2.5-flash — the model every published measurement in this
project was produced on — from new API keys. Its replacements reject any request
whose message list ends with an assistant turn:

    400 INVALID_ARGUMENT
    "Requests ending with a model turn are not supported."

That is exactly the shape the agent framework's reasoning loop produces: the
agent writes a thought, the transcript is re-sent to decide the next step, and
the last entry is therefore the agent's own words. The three-agent architecture
never produces it, because it makes one request per step with no loop. So without
this shim the shipped path runs and the two six-agent architectures cannot run at
all — which means the comparison the dissertation rests on cannot be repeated.

What this does
--------------
Wraps the model client so that a request ending with an assistant turn gains a
short user turn before it is sent. Every other request passes through untouched.

Why this is honest
------------------
It changes the prompt, so it must be declared rather than hidden:

  * Only requests that would otherwise be REJECTED are altered. A request the
    provider accepts is passed through byte-for-byte.
  * The added turn is a minimal continuation cue. Providers that accept a
    trailing assistant turn treat it as an instruction to continue, so this
    makes the new model behave as the old one did rather than inventing new
    behaviour.
  * It is counted. The shim records how many requests it altered, so a run can
    report whether it was needed at all and how often.

Results produced with this shim active are NOT comparable to the recorded
gemini-2.5-flash results, and not because of the shim — the model is different.
Any re-measurement must re-run all four arms together.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# The model used when GEMINI_MODEL is not set.
#
# This lives here, once, and every caller reads it through model_string() below.
# It was previously typed into seven modules as "gemini/gemini-2.5-flash" — a
# model Google has since withdrawn from new API keys. Anyone who ran the project
# without a .env therefore got a 404 from every arm, which is the worst possible
# first impression and had nothing to do with their setup.
DEFAULT_MODEL = "gemini/gemini-3.6-flash"

# The model every published measurement in this project was FIRST produced on,
# before it was withdrawn. Kept because the documents have to be able to say what
# changed, not because anything still runs on it.
WITHDRAWN_MODEL = "gemini/gemini-2.5-flash"


def model_string() -> str:
    """The LiteLLM model string to use, honouring GEMINI_MODEL if it is set."""
    return os.getenv("GEMINI_MODEL") or DEFAULT_MODEL


def normalise_api_keys() -> bool:
    """
    Make Google's key available under both names it is known by.

    LiteLLM reads GEMINI_API_KEY for gemini/ models; other code and most
    documentation say GOOGLE_API_KEY. They are the same credential, and a .env in
    the wild carries either one. Copying in only one direction meant a .env
    holding just GEMINI_API_KEY was reported as having no key at all — a
    confusing way to fail when the key is sitting right there.

    Returns whether a key was found, so a caller can tell "normalised" from
    "there was nothing to normalise".
    """
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    if not key or key.startswith("your_"):
        return False
    os.environ["GOOGLE_API_KEY"] = key
    os.environ["GEMINI_API_KEY"] = key
    return True

# The cue appended when a request would otherwise be refused. Deliberately
# short and neutral: it must not steer the answer, only satisfy the API's
# requirement that a request end with a user turn.
CONTINUATION_CUE = "Continue."

_installed = False


class _Counter:
    """How often the shim was needed, so a run can report it rather than assume."""

    def __init__(self) -> None:
        self.requests = 0
        self.rewritten = 0

    def summary(self) -> Dict[str, Any]:
        return {
            "requests_seen": self.requests,
            "requests_rewritten": self.rewritten,
            "shim_was_needed": self.rewritten > 0,
        }

    def reset(self) -> None:
        self.requests = 0
        self.rewritten = 0


STATS = _Counter()


def _needs_rewrite(messages: Any) -> bool:
    if not isinstance(messages, list) or not messages:
        return False
    last = messages[-1]
    return isinstance(last, dict) and last.get("role") == "assistant"


def _rewrite(messages: List[dict]) -> List[dict]:
    return list(messages) + [{"role": "user", "content": CONTINUATION_CUE}]


def install() -> bool:
    """
    Wrap the model client's completion functions. Safe to call repeatedly.

    Returns True if the shim was installed, False if it could not be (the client
    is unavailable), so a caller can report the fact instead of assuming.
    """
    global _installed
    if _installed:
        return True
    try:
        import litellm
    except ImportError:  # pragma: no cover - litellm is a hard dependency
        logger.debug("litellm unavailable; Gemini message shim not installed")
        return False

    def wrap(original, is_async: bool):
        def sync_wrapper(*args, **kwargs):
            STATS.requests += 1
            messages = kwargs.get("messages")
            if _needs_rewrite(messages):
                kwargs["messages"] = _rewrite(messages)
                STATS.rewritten += 1
            return original(*args, **kwargs)

        async def async_wrapper(*args, **kwargs):
            STATS.requests += 1
            messages = kwargs.get("messages")
            if _needs_rewrite(messages):
                kwargs["messages"] = _rewrite(messages)
                STATS.rewritten += 1
            return await original(*args, **kwargs)

        return async_wrapper if is_async else sync_wrapper

    litellm.completion = wrap(litellm.completion, is_async=False)
    if hasattr(litellm, "acompletion"):
        litellm.acompletion = wrap(litellm.acompletion, is_async=True)

    _installed = True
    logger.debug("Gemini trailing-assistant-turn shim installed")
    return True
