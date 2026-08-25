# Demonstrations

Scripts for showing the work — to a supervisor, or in the viva.

**Every one of these runs with no API keys, no internet and no quota.** That is
deliberate. The free tiers this project uses are exhaustible, and a demonstration
that needs a working API is one that cannot be given on the day the quota runs
out, which is exactly the day it will be needed.

## What to run

```bash
python trip_planner/demos/compare_all_approaches.py          # show this first
python trip_planner/demos/approach_a_single_llm.py           # one approach, in detail
python trip_planner/demos/approach_b_six_agent_naive.py
python trip_planner/demos/approach_c_six_agent_tuned.py
python trip_planner/demos/approach_d_three_agent_direct.py   # the one that ships
```

Or use `run.bat` and pick options 1–5.

Add `--no-pause` to run straight through without the "press Enter" stops.

## The two modes

| Mode | Command | What happens | Costs |
|---|---|---|---|
| **Playback** | *(default)* | Replays the measurement recorded in `trip_planner/evaluation/results/` — the same timings, the same cost, the same itinerary text that run really produced | Nothing at all |
| **Live** | `--live` | Executes the architecture now, through the same code path the evaluation uses. The model runs for real; travel responses replay from disk | Model quota only |
| **Fully live** | `--live --live-apis` | As above, but the travel APIs are called for real too | Model quota **and** monthly flight/hotel quota |

Playback is the default because it always works. It is labelled as playback on
screen every time, with the date of the run it is replaying and the model that
produced it — presenting a recorded run as a live one would be dishonest, and a
supervisor asking "is this running now?" should get the answer from the screen.

The two modes narrate the same steps in the same order, because they describe
the same architecture. The only difference is whether the numbers are being
produced now or were produced earlier and recorded.

## What each demo shows

Every approach demo prints the same six things, so they can be compared directly:

1. **What this approach is** — one paragraph
2. **How it works** — the numbered steps it actually performs
3. **What to watch for** — the point to make to your supervisor
4. **The itinerary it produced** — real output, not a summary
5. **What it cost** — requests, prompt vs completion tokens, money, time by phase
6. **Was any of it real?** — how many of its quoted prices match a fare the APIs
   actually returned

That last section is the one to dwell on. In the recorded run, approach A quoted
29 prices and matched none of them to a fare the APIs returned — 1.7% averaged
over its five runs. Approach C averaged 56% and approach D 47%. The contrast
between "no tools" and "tools" is the project's central finding; the gap between
C and D is inside both their 95% intervals, so it is not a finding at all, and
the dissertation says so.

## Layout

| File | What it is |
|---|---|
| `compare_all_approaches.py` | All four side by side, with the table and what to say about it |
| `approach_a_single_llm.py` | Approach A, in detail |
| `approach_b_six_agent_naive.py` | Approach B, in detail |
| `approach_c_six_agent_tuned.py` | Approach C, in detail |
| `approach_d_three_agent_direct.py` | Approach D, in detail |
| `show_agent_messages.py` | The A2A protocol working, message by message: who may talk to whom, a real exchange, an undeclared pair being refused, and the conversation replayed from its own history. No model, no network, under a second. |
| `_presenter.py` | The narration, in one place. The approach files hold only their own description |

Each approach file describes its own approach and nothing else; the presentation
logic is not duplicated across them.

## A caution worth stating

Playback shows one recorded scenario, run once. It is real measured output, and
it is a single observation — the demos say so at the end of every run, and so
does the dissertation. If a supervisor asks how many scenarios this covers, the
honest answer is on the screen: 1 of 20 designed.
