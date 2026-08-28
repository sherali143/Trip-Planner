"""
Finds the sections and the days inside a finished plan.

A plan is about 24,000 characters, so the page shows it in parts rather than
as one long column. The structure is read from the plan, not assumed, because
the heading style varies between runs.

Imports no Streamlit, so importing this does not draw a page.
"""

from __future__ import annotations

import re

# The words in a heading that place a section under a tab, in MATCHING order,
# which is not the reading order. The specific categories are tested first
# because the generic ones would steal from them: "FLIGHT OPTIONS ANALYSIS &
# RECOMMENDATIONS" contains "recommendation", and would land in Overview if
# Overview were tested first. Budget precedes the day rules for the same reason,
# so "DAILY BUDGET BREAKDOWN" is a budget section rather than a day.
MATCH_RULES = [
    ("Flights",    ("flight",)),
    ("Hotels",     ("hotel", "accommodation", "where to stay")),
    ("Budget",     ("budget", "cost")),
    ("Day by day", ("day-by-day", "day by day", "daily", "itinerary")),
    ("Tips",       ("tip", "knowledge", "practical", "advice", "packing")),
    ("Overview",   ("summary", "overview", "expert", "recommendation",
                    "combination", "at a glance")),
]

# The order they are shown in, which is how someone reads a plan.
DISPLAY_ORDER = ["Overview", "Flights", "Hotels", "Day by day", "Budget",
                 "Tips", "More"]

MAX_DAY_LABEL = 72          # Streamlit renders this in an expander header.

# ---------------------------------------------------------------------------
# Progress: seven named steps, built from what the orchestrator reports
#
# The orchestrator reports four phases, and inside the third it reports one line
# per search. Showing four rows hid the interesting part — three of the four
# searches happen inside one of them — so the rows are those reports spread out
# rather than a different account of the run.
# ---------------------------------------------------------------------------
STEPS = [
    ("Conversation",  "Collecting the details the plan needs"),
    ("Preferences",   "Reading the request and checking the budget is possible"),
    ("Flights",       "Finding real fares for the route and dates"),
    ("Hotels",        "Finding rooms inside the nightly budget"),
    ("Attractions",   "Finding things to do that match the interests"),
    ("Restaurants",   "Finding places to eat at the right price"),
    ("Itinerary",     "Arranging all of it into a day-by-day plan"),
]

PHASE_ROW = {1: 0, 2: 1, 3: 2, 4: 6}
SEARCH_ROW = {"flight": 2, "hotel": 3, "attraction": 4, "restaurant": 5}

IDLE, NOW, DONE = 0, 1, 2


def progress_states(events, conversation_done: bool = False):
    """
    Turn the run's reports into one state per step: IDLE, NOW or DONE.

    `events` is a list of ("phase", number) and ("search", label) pairs in the
    order they were reported. `conversation_done` marks the first row complete
    from the start, which is right on the web page: the form IS the conversation,
    so those questions were answered before the button was pressed. The
    orchestrator never announces phase 1 on that path, so without this the first
    row would sit unstarted for the whole run.

    A phase beginning marks every earlier row done, because the orchestrator only
    reports a phase when the one before it has returned. A search reports its own
    completion, so it marks its row done and starts the next.
    """
    states = [IDLE] * len(STEPS)
    if conversation_done:
        states[0] = DONE
    for kind, value in events or []:
        if kind == "phase":
            row = PHASE_ROW.get(value)
            if row is None:
                continue
            for earlier in range(row):
                states[earlier] = DONE
            if states[row] != DONE:
                states[row] = NOW
        elif kind == "search":
            row = SEARCH_ROW.get(value)
            if row is None:
                continue
            states[row] = DONE
            if row + 1 < len(STEPS) and states[row + 1] == IDLE:
                states[row + 1] = NOW
    return states


def section_level(itinerary: str) -> int:
    """
    Which heading level carries the sections — because it varies between runs.

    Two real plans from the same prompt: one used `#` eight times, once per
    section. The other used `#` once for the document title and `##` eight times
    for the sections. Splitting on `#` regardless turned the second into a single
    unrecognised blob, so the whole plan appeared under one tab called "More".

    The rule that separates them: a level used ONCE is a title, a level used more
    than once is a divider. So this returns the shallowest level appearing at
    least twice, and falls back to 1 when nothing repeats.
    """
    counts = {}
    for line in (itinerary or "").splitlines():
        match = re.match(r"^(#{1,4})\s+\S", line)
        if match:
            depth = len(match.group(1))
            counts[depth] = counts.get(depth, 0) + 1
    for depth in (1, 2, 3):
        if counts.get(depth, 0) >= 2:
            return depth
    return 1


