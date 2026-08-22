"""
WHAT THIS FILE DOES
===================
The web interface. Collects the trip details, runs the planner, and shows the
itinerary alongside the checks that were applied to it.

Everything below the form is approach D: extraction by a model, then retrieval in
plain Python, then assembly by a model.

The page has two states, and they want different shapes
-------------------------------------------------------
Asking and showing are different jobs. Asking wants a narrow column — a form
80 characters wide is harder to read, not easier. Showing wants the whole page: a
finished itinerary is around 24,000 characters across eight sections and one block
per day, and it was being poured into a 55%-wide column as a single markdown
string. That is 380 lines of vertical scroll with no way to reach the third day
except by dragging past the first two.

So the form is centred and grouped while it is being filled in, and the results
take the full width and are split into tabs, one per section the itinerary
actually contains, with a block per day inside the day-by-day tab.

The sections are read from the itinerary rather than assumed. A model asked for a
plan usually produces the eight headings the coordinator's prompt requests, but
not always — so anything unrecognised keeps its own tab, and text with no headings
at all falls back to being shown whole. A tab that hid part of the plan would be
worse than a long page.

THREE THINGS THAT WERE WRONG, BEYOND THE LAYOUT
-----------------------------------------------
It never asked how many people were travelling. The command-line agent asks that
second; this form did not ask at all, so the extractor supplied the number from
context — and it multiplies airfare and meals inside the feasibility check. A
budget was being called possible or impossible partly on a figure nobody entered.

Both date fields opened on today, so the first press of the button always failed
with "the return date is not after the departure date". A default that cannot be
submitted is not a default.

The progress it showed was not real. A spinner reading "Planning your amazing
trip..." covered the entire run, which is several minutes, so a frozen page and a
working page looked identical. The orchestrator now reports each step as it
begins, through `set_progress_hook`, and what appears here is the same four steps
the terminal prints.
"""

import datetime
import html
import io
import re
import uuid
from contextlib import redirect_stdout

import streamlit as st
from dotenv import load_dotenv

