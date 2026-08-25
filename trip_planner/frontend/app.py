"""
The web page.

Collects the trip details in one form, runs the planner while showing which
step is working, and shows the finished plan in tabs with a block per day.
"""

import datetime
import html
import re
import sys
import uuid
from contextlib import redirect_stdout

import streamlit as st
from dotenv import load_dotenv

from trip_planner.core.log_setup import TeeStream
from trip_planner.orchestrator import TripPlannerCrew, set_progress_hook
from trip_planner.frontend.plan_layout import (DONE, IDLE, NOW, SEARCH_ROW, STEPS,
                                         group_into_tabs, plan_checks,
                                         progress_states, split_blocks,
                                         split_days)

load_dotenv()

st.set_page_config(
    page_title="Trip Planner — planning from real prices",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# The display name, in one place. Nothing else in the project depends on it.
BRAND = "Trip Planner"
TAGLINE = ("Real fares. Real rooms. A day-by-day plan you could actually book — "
           "priced from live travel data, not guesswork.")

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  :root {
    --ink:        #161A23;
    --ink-soft:   #545C6E;
    --ink-faint:  #8A91A0;
    --line:       #E3E7F0;
    --line-soft:  #EEF1F7;
    --surface:    #FFFFFF;
    --surface-2:  #F7F8FC;
    --accent:     #4338CA;
    --accent-2:   #0EA5A4;
    --good:       #0F7B4F;
    --warn:       #A85B00;
    --bad:        #B3261E;
  }

  /* Wider than Streamlit's default, because the plan is the point. */
  .block-container { padding-top: 1.6rem; max-width: 1560px; }

  /* ---- Masthead ------------------------------------------------------- */
  .wf-mast { margin-bottom: 1.5rem; }
  .wf-eyebrow {
    font-size: 0.68rem; font-weight: 680; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--accent); margin: 0 0 0.35rem 0;
  }
  .wf-title {
    font-size: 4.4rem; font-weight: 780; letter-spacing: -0.04em;
    line-height: 1.02; margin: 0 0 0.7rem 0;
    background: linear-gradient(96deg, #1E1B4B 8%, #4338CA 46%, #0EA5A4 96%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: var(--accent);
  }
  .wf-tag {
    font-size: 0.98rem; color: var(--ink-soft); margin: 0; max-width: 74ch;
    line-height: 1.5;
  }
  .wf-rule {
    height: 3px; width: 74px; margin: 1rem 0 0 0; border-radius: 3px;
    background: linear-gradient(90deg, #4338CA, #0EA5A4);
  }

  /* ---- Sidebar -------------------------------------------------------- */
  .wf-brandbox {
    background: linear-gradient(150deg, #1E1B4B 0%, #312E81 52%, #0F766E 100%);
    border-radius: 10px; padding: 1.05rem 1.1rem; margin-bottom: 1.15rem;
    color: #fff;
  }
  .wf-brandbox__name {
    font-size: 1.22rem; font-weight: 720; letter-spacing: -0.02em;
    margin: 0 0 0.2rem 0;
  }
  .wf-brandbox__sub {
    font-size: 0.735rem; color: #C7D2FE; margin: 0; line-height: 1.45;
  }

  .wf-sect {
    font-size: 0.66rem; font-weight: 700; letter-spacing: 0.13em;
    text-transform: uppercase; color: var(--ink-faint);
    margin: 1.25rem 0 0.55rem 0; display: flex; align-items: center; gap: 0.5rem;
  }
  .wf-sect::after {
    content: ""; flex: 1 1 auto; height: 1px; background: var(--line);
  }

  .wf-source {
    display: flex; align-items: center; gap: 0.5rem;
    font-size: 0.775rem; color: var(--ink-soft); padding: 0.28rem 0;
  }
  .wf-dot {
    width: 6px; height: 6px; border-radius: 50%; flex: none;
    background: var(--accent-2);
  }
  .wf-source__what { color: var(--ink-faint); font-size: 0.72rem; }

  /* ---- Cards ---------------------------------------------------------- */
  .wf-card {
    background: var(--surface); border: 1px solid var(--line);
    border-radius: 8px; padding: 0.95rem 1.1rem; margin-bottom: 0.8rem;
  }

  /* ---- Progress rows -------------------------------------------------- */
  .wf-step {
    display: flex; gap: 0.65rem; align-items: flex-start;
    padding: 0.42rem 0; border-bottom: 1px solid var(--line-soft);
  }
  .wf-step:last-child { border-bottom: none; }
  .wf-step__mark {
    width: 1.15rem; flex: none; text-align: center; font-size: 0.8rem;
    line-height: 1.5;
  }
  .wf-step__who {
    font-size: 0.835rem; font-weight: 600; color: var(--ink); display: block;
  }
  .wf-step__what {
    font-size: 0.735rem; color: var(--ink-soft); display: block;
    margin-top: 0.06rem; line-height: 1.4;
  }
  .wf-step--done .wf-step__mark { color: var(--good); }
  .wf-step--now  .wf-step__mark { color: var(--accent); }
  .wf-step--now  .wf-step__who  { color: var(--accent); }
  .wf-step--idle .wf-step__mark { color: var(--ink-faint); }
  .wf-step--idle .wf-step__who,
  .wf-step--idle .wf-step__what { color: var(--ink-faint); }

  /* ---- Label / value rows --------------------------------------------- */
  .wf-fact {
    display: flex; justify-content: space-between; gap: 0.9rem;
    font-size: 0.795rem; padding: 0.29rem 0;
    border-bottom: 1px dotted var(--line);
  }
  .wf-fact:last-child { border-bottom: none; }
  .wf-fact__k { color: var(--ink-soft); flex: none; }
  .wf-fact__v { color: var(--ink); font-weight: 560; text-align: right; }

  /* ---- Badges --------------------------------------------------------- */
  .wf-badge {
    display: inline-block; font-size: 0.735rem; font-weight: 600;
    padding: 0.24rem 0.6rem; border-radius: 999px; border: 1px solid;
    margin-right: 0.3rem;
  }
  .wf-badge--good { color: var(--good); background: #EAF6F0; border-color: #C6E5D6; }
  .wf-badge--warn { color: var(--warn); background: #FDF3E4; border-color: #F0DCBC; }
  .wf-badge--bad  { color: var(--bad);  background: #FCEDEC; border-color: #F4D3D1; }
  .wf-badge--flat { color: var(--ink-soft); background: var(--surface-2); border-color: var(--line); }

  /* ---- Numbered form groups ------------------------------------------- */
  .wf-groupno {
    display: inline-block; width: 1.4rem; height: 1.4rem; line-height: 1.4rem;
    text-align: center; border-radius: 50%;
    background: linear-gradient(140deg, #4338CA, #0EA5A4);
    color: #fff; font-size: 0.72rem; font-weight: 720; margin-right: 0.5rem;
  }
  .wf-grouphead {
    font-size: 1rem; font-weight: 650; color: var(--ink); margin: 0 0 0.12rem 0;
  }
  .wf-groupsub {
    font-size: 0.78rem; color: var(--ink-soft); margin: 0 0 0.75rem 1.9rem;
    line-height: 1.45;
  }

  /* ---- The plan itself ------------------------------------------------ */
  .wf-blockhead {
    font-size: 0.93rem; font-weight: 650; color: var(--ink);
    margin: 0 0 0.5rem 0; padding-bottom: 0.38rem;
    border-bottom: 2px solid var(--line);
  }
  .wf-empty {
    border: 1px dashed var(--line); border-radius: 8px;
    padding: 2.4rem 1.5rem; text-align: center; color: var(--ink-faint);
    font-size: 0.86rem; line-height: 1.65;
  }
  .wf-note { font-size: 0.755rem; color: var(--ink-faint); line-height: 1.55; }

  /* ---- Streamlit's own chrome ----------------------------------------- */
  div[data-testid="stForm"] { border: none; padding: 0; }
  .stButton > button, .stDownloadButton > button {
    font-weight: 600; border-radius: 6px;
  }
  button[data-baseweb="tab"] { font-size: 0.9rem; font-weight: 600; }
  #MainMenu, footer { visibility: hidden; }

  /* Wide tables scroll inside themselves rather than widening the page. */
  .stMarkdown table { display: block; overflow-x: auto; max-width: 100%; }
</style>
""", unsafe_allow_html=True)


DATA_SOURCES = [
    ("Flight fares", "live search, recorded and replayed"),
    ("Hotel rates", "live search, recorded and replayed"),
    ("Attractions and dining", "live venue lookups"),
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


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _badge(text: str, tone: str = "flat") -> str:
    return f'<span class="wf-badge wf-badge--{tone}">{html.escape(text)}</span>'


def _facts(rows) -> str:
    body = "".join(
        f'<div class="wf-fact"><span class="wf-fact__k">{html.escape(str(k))}</span>'
        f'<span class="wf-fact__v">{html.escape(str(v))}</span></div>'
        for k, v in rows if v not in (None, "", 0))
    return f'<div class="wf-card">{body}</div>'


def _progress(states, container) -> None:
    """Draw the seven rows from a list of IDLE / NOW / DONE."""
    marks = {DONE: "✓", NOW: "▸", IDLE: "○"}
    names = {DONE: "done", NOW: "now", IDLE: "idle"}
    rows = "".join(
        f'<div class="wf-step wf-step--{names[state]}">'
        f'<span class="wf-step__mark">{marks[state]}</span>'
        f'<span><span class="wf-step__who">{html.escape(who)}</span>'
        f'<span class="wf-step__what">{html.escape(what)}</span></span></div>'
        for (who, what), state in zip(STEPS, states))
    container.markdown(f'<div class="wf-card">{rows}</div>',
                       unsafe_allow_html=True)


def _group_head(number: int, title: str, subtitle: str) -> None:
    st.markdown(
        f'<p class="wf-grouphead"><span class="wf-groupno">{number}</span>'
        f'{html.escape(title)}</p>'
        f'<p class="wf-groupsub">{html.escape(subtitle)}</p>',
        unsafe_allow_html=True)


def _travellers(answers) -> str:
    adults = answers.get("adults", 1)
    text = f"{adults} adult" + ("s" if adults != 1 else "")
    kids = answers.get("children", 0)
    if kids:
        text += f", {kids} child" + ("ren" if kids != 1 else "")
    return text


def _render_section(body: str) -> None:
    """
    Show one section as cards, one per part, or plainly if it has only one part.

    A flight or hotel section is three recommended options and a table of the
    rest, each under its own sub-heading. Run together as one markdown string
    they become a column of text with the boundaries buried in it.
    """
    blocks = split_blocks(body)
    if len(blocks) < 2:
        # No card: one border around a whole section is a border for no reason.
        # This used to open a styling <div> here and close it in a second
        # st.markdown call, which does nothing — Streamlit renders each call as
        # its own element, so the div never wrapped anything and the rules that
        # depended on it never applied.
        st.markdown(blocks[0][1] if blocks else body)
        return
    for heading, text in blocks:
        with st.container(border=True):
            if heading:
                st.markdown(
                    f'<p class="wf-blockhead">{html.escape(heading)}</p>',
                    unsafe_allow_html=True)
            st.markdown(text)


# ---------------------------------------------------------------------------
# Masthead
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="wf-mast">
  <p class="wf-eyebrow">Trip planning studio</p>
  <p class="wf-title">{BRAND}</p>
  <p class="wf-tag">{TAGLINE}</p>
  <div class="wf-rule"></div>
</div>
""", unsafe_allow_html=True)

FINISHED = bool(st.session_state.itinerary or st.session_state.failure)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
<div class="wf-brandbox">
  <p class="wf-brandbox__name">✦ {BRAND}</p>
  <p class="wf-brandbox__sub">Every price here was quoted by a real travel API.
     Where a figure had to be estimated instead, the plan says so.</p>
</div>
""", unsafe_allow_html=True)

    if FINISHED:
        answers = st.session_state.answers
        st.markdown('<div class="wf-sect">Your trip</div>',
                    unsafe_allow_html=True)
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

        st.markdown('<div class="wf-sect">Steps</div>', unsafe_allow_html=True)
        _progress([DONE] * len(STEPS), st)

        if st.session_state.facts:
            st.markdown('<div class="wf-sect">What each step found</div>',
                        unsafe_allow_html=True)
            st.markdown(_facts(st.session_state.facts), unsafe_allow_html=True)

        st.write("")
        if st.button("Plan another trip", use_container_width=True,
                     type="primary"):
            _reset()
            st.rerun()
    else:
        st.markdown('<div class="wf-sect">Steps it will run</div>',
                    unsafe_allow_html=True)
        _progress([IDLE] * len(STEPS), st)

        st.markdown('<div class="wf-sect">Where the prices come from</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="wf-card">' + "".join(
                f'<div class="wf-source"><span class="wf-dot"></span>'
                f'<span>{html.escape(name)}<br>'
                f'<span class="wf-source__what">{html.escape(what)}</span>'
                f'</span></div>'
                for name, what in DATA_SOURCES) + '</div>',
            unsafe_allow_html=True)

        st.markdown(
            '<p class="wf-note">Responses are recorded the first time they are '
            'fetched and replayed afterwards, so the same trip can be shown '
            'again without spending a monthly allowance.</p>',
            unsafe_allow_html=True)


# ===========================================================================
# STATE 1 — asking
# ===========================================================================
submitted = False

if not FINISHED:
    gutter_l, middle, gutter_r = st.columns([0.17, 0.66, 0.17])
    with middle:
        with st.form("trip", clear_on_submit=False, border=False):

            with st.container(border=True):
                _group_head(1, "Where and when",
                            "The route and the dates. Both are used to fetch "
                            "real fares, so they should be the dates you would "
                            "actually book.")
                destination = st.text_input(
                    "Destination", placeholder="Istanbul, Turkey")
                origin = st.text_input(
                    "Travelling from", placeholder="Lahore, Pakistan")
                # A month out, not today. Both fields used to open on today's
                # date, so the first press of the button always failed.
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
                            "The total, and what matters most to you. The "
                            "wording of the second changes how the money is "
                            "divided, not just how much is spent.")
                budget = st.number_input(
                    "Total budget for the whole trip, in US dollars",
                    min_value=0, value=3000, step=100,
                    help="Every figure in this system is USD — the APIs are "
                         "queried in USD and the cost model's thresholds are "
                         "USD amounts. Please convert before entering.")
                # Free text rather than three options. "luxury stay" moves the
                # room budget; "luxury trip" spreads it across room, food and
                # activities; "I can compromise" moves money out of the room and
                # the airfare into experiences. A dropdown expresses none of it.
                travel_style = st.text_input(
                    "What matters most on this trip?",
                    placeholder="a luxury stay / great food and lots to do / "
                                "I can compromise to keep it cheap / moderate")

            with st.container(border=True):
                _group_head(4, "Preferences",
                            "What to fill the days with, and anything that has "
                            "to be worked around.")
                interests = st.text_input(
                    "Interests", placeholder="museums, food, nightlife, hiking")
                special_requirements = st.text_input(
                    "Special requirements",
                    placeholder="dietary, accessibility, or leave blank")

            st.write("")
            submitted = st.form_submit_button(
                "Build my itinerary", type="primary", use_container_width=True)

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
<div class="wf-empty">
  Your plan appears here.<br>
  Fares and rooms are fetched, the budget is checked against what the trip really
  costs, and every day is verified present before anything is shown.
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
            st.markdown('<div class="wf-sect">Working</div>',
                        unsafe_allow_html=True)
            step_box, note_box, fact_box = st.empty(), st.empty(), st.empty()

            # The events the run reports, in order, replayed into step states by
            # progress_states — so what is shown here is derived from the run
            # rather than tracked separately and allowed to drift from it.
            state = {"events": [], "facts": []}
            _progress(progress_states([], conversation_done=True), step_box)

            def redraw():
                _progress(progress_states(state["events"],
                                          conversation_done=True), step_box)

            def on_progress(kind, *parts):
                """Told by the orchestrator as each phase begins and each search lands."""
                if kind == "step":
                    match = re.search(r"(\d+)", parts[0])     # "STEP 2 of 4"
                    if match:
                        state["events"].append(("phase", int(match.group(1))))
                        redraw()
                elif kind == "detail":
                    label, value = parts[0], parts[1]
                    state["facts"].append((label, value))
                    fact_box.markdown(_facts(state["facts"]),
                                      unsafe_allow_html=True)
                    if label in SEARCH_ROW:
                        state["events"].append(("search", label))
                        redraw()
                elif kind == "budget":
                    note_box.markdown(
                        f'<p class="wf-note">{html.escape(parts[1])}</p>',
                        unsafe_allow_html=True)

            set_progress_hook(on_progress)
            # Both places: the page's expander, and the console the demonstration
            # is being watched from. sys.stdout rather than sys.__stdout__ so
            # whatever Streamlit has put in front of the terminal is respected.
            captured = TeeStream(sys.stdout)
            print(f"\n  Planning {st.session_state.answers['destination']} "
                  f"from the web interface "
                  f"(conversation {st.session_state.conversation_id[:8]}).")
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
# STATE 2 — showing
# ===========================================================================
else:
    if st.session_state.failure:
        st.markdown('<div class="wf-sect">The run did not finish</div>',
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
        # that under the heading "Itinerary" would misdescribe it.
        refused = "CANNOT BE PLANNED WITHIN THAT BUDGET" in itinerary

        st.markdown(
            f'<div class="wf-sect">'
            f'{html.escape(str(answers.get("destination", "Your trip")))} · '
            f'{html.escape(str(answers.get("nights", "?")))} nights · '
            f'{html.escape(_travellers(answers))}</div>',
            unsafe_allow_html=True)

        checks = [_badge(text, tone)
                  for text, tone in plan_checks(console, refused)]
        if checks:
            st.markdown("".join(checks), unsafe_allow_html=True)

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
                st.markdown(itinerary)          # no headings: show it whole
            else:
                for tab, (name, sections) in zip(
                        st.tabs([name for name, _ in tabs]), tabs):
                    with tab:
                        for title, body in sections:
                            if name == "Day by day":
                                days = split_days(body)
                                if len(days) > 1:
                                    for index, (label, text) in enumerate(days):
                                        with st.expander(label,
                                                         expanded=index == 0):
                                            _render_section(text)
                                    continue
                            _render_section(body)

        st.write("")
        download, terminal = st.columns([0.3, 0.7])
        download.download_button(
            "Download the plan",
            data=itinerary,
            file_name=("itinerary-" +
                       re.sub(r"[^A-Za-z0-9]+", "-",
                              str(answers.get("destination", "trip"))
                              ).strip("-") + ".md"),
            mime="text/markdown",
            use_container_width=True,
        )
        if console:
            with terminal.expander("Terminal output for this run"):
                st.code(console, language="text")
