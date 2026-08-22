"""
WHAT THIS FILE DOES
===================
The web interface. Collects the trip details, runs the planner, and shows the
itinerary alongside the checks that were applied to it.

Everything below the form is approach D: extraction by a model, then retrieval in
plain Python, then assembly by a model.

Three things changed here, and each fixed something that was wrong rather than
merely plain.

ONE FORM, NOT EIGHT SCREENS
---------------------------
The questions used to arrive one at a time, each on its own submit. Eight
round-trips to enter eight short facts, no way to look back at an answer already
given, and no way to correct one without starting over. They are now a single
grouped form. This is still a fixed question list rather than a dialogue with the
conversational agent — Streamlit re-runs the whole script on every interaction,
which does not suit a streaming multi-turn conversation — so the deviation from
the proposal is the same one, recorded in the dissertation, and no larger. The
conversational agent remains on the command-line path.

IT ASKS HOW MANY PEOPLE ARE TRAVELLING
--------------------------------------
It did not. The command-line agent asks as its second question; this form never
did, so the extractor filled the number in from context — and the traveller count
multiplies airfare and meals in the feasibility check. A budget was being declared
possible or impossible partly on a figure nobody had supplied. Adults and children
are now asked outright.

THE PROGRESS IT SHOWS IS REAL
-----------------------------
A spinner reading "Planning your amazing trip..." covered the entire run, which is
several minutes. A frozen page and a working page looked the same. The orchestrator
now reports each step as it begins, through `set_progress_hook`, and what appears
here is the same four steps the terminal prints — not an animation.
"""

import html
import io
import re
import uuid
from contextlib import redirect_stdout

import streamlit as st
from dotenv import load_dotenv

from trip_planner.orchestrator import TripPlannerCrew, set_progress_hook

load_dotenv()