def split_sections(itinerary: str):
    """
    Break the itinerary into (title, body) pairs at whatever level divides it.

    Anything before the first section heading — the document title, the dates,
    the headline budget — is returned with a title of None rather than dropped. A
    plan with no headings at all comes back as one (None, text) pair, which is
    the fallback that keeps an unexpectedly-shaped plan fully visible.
    """
    hashes = "#" * section_level(itinerary)
    pattern = re.compile(rf"^{hashes}\s+(.*\S)\s*$")
    sections, title, body = [], None, []
    for line in (itinerary or "").splitlines():
        match = pattern.match(line)
        if match:
            if title is not None or any(l.strip() for l in body):
                sections.append((title, "\n".join(body).strip()))
            title, body = match.group(1).strip(), []
        else:
            body.append(line)
    if title is not None or any(l.strip() for l in body):
        sections.append((title, "\n".join(body).strip()))
    return [(t, b) for t, b in sections if (t or b)]


def tab_for(title) -> str:
    """
    Which tab a section heading belongs under, or 'More' if none fits.

    An untitled section is the preamble — the plan's own title line and the trip
    at a glance — so it goes to Overview, which is where a reader looks first.
    """
    if not title:
        return "Overview"
    lowered = re.sub(r"[^a-z ,&-]", " ", title.lower())
    for tab, words in MATCH_RULES:
        if any(word in lowered for word in words):
            return tab
    return "More"


def group_into_tabs(itinerary: str):
    """
    Group the itinerary's sections into tabs, in a fixed reading order.

    Returns a list of (tab name, [(section title, body), ...]). Empty tabs are
    dropped, so a plan with no hotel section shows no hotel tab rather than an
    empty one. Two sections that belong together — the budget validation and the
    full breakdown — share a tab rather than producing two called Budget.
    """
    grouped = {}
    for title, body in split_sections(itinerary):
        grouped.setdefault(tab_for(title), []).append((title, body))
    return [(name, grouped[name]) for name in DISPLAY_ORDER if grouped.get(name)]


def split_days(body: str):
    """
    Break a day-by-day section into one entry per day, as (label, text).

    The delimiters are the headings the coordinator writes — `### 🌅 DAY 1: ...`
    or `**Day 1**` — matched loosely, because the decoration varies between runs.

    Two things a looser match got wrong. Every day ends with its own
    `**DAY 1 SUMMARY:**` line, which reads as another heading and split each day
    into a stub plus a summary: nine entries for a four-day trip. So a heading
    only opens a new entry when its NUMBER CHANGES, and a second mention of the
    day already being read stays part of it. And `| **Day 2 Expenses** | ... |`
    in the budget table is a row, not a heading, so rows are skipped.

    Anything before the first day heading is kept only if it holds something. The
    coordinator usually writes a bare `---` there, and an expander labelled
    "Before day 1" with nothing in it is something to click for no reason.
    """
    pattern = re.compile(r"^\s*(?:#{2,4}\s*)?(?:\*{0,2})\s*[^\w\n]{0,4}\s*"
                         r"day\s*(\d+)\b(.*)$", re.IGNORECASE)
    days, label, number, chunk = [], None, None, []

    def flush():
        text = "\n".join(chunk).strip()
        if label is None and not re.search(r"[A-Za-z0-9]", text):
            return                                  # a bare rule, not content
        if label is not None or text:
            days.append((label or "Before day 1", text))

    for line in (body or "").splitlines():
        match = pattern.match(line)
        if match and "|" not in line and int(match.group(1)) != number:
            flush()
            number = int(match.group(1))
            tail = re.sub(r"^[\s:—–\-*#]+", "", match.group(2) or "").strip("*# ")
            room = MAX_DAY_LABEL - len(f"Day {number} — ")
            if len(tail) > room:
                tail = tail[:room - 1].rstrip(" ,—–-") + "…"
            label = f"Day {number}" + (f" — {tail}" if tail else "")
            chunk = []
        else:
            chunk.append(line)
    flush()
    return days


def split_blocks(body: str):
    """
    Break one section's body into its own sub-blocks, as (heading, text) pairs.

    A flight or hotel section is not prose — it is three recommended options and
    a table of the rest, each under its own sub-heading. Rendered as one markdown
    string they run together into a column of text where the reader has to find
    the boundaries. Split, each becomes a card.

    Uses the same "a level used once is a title, a level used repeatedly is a
    divider" rule as `section_level`, applied inside the section. A body with
    nothing repeated comes back as one block, which is the signal to render it
    plainly rather than as a single pointless card.
    """
    text = body or ""
    hashes = "#" * section_level(text)
    pattern = re.compile(rf"^{hashes}\s+(.*\S)\s*$")
    blocks, heading, chunk = [], None, []

    def flush():
        joined = "\n".join(chunk).strip()
        if heading is not None or re.search(r"[A-Za-z0-9]", joined):
            blocks.append((heading, joined))

    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            flush()
            # The coordinator writes "### **YOUR TOP 3 RECOMMENDED FLIGHTS:**",
            # so the markers come through with the words. They are decoration for
            # a markdown reader, not part of the name of anything.
            heading = match.group(1).strip().strip("*#: ").strip()
            chunk = []
        else:
            chunk.append(line)
    flush()
    return blocks or [(None, text.strip())]