from trip_planner.orchestrator import TripPlannerCrew, set_progress_hook
from trip_planner.ui.plan_layout import (group_into_tabs, plan_checks,
                                         split_days)

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
# Type, spacing and one accent. The previous version drew chat bubbles in raw
# HTML under a 3rem centred heading, which read as a demonstration of Streamlit
# rather than as a travel tool.
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

  .block-container { padding-top: 2rem; }

  /* Masthead ------------------------------------------------------------- */
  .tp-mast {
    border-bottom: 1px solid var(--line);
    padding-bottom: 1.1rem; margin-bottom: 1.6rem;
  }
  .tp-mast h1 {
    font-size: 1.55rem; font-weight: 640; letter-spacing: -0.02em;
    color: var(--ink); margin: 0 0 0.3rem 0; line-height: 1.2;
  }
  .tp-mast p { font-size: 0.88rem; color: var(--ink-soft); margin: 0; max-width: 68ch; }
  .tp-tags { margin-top: 0.7rem; display: flex; gap: 0.4rem; flex-wrap: wrap; }
  .tp-tag {
    font-size: 0.68rem; font-weight: 560; letter-spacing: 0.03em;
    text-transform: uppercase; color: var(--accent);
    background: #EEF0FF; border: 1px solid #DDE0FB;
    padding: 0.18rem 0.48rem; border-radius: 3px;
  }

  /* Section labels ------------------------------------------------------- */
  .tp-sect {
    font-size: 0.7rem; font-weight: 660; letter-spacing: 0.09em;
    text-transform: uppercase; color: var(--ink-faint);
    margin: 0 0 0.5rem 0;
  }
  .tp-groupno {
    display: inline-block; width: 1.25rem; height: 1.25rem; line-height: 1.25rem;
    text-align: center; border-radius: 50%; background: var(--accent);
    color: #fff; font-size: 0.68rem; font-weight: 700; margin-right: 0.45rem;
  }
  .tp-grouphead {
    font-size: 0.95rem; font-weight: 620; color: var(--ink);
    margin: 0 0 0.15rem 0;
  }
  .tp-groupsub {
    font-size: 0.78rem; color: var(--ink-soft); margin: 0 0 0.7rem 1.7rem;
  }

  .tp-card {
    background: var(--surface); border: 1px solid var(--line);
    border-radius: 6px; padding: 1rem 1.15rem; margin-bottom: 0.85rem;
  }

  /* Step list ------------------------------------------------------------ */
  .tp-step {
    display: flex; gap: 0.7rem; align-items: baseline;
    padding: 0.48rem 0; border-bottom: 1px solid var(--line);
  }
  .tp-step:last-child { border-bottom: none; }
  .tp-step__mark { width: 1.1rem; flex: none; font-size: 0.9rem; }
  .tp-step__who { font-size: 0.85rem; font-weight: 580; color: var(--ink); display: block; }
  .tp-step__what { font-size: 0.77rem; color: var(--ink-soft); display: block; margin-top: 0.1rem; }
  .tp-step--idle .tp-step__who,
  .tp-step--idle .tp-step__what { color: var(--ink-faint); }

  /* Label / value rows --------------------------------------------------- */
  .tp-fact {
    display: flex; justify-content: space-between; gap: 1rem;
    font-size: 0.81rem; padding: 0.28rem 0;
    border-bottom: 1px dotted var(--line);
  }
  .tp-fact:last-child { border-bottom: none; }
  .tp-fact__k { color: var(--ink-soft); }
  .tp-fact__v { color: var(--ink); font-weight: 550; text-align: right; }

  /* Badges --------------------------------------------------------------- */
  .tp-badge {
    display: inline-block; font-size: 0.73rem; font-weight: 580;
    padding: 0.2rem 0.52rem; border-radius: 3px; border: 1px solid;
  }
  .tp-badge--good { color: var(--good); background: #EAF6F0; border-color: #C6E5D6; }
  .tp-badge--warn { color: var(--warn); background: #FDF3E4; border-color: #F0DCBC; }
  .tp-badge--bad  { color: var(--bad);  background: #FCEDEC; border-color: #F4D3D1; }
  .tp-badge--flat { color: var(--ink-soft); background: var(--surface-2); border-color: var(--line); }

  /* Itinerary body ------------------------------------------------------- */
  .tp-body { max-width: 86ch; }
  .tp-body h1, .tp-body h2 { display: none; }   /* the tab already names it */

  .tp-empty {
    border: 1px dashed var(--line); border-radius: 6px;
    padding: 2.2rem 1.5rem; text-align: center; color: var(--ink-faint);
    font-size: 0.85rem; line-height: 1.6;
  }
  .tp-note { font-size: 0.755rem; color: var(--ink-faint); line-height: 1.5; }

  /* Streamlit's own chrome ---------------------------------------------- */
  div[data-testid="stForm"] { border: none; padding: 0; }
  .stButton > button { font-weight: 560; border-radius: 4px; }
  button[data-baseweb="tab"] { font-size: 0.86rem; font-weight: 560; }
  #MainMenu, footer { visibility: hidden; }

  /* Tables inside the plan must not push the page sideways. */
  .stMarkdown table { display: block; overflow-x: auto; max-width: 100%; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Small render helpers
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
    "facts": [],
}
for _key, _value in DEFAULTS.items():
    st.session_state.setdefault(_key, _value)


def _reset() -> None:
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def _badge(text: str, tone: str = "flat") -> str:
    return f'<span class="tp-badge tp-badge--{tone}">{html.escape(text)}</span>'


def _facts(rows) -> str:
    body = "".join(
        f'<div class="tp-fact"><span class="tp-fact__k">{html.escape(str(k))}</span>'
        f'<span class="tp-fact__v">{html.escape(str(v))}</span></div>'
        for k, v in rows if v not in (None, "", 0))
    return f'<div class="tp-card">{body}</div>'


def _group_head(number: int, title: str, subtitle: str) -> None:
    """A numbered heading for one group of questions."""
    st.markdown(
        f'<p class="tp-grouphead"><span class="tp-groupno">{number}</span>'
        f'{html.escape(title)}</p>'
        f'<p class="tp-groupsub">{html.escape(subtitle)}</p>',
        unsafe_allow_html=True)


def _render_steps(reached: int, container) -> None:
    """Draw the step list with everything before `reached` marked done."""
    rows = []
    for index, (who, what) in enumerate(STEPS, start=1):
        mark = "✓" if index < reached else ("▸" if index == reached else "·")
        cls = "" if index <= reached else " tp-step--idle"
        rows.append(
            f'<div class="tp-step{cls}"><span class="tp-step__mark">{mark}</span>'
            f'<span><span class="tp-step__who">{html.escape(who)}</span>'
            f'<span class="tp-step__what">{html.escape(what)}</span></span></div>')
    container.markdown(f'<div class="tp-card">{"".join(rows)}</div>',
                       unsafe_allow_html=True)


def _travellers(answers) -> str:
    adults = answers.get("adults", 1)
    text = f"{adults} adult" + ("s" if adults != 1 else "")
    kids = answers.get("children", 0)
    if kids:
        text += f", {kids} child" + ("ren" if kids != 1 else "")
    return text


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

FINISHED = bool(st.session_state.itinerary or st.session_state.failure)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    if FINISHED:
        answers = st.session_state.answers
        st.markdown('<div class="tp-sect">The request</div>', unsafe_allow_html=True)
        st.markdown(_facts([
            ("Destination", answers.get("destination")),
            ("From", answers.get("origin")),
            ("Departure", answers.get("start_date")),
            ("Return", answers.get("end_date")),
            ("Nights", answers.get("nights")),
            ("Travellers", _travellers(answers)),
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

        st.markdown("---")
        if st.button("Plan another trip", use_container_width=True):
            _reset()
            st.rerun()
    else:
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

        st.markdown('<div class="tp-sect">Steps it will run</div>',
                    unsafe_allow_html=True)
        _render_steps(0, st)


# ===========================================================================
# STATE 1 — asking. A centred form, grouped and numbered.
# ===========================================================================
submitted = False

if not FINISHED:
    gutter_l, middle, gutter_r = st.columns([0.14, 0.72, 0.14])
    with middle:
        with st.form("trip", clear_on_submit=False, border=False):

            with st.container(border=True):
                _group_head(1, "Where and when",
                            "The route and the dates. Both are used to fetch real "
                            "fares, so they need to be the dates you would book.")
                destination = st.text_input(
                    "Destination", placeholder="Istanbul, Turkey")
                origin = st.text_input(
                    "Travelling from", placeholder="Lahore, Pakistan")
                # Defaulted a month out, not to today. Both fields used to open on
                # today's date, so the first press of the button always failed with
                # "the return date is not after the departure date".
                today = datetime.date.today()
                date_a, date_b = st.columns(2)
                start_date = date_a.date_input(
                    "Departure", value=today + datetime.timedelta(days=30))
                end_date = date_b.date_input(
                    "Return", value=today + datetime.timedelta(days=37))

            with st.container(border=True):
                _group_head(2, "Who is going",
                            "Asked outright, because this number multiplies "
                            "airfare and meals when the budget is checked.")
                who_a, who_b = st.columns(2)
                adults = who_a.number_input("Adults", min_value=1, max_value=12,
                                            value=1, step=1)
                children = who_b.number_input("Children", min_value=0,
                                              max_value=12, value=0, step=1)

            with st.container(border=True):
                _group_head(3, "Budget and style",
                            "The total, and what matters most. The wording of the "
                            "second changes how the money is divided.")
                budget = st.number_input(
                    "Total budget for the whole trip, in US dollars",
                    min_value=0, value=3000, step=100,
                    help="Every figure in this system is USD — the APIs are "
                         "queried in USD and the cost model's thresholds are USD "
                         "amounts. Please convert before entering.")
                # Free text rather than three options. The allocation reads
                # phrasing: "luxury stay" moves the room budget, "luxury trip"
                # spreads it across room, food and activities, and "I can
                # compromise" moves money out of the room and airfare into
                # experiences. A luxury/moderate/budget dropdown expresses none
                # of that.
                travel_style = st.text_input(
                    "What matters most on this trip?",
                    placeholder="a luxury stay / great food and lots to do / "
                                "I can compromise to keep it cheap / moderate")

            with st.container(border=True):
                _group_head(4, "Preferences",
                            "What to fill the days with, and anything that has to "
                            "be worked around.")
                interests = st.text_input(
                    "Interests", placeholder="museums, food, nightlife, hiking")
                special_requirements = st.text_input(
                    "Special requirements",
                    placeholder="dietary, accessibility, or leave blank")

            st.write("")
            submitted = st.form_submit_button(
                "Build itinerary", type="primary", use_container_width=True)

        problems = []
        if submitted:
            problems = [name for name, value in
                        [("destination", destination), ("origin", origin),
                         ("interests", interests)] if not str(value).strip()]
            if problems:
                st.error("Still needed: " + ", ".join(problems) + ".")
            elif end_date <= start_date:
                problems = ["dates"]
                st.error("The return date is not after the departure date.")

        if not submitted:
            st.markdown("""
<div class="tp-empty">
  The plan appears here once this is built.<br>
  Flights and hotels are fetched, the budget is checked against what the trip
  really costs, and the day count is verified before anything is shown.
</div>
""", unsafe_allow_html=True)

    # ---- run ----------------------------------------------------------------
    if submitted and not problems:
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

        # The transcript keeps the question-and-answer shape the extractor was
        # written against, so nothing downstream needs to know the form changed.
        # The traveller counts are stated in words for the same reason.
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

        with middle:
            st.markdown('<div class="tp-sect">Working</div>',
                        unsafe_allow_html=True)
            step_box, note_box, fact_box = st.empty(), st.empty(), st.empty()
            _render_steps(1, step_box)
            state = {"facts": []}

            def on_progress(kind, *parts):
                """
                Told by the orchestrator as each step begins and each fact lands.

                The same four steps the terminal prints, and the same detail
                lines — route, dates, the budget handed to each search, and what
                each search came back with.
                """
                if kind == "step":
                    match = re.search(r"(\d+)", parts[0])   # "STEP 2 of 4"
                    if match:
                        _render_steps(int(match.group(1)), step_box)
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
                with redirect_stdout(captured):
                    if not st.session_state.crew:
                        st.session_state.crew = TripPlannerCrew()
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


# ===========================================================================
# STATE 2 — showing. Full width, one tab per section the plan contains.
# ===========================================================================
else:
    if st.session_state.failure:
        st.markdown('<div class="tp-sect">The run did not finish</div>',
                    unsafe_allow_html=True)
        st.error(st.session_state.failure)
        if st.session_state.console:
            with st.expander("Terminal output for this run"):
                st.code(st.session_state.console, language="text")

    else:
        itinerary = st.session_state.itinerary
        console = st.session_state.console or ""
        answers = st.session_state.answers

        # The budget check can refuse a trip outright, in which case what came
        # back is the refusal and its reasoning rather than a plan. Presenting
        # that under the heading "Itinerary" would be a lie about what it is.
        refused = "CANNOT BE PLANNED WITHIN THAT BUDGET" in itinerary

        heading = (f"{answers.get('destination', 'Trip')} · "
                   f"{answers.get('nights', '?')} nights · "
                   f"{_travellers(answers)}")
        st.markdown(f'<div class="tp-sect">{html.escape(heading)}</div>',
                    unsafe_allow_html=True)

        checks = [_badge(text, tone)
                  for text, tone in plan_checks(console, refused)]
        if checks:
            st.markdown(" ".join(checks), unsafe_allow_html=True)

        # Only values the run established. A cheapest fare appears when the route
        # had been recorded and a real price was read out of it; when it had not,
        # the column is absent rather than estimated.
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

        if refused:
            st.code(itinerary, language="text")
        else:
            tabs = group_into_tabs(itinerary)
            if not tabs:
                # No headings at all. Show the whole thing rather than nothing.
                st.markdown(itinerary)
            else:
                for tab, (name, sections) in zip(
                        st.tabs([name for name, _ in tabs]), tabs):
                    with tab:
                        for title, body in sections:
                            if name == "Day by day":
                                days = split_days(body)
                                if len(days) > 1:
                                    for index, (label, text) in enumerate(days):
                                        with st.expander(label, expanded=index == 0):
                                            st.markdown(
                                                f'<div class="tp-body">',
                                                unsafe_allow_html=True)
                                            st.markdown(text)
                                            st.markdown('</div>',
                                                        unsafe_allow_html=True)
                                    continue
                            if title and len(sections) > 1:
                                st.markdown(f"##### {title}")
                            st.markdown(body)

        st.write("")
        download, terminal = st.columns([0.32, 0.68])
        download.download_button(
            "Download the plan",
            data=itinerary,
            file_name=("itinerary-" +
                       re.sub(r"[^A-Za-z0-9]+", "-",
                              answers.get("destination", "trip")).strip("-") +
                       ".md"),
            mime="text/markdown",
            use_container_width=True,
        )
        if console:
            with terminal.expander("Terminal output for this run"):
                st.code(console, language="text")