st.set_page_config(
    page_title="Trip Planner — multi-agent itinerary builder",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling
#
# Kept to type, spacing and one accent. The previous version drew chat bubbles
# with raw HTML and a 3rem centred heading; the result read as a demo of
# Streamlit rather than a travel tool.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  :root {
    --ink:        #1F2430;
    --ink-soft:   #5A6274;
    --ink-faint:  #8A91A0;
    --line:       #E4E7EF;
    --surface:    #FFFFFF;
    --surface-2:  #F7F8FC;
    --accent:     #4338CA;
    --good:       #0F7B4F;
    --warn:       #A85B00;
    --bad:        #B3261E;
  }

  .block-container { padding-top: 2.2rem; max-width: 1180px; }

  /* Masthead ------------------------------------------------------------- */
  .tp-mast {
    border-bottom: 1px solid var(--line);
    padding-bottom: 1.15rem;
    margin-bottom: 1.7rem;
  }
  .tp-mast h1 {
    font-size: 1.6rem; font-weight: 640; letter-spacing: -0.02em;
    color: var(--ink); margin: 0 0 0.3rem 0; line-height: 1.2;
  }
  .tp-mast p {
    font-size: 0.9rem; color: var(--ink-soft); margin: 0; max-width: 62ch;
  }
  .tp-tags { margin-top: 0.75rem; display: flex; gap: 0.4rem; flex-wrap: wrap; }
  .tp-tag {
    font-size: 0.7rem; font-weight: 560; letter-spacing: 0.03em;
    text-transform: uppercase; color: var(--accent);
    background: #EEF0FF; border: 1px solid #DDE0FB;
    padding: 0.2rem 0.5rem; border-radius: 3px;
  }

  /* Section headings ----------------------------------------------------- */
  .tp-sect {
    font-size: 0.72rem; font-weight: 640; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--ink-faint);
    margin: 1.6rem 0 0.55rem 0;
  }
  .tp-sect:first-child { margin-top: 0; }

  /* Cards ---------------------------------------------------------------- */
  .tp-card {
    background: var(--surface); border: 1px solid var(--line);
    border-radius: 6px; padding: 1.15rem 1.3rem; margin-bottom: 0.9rem;
  }
  .tp-card--quiet { background: var(--surface-2); }

  /* Step list ------------------------------------------------------------ */
  .tp-step {
    display: flex; gap: 0.7rem; align-items: baseline;
    padding: 0.5rem 0; border-bottom: 1px solid var(--line);
  }
  .tp-step:last-child { border-bottom: none; }
  .tp-step__mark { width: 1.1rem; flex: none; font-size: 0.9rem; }
  .tp-step__body { flex: 1 1 auto; }
  .tp-step__who {
    font-size: 0.85rem; font-weight: 580; color: var(--ink); display: block;
  }
  .tp-step__what {
    font-size: 0.78rem; color: var(--ink-soft); display: block;
    margin-top: 0.1rem;
  }
  .tp-step--idle .tp-step__who,
  .tp-step--idle .tp-step__what { color: var(--ink-faint); }

  /* Facts (label / value rows) ------------------------------------------- */
  .tp-fact {
    display: flex; justify-content: space-between; gap: 1rem;
    font-size: 0.82rem; padding: 0.3rem 0;
    border-bottom: 1px dotted var(--line);
  }
  .tp-fact:last-child { border-bottom: none; }
  .tp-fact__k { color: var(--ink-soft); }
  .tp-fact__v { color: var(--ink); font-weight: 550; text-align: right; }

  /* Badges --------------------------------------------------------------- */
  .tp-badge {
    display: inline-block; font-size: 0.74rem; font-weight: 580;
    padding: 0.22rem 0.55rem; border-radius: 3px; border: 1px solid;
  }
  .tp-badge--good { color: var(--good); background: #EAF6F0; border-color: #C6E5D6; }
  .tp-badge--warn { color: var(--warn); background: #FDF3E4; border-color: #F0DCBC; }
  .tp-badge--bad  { color: var(--bad);  background: #FCEDEC; border-color: #F4D3D1; }
  .tp-badge--flat { color: var(--ink-soft); background: var(--surface-2); border-color: var(--line); }

  /* Itinerary ------------------------------------------------------------ */
  .tp-itin { font-size: 0.92rem; line-height: 1.62; color: var(--ink); }
  .tp-itin h1, .tp-itin h2 { font-size: 1.12rem; font-weight: 620;
    margin: 1.5rem 0 0.5rem 0; padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--line); }
  .tp-itin h3 { font-size: 0.98rem; font-weight: 600; margin: 1.2rem 0 0.35rem 0; }

  /* Empty state ---------------------------------------------------------- */
  .tp-empty {
    border: 1px dashed var(--line); border-radius: 6px;
    padding: 2rem 1.5rem; text-align: center; color: var(--ink-faint);
    font-size: 0.86rem;
  }

  .tp-note { font-size: 0.76rem; color: var(--ink-faint); line-height: 1.5; }

  /* Streamlit's own chrome ---------------------------------------------- */
  div[data-testid="stForm"] { border: none; padding: 0; }
  .stButton > button { font-weight: 560; border-radius: 4px; }
  #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# The four steps, named as the orchestrator names them.
# ---------------------------------------------------------------------------
STEPS = [
    ("Conversational agent", "Collecting the details the plan needs"),
    ("Preferences extractor", "Turning the request into structured fields, then checking the budget"),
    ("Retrieval", "Fetching flights, hotels and venues in plain Python"),
    ("Itinerary coordinator", "Assembling the day-by-day plan"),
]

DEFAULTS = {
    "itinerary": None,
    "crew": None,
    "conversation_id": None,
    "console": "",
    "failure": None,
    "answers": {},
    "facts": [],            # (label, value) pairs the run reported as it went
}
for _key, _value in DEFAULTS.items():
    st.session_state.setdefault(_key, _value)


def _reset() -> None:
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def _badge(text: str, tone: str = "flat") -> str:
    return (f'<span class="tp-badge tp-badge--{tone}">'
            f'{html.escape(text)}</span>')


def _facts(rows) -> str:
    body = "".join(
        f'<div class="tp-fact"><span class="tp-fact__k">{html.escape(str(k))}</span>'
        f'<span class="tp-fact__v">{html.escape(str(v))}</span></div>'
        for k, v in rows if v not in (None, "", 0))
    return f'<div class="tp-card">{body}</div>'


def plan_checks(console: str, refused: bool = False):
    """
    The checks the run actually applied, as (text, tone) pairs.

    Read back out of what the run reported rather than asserted here, so a check
    that stopped running stops being claimed. A separate function because it is
    the one piece of this page with logic worth testing — the day count in
    particular, which is the difference between an itinerary that covers the trip
    and one that stops on the first morning.

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


def _render_steps(reached: int, container) -> None:
    """
    Draw the step list with everything up to `reached` marked done.

    `reached` is the 1-based number of the step currently running, or
    len(STEPS) + 1 once the run is over.
    """
    rows = []
    for index, (who, what) in enumerate(STEPS, start=1):
        if index < reached:
            mark, cls = "✓", ""
        elif index == reached:
            mark, cls = "▸", ""
        else:
            mark, cls = "·", " tp-step--idle"
        rows.append(
            f'<div class="tp-step{cls}"><span class="tp-step__mark">{mark}</span>'
            f'<span class="tp-step__body">'
            f'<span class="tp-step__who">{html.escape(who)}</span>'
            f'<span class="tp-step__what">{html.escape(what)}</span>'
            f'</span></div>')
    container.markdown(f'<div class="tp-card">{"".join(rows)}</div>',
                       unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Masthead
# ---------------------------------------------------------------------------
st.markdown("""
<div class="tp-mast">
  <h1>Trip Planner</h1>
  <p>A day-by-day itinerary built from real flight, hotel and venue data. Two
     model steps with retrieval in plain Python between them, exchanging typed
     messages over an A2A protocol.</p>
  <div class="tp-tags">
    <span class="tp-tag">Approach D &middot; three agents</span>
    <span class="tp-tag">A2A protocol</span>
    <span class="tp-tag">MCP tools</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — run detail, and the honest notes
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="tp-sect">This run</div>', unsafe_allow_html=True)

    if st.session_state.conversation_id:
        st.markdown(_facts([
            ("Conversation", st.session_state.conversation_id[:8]),
            ("Architecture", "Approach D"),
            ("Model steps", "2 of 4"),
        ]), unsafe_allow_html=True)
    else:
        st.markdown('<p class="tp-note">Nothing planned yet. Fill in the trip '
                    'and press Build itinerary.</p>', unsafe_allow_html=True)

    st.markdown('<div class="tp-sect">What the model does</div>',
                unsafe_allow_html=True)
    st.markdown("""
<p class="tp-note">
A model is used where the step needs a judgement that cannot be written as code —
reading a request, and arranging retrieved options into a sensible plan. Fetching
a fare for a known route on a known date is not such a step, so it runs as plain
Python. That division is the argument this project tests.
</p>
""", unsafe_allow_html=True)

    st.markdown('<div class="tp-sect">Prices</div>', unsafe_allow_html=True)
    st.markdown("""
<p class="tp-note">
Flights, hotels and venues come from live APIs, recorded on first use and replayed
after. Where a route has been recorded the budget check uses the fare that was
really quoted; where it has not, it estimates from a price table and says so.
</p>
""", unsafe_allow_html=True)

    if st.session_state.itinerary or st.session_state.failure:
        st.markdown("---")
        if st.button("Plan another trip", use_container_width=True):
            _reset()
            st.rerun()


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
left, right = st.columns([0.9, 1.1], gap="large")

# Defined before the form, because the form is only drawn on the first pass and
# the blocks below test this on every rerun. Without it the second pass raises
# NameError instead of showing the finished itinerary.
submitted = False

# --- the form ---------------------------------------------------------------
with left:
    if st.session_state.itinerary or st.session_state.failure:
        answers = st.session_state.answers
        st.markdown('<div class="tp-sect">The request</div>',
                    unsafe_allow_html=True)
        travellers = f"{answers.get('adults', 1)} adult"
        if answers.get("adults", 1) != 1:
            travellers += "s"
        if answers.get("children"):
            kids = answers["children"]
            travellers += f", {kids} child" + ("ren" if kids != 1 else "")
        st.markdown(_facts([
            ("Destination", answers.get("destination")),
            ("From", answers.get("origin")),
            ("Dates", f"{answers.get('start_date')} to {answers.get('end_date')}"),
            ("Travellers", travellers),
            ("Budget", f"${answers.get('budget', 0):,.0f} USD"),
            ("Style", answers.get("travel_style")),
            ("Interests", answers.get("interests")),
            ("Requirements", answers.get("special_requirements")),
        ]), unsafe_allow_html=True)

        st.markdown('<div class="tp-sect">Steps</div>', unsafe_allow_html=True)
        _render_steps(len(STEPS) + 1, st)

        if st.session_state.facts:
            st.markdown('<div class="tp-sect">What the run reported</div>',
                        unsafe_allow_html=True)
            st.markdown(_facts(st.session_state.facts), unsafe_allow_html=True)

        if st.session_state.console:
            with st.expander("Terminal output for this run"):
                st.code(st.session_state.console, language="text")

    else:
        with st.form("trip", clear_on_submit=False):
            st.markdown('<div class="tp-sect">Where and when</div>',
                        unsafe_allow_html=True)
            destination = st.text_input(
                "Destination", placeholder="Istanbul, Turkey")
            origin = st.text_input(
                "Travelling from", placeholder="Lahore, Pakistan")
            date_a, date_b = st.columns(2)
            start_date = date_a.date_input("Departure")
            end_date = date_b.date_input("Return")

            # Asked outright. The extractor used to infer this, and the number
            # multiplies airfare and meals in the feasibility check.
            st.markdown('<div class="tp-sect">Who is going</div>',
                        unsafe_allow_html=True)
            who_a, who_b = st.columns(2)
            adults = who_a.number_input("Adults", min_value=1, max_value=12,
                                        value=1, step=1)
            children = who_b.number_input("Children", min_value=0, max_value=12,
                                          value=0, step=1)

            st.markdown('<div class="tp-sect">Budget</div>',
                        unsafe_allow_html=True)
            budget = st.number_input(
                "Total budget for the whole trip, in US dollars",
                min_value=0, value=3000, step=100,
                help="Every figure in this system is USD — the APIs are queried "
                     "in USD and the cost model's thresholds are USD amounts. "
                     "Please convert before entering.")

            # Free text rather than three options. The allocation reads phrasing:
            # "luxury stay" moves the room budget, "luxury trip" spreads it
            # across room, food and activities, and "I can compromise" moves
            # money out of the room and airfare into experiences. A dropdown
            # offering luxury/moderate/budget cannot express any of that.
            travel_style = st.text_input(
                "What matters most on this trip?",
                placeholder="a luxury stay / great food and lots to do / "
                            "I can compromise to keep it cheap / moderate",
                help="Said however you like. The wording changes how the budget "
                     "is divided, not just how much of it is spent.")

            st.markdown('<div class="tp-sect">Preferences</div>',
                        unsafe_allow_html=True)
            interests = st.text_input(
                "Interests", placeholder="museums, food, nightlife, hiking")
            special_requirements = st.text_input(
                "Special requirements",
                placeholder="dietary, accessibility, or leave blank")

            submitted = st.form_submit_button(
                "Build itinerary", type="primary", use_container_width=True)

# --- run --------------------------------------------------------------------
if not st.session_state.itinerary and not st.session_state.failure and submitted:
    missing = [name for name, value in
               [("destination", destination), ("origin", origin),
                ("interests", interests)] if not str(value).strip()]
    if missing:
        with left:
            st.error("Still needed: " + ", ".join(missing) + ".")
    elif end_date <= start_date:
        with left:
            st.error("The return date is not after the departure date.")
    else:
        nights = (end_date - start_date).days
        st.session_state.answers = {
            "destination": destination.strip(),
            "origin": origin.strip(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "adults": int(adults),
            "children": int(children),
            "budget": float(budget),
            "travel_style": travel_style.strip() or "moderate",
            "interests": interests.strip(),
            "special_requirements": special_requirements.strip() or "none",
            "nights": nights,
        }
        st.session_state.conversation_id = str(uuid.uuid4())

        # The transcript keeps the same question-and-answer shape the extractor
        # was written against, so nothing downstream needs to know the form
        # changed. The traveller counts are stated in words for the same reason.
        people = f"{adults} adult" + ("s" if adults != 1 else "")
        if children:
            people += f" and {children} child" + ("ren" if children != 1 else "")
        transcript = "CONVERSATION TRANSCRIPT:\n\n" + "\n".join([
            "Agent: Where would you like to go?",
            f"User: {destination.strip()}",
            "Agent: Where are you travelling from?",
            f"User: {origin.strip()}",
            "Agent: How many people are travelling? (adults + children)",
            f"User: {people}",
            "Agent: When do you leave and when do you return?",
            f"User: Departing {start_date.isoformat()}, returning "
            f"{end_date.isoformat()} — {nights} nights",
            "Agent: What is your total budget in USD?",
            f"User: {budget:.0f} USD total for the whole trip",
            "Agent: What interests you most?",
            f"User: {interests.strip()}",
            "Agent: What matters most on this trip?",
            f"User: {travel_style.strip() or 'moderate'}",
            "Agent: Any special requirements?",
            f"User: {special_requirements.strip() or 'none'}",
        ]) + "\n"

        with right:
            st.markdown('<div class="tp-sect">Progress</div>',
                        unsafe_allow_html=True)
            step_box = st.empty()
            note_box = st.empty()
            fact_box = st.empty()
            _render_steps(1, step_box)

            state = {"step": 1, "facts": []}

            def on_progress(kind, *parts):
                """
                Told by the orchestrator as each step begins and each fact lands.

                Same four steps the terminal prints, and the same detail lines —
                the route, the dates, the budget handed to each search, and what
                each search came back with.
                """
                if kind == "step":
                    number = parts[0]                      # "STEP 2 of 4"
                    match = re.search(r"(\d+)", number)
                    if match:
                        state["step"] = int(match.group(1))
                        _render_steps(state["step"], step_box)
                elif kind == "detail":
                    state["facts"].append((parts[0], parts[1]))
                    fact_box.markdown(_facts(state["facts"]),
                                      unsafe_allow_html=True)
                elif kind == "budget":
                    note_box.markdown(
                        f'<p class="tp-note">{html.escape(parts[1])}</p>',
                        unsafe_allow_html=True)

            set_progress_hook(on_progress)
            captured = io.StringIO()
            try:
                if not st.session_state.crew:
                    with redirect_stdout(captured):
                        st.session_state.crew = TripPlannerCrew()
                with redirect_stdout(captured):
                    st.session_state.itinerary = (
                        st.session_state.crew.plan_trip_from_transcript(
                            transcript, st.session_state.conversation_id))
            except Exception as exc:                        # noqa: BLE001
                st.session_state.failure = f"{type(exc).__name__}: {exc}"
            finally:
                set_progress_hook(None)
                st.session_state.console = captured.getvalue()
                st.session_state.facts = state["facts"]
        st.rerun()

# --- results ----------------------------------------------------------------
with right:
    if st.session_state.failure:
        st.markdown('<div class="tp-sect">The run did not finish</div>',
                    unsafe_allow_html=True)
        st.error(st.session_state.failure)
        st.markdown(
            '<p class="tp-note">The terminal output for this run is under the '
            'request on the left, and holds the step it stopped at.</p>',
            unsafe_allow_html=True)

    elif st.session_state.itinerary:
        itinerary = st.session_state.itinerary
        console = st.session_state.console or ""

        # The budget check can refuse a trip outright, in which case what came
        # back is the refusal and its reasoning, not an itinerary. Saying so
        # plainly beats presenting a refusal under the heading "Your itinerary".
        refused = "CANNOT BE PLANNED WITHIN THAT BUDGET" in itinerary

        st.markdown('<div class="tp-sect">'
                    + ("Budget" if refused else "Itinerary")
                    + '</div>', unsafe_allow_html=True)

        # Only values the run actually established. A cheapest fare appears here
        # when the route had been recorded and the probe read a real price out of
        # it; when it had not, the row is absent rather than estimated.
        answers = st.session_state.answers
        fare = next((v for k, v in st.session_state.facts if k == "flight"), "")
        cheapest = re.search(r"cheapest \$([\d,]+)", str(fare))
        strip = st.columns(4 if cheapest else 3)
        strip[0].metric("Nights", answers.get("nights", "—"))
        strip[1].metric("Travellers",
                        answers.get("adults", 1) + answers.get("children", 0))
        strip[2].metric("Budget", f"${answers.get('budget', 0):,.0f}")
        if cheapest:
            strip[3].metric("Cheapest fare found", f"${cheapest.group(1)}")
        st.write("")

        checks = [_badge(text, tone)
                  for text, tone in plan_checks(console, refused)]
        if checks:
            st.markdown(" ".join(checks), unsafe_allow_html=True)
            st.write("")

        if refused:
            st.code(itinerary, language="text")
        else:
            st.markdown(itinerary)
            st.write("")
            st.download_button(
                "Download itinerary",
                data=itinerary,
                file_name=f"itinerary-{st.session_state.answers.get('destination','trip')}.md"
                          .replace(" ", "-").replace(",", ""),
                mime="text/markdown",
            )

    elif not submitted:
        st.markdown('<div class="tp-sect">Itinerary</div>',
                    unsafe_allow_html=True)
        st.markdown("""
<div class="tp-empty">
  The plan appears here.<br>
  Flights and hotels are fetched, the budget is checked against what the trip
  really costs, and the day count is verified before anything is shown.
</div>
""", unsafe_allow_html=True)