def split_meta(body: str):
    """
    Pull "**Label:** value | **Label:** value" header lines out of a section.

    Returns (facts, remaining_text), where facts are (label, value) pairs with the
    markdown removed, so the page can render them as a clean table instead.

    Why this exists. The coordinator opens a plan with two lines like

        **Prepared for:** 1 Adult Traveler | **Dates:** August 15, 2026 ...
        **Origin:** Lahore (LHE) | **Destination:** Istanbul (IST) | ...

    Two consecutive lines containing pipes, with no |---| separator row. A
    markdown renderer cannot tell whether that is meant to be a table, and
    Streamlit resolves the ambiguity by printing it verbatim -- so the reader sees
    raw asterisks at the very top of the plan, which is the first thing they look
    at. Real tables in the plan have a separator row and render correctly; these
    two lines never did.

    Two guards keep this from eating content. Only the first ten lines are
    considered, because this is a header block. And every pair must have a value:
    "**DAY 1 SUMMARY:**" is a heading with nothing after the colon, and taking it
    would delete a day's summary. Prose that merely contains a pipe is untouched,
    since it does not parse as label/value pairs.
    """
    pair = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
    lines = (body or "").splitlines()
    facts, taken = [], set()

    for index, line in enumerate(lines[:10]):
        stripped = line.strip()
        if not stripped:
            continue
        matches = [pair.match(part.strip()) for part in stripped.split("|")]
        if not matches or not all(matches):
            continue
        if not all(match.group(2).strip() for match in matches):
            continue
        for match in matches:
            facts.append((match.group(1).strip(), match.group(2).strip()))
        taken.add(index)

    # One more shape carries the same risk without being label/value pairs: a
    # whole line wrapped in ** with a pipe inside it, such as
    # "**4-Day Custom Travel Itinerary for 1 Traveler | Lahore to Istanbul**".
    # The pipe still makes the line look like a table row. Unwrapping the bold
    # and replacing the pipe with a middot removes the ambiguity and reads better
    # than a line of asterisks.
    whole_bold = re.compile(r"^\*\*(.+)\*\*$")
    kept = []
    for index, line in enumerate(lines):
        if index in taken:
            continue
        match = whole_bold.match(line.strip()) if index < 10 else None
        if match and "|" in match.group(1):
            kept.append(match.group(1).replace(" | ", "  ·  ").strip())
        else:
            kept.append(line)

    if not facts and kept == lines:
        return [], body
    return facts, "\n".join(kept).strip()


def defuse_pipes(text: str) -> str:
    """
    Replace pipes with a middot on every line that is not part of a real table.

    This is the general form of the bug split_meta fixes one case of. A pipe is
    how markdown marks a table cell, so a line containing one looks like a table
    row -- and when the surrounding rows do not agree, or there is no |---|
    separator, the renderer gives up and prints the line verbatim, asterisks and
    all. The plans are full of pipes used as ordinary separators:

        * **Outbound Flight:** LHE (03:05) -> IST (10:45) | Duration 7h 40m
        **Prepared for:** 1 Adult | **Dates:** August 15, 2026

    A genuine table row starts with a pipe, and those are left exactly as they
    are: the flight and hotel comparison tables have proper separator rows and
    render correctly. Everything else gets a middot, which is what the pipe was
    being used as anyway.
    """
    out = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if "|" in line and not stripped.startswith("|"):
            line = re.sub(r"\s*\|\s*", "  ·  ", line).rstrip()
        out.append(line)
    return "\n".join(out)


def plan_checks(console: str, refused: bool = False):
    """
    The checks the run actually applied, as (text, tone) pairs.

    Read back out of what the run reported rather than asserted here, so a check
    that stopped running stops being claimed.

    Models do drop days: asked for four, they return one and stop. That is
    reported, not hidden, and not silently regenerated — a second attempt costs
    another set of model requests, and the shortfall is a finding the
    dissertation reports rather than a defect to paper over.
    """
    checks = []
    days = re.search(r"validation(?: passed)?: (\d+)/(\d+) days found", console)
    if days:
        found, expected = int(days.group(1)), int(days.group(2))
        checks.append((f"{found} of {expected} days present",
                       "good" if found >= expected else "warn"))
    if "this figure is measured, not estimated" in console:
        checks.append(("flight price measured, not estimated", "good"))
    if "is not in the price table" in console:
        checks.append(("destination not in the price table", "warn"))
    if refused:
        checks.append(("budget below the floor for this trip", "bad"))
    return checks
