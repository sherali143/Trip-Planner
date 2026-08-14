"""
Generate results charts from the measured evaluation data.

Reads comparison/results/comparison_results.json — nothing here is hardcoded, so
the figures cannot drift from the numbers they claim to show. Re-run after any
evaluation run to refresh every chart.

Design notes (why the charts look the way they do):
  * Horizontal bars: the arm names are long ("6 AGENTS (optimised)"), and
    horizontal bars give them room without rotated tick labels.
  * ONE hue for every bar in a panel. Colouring each bar darker-where-bigger
    would double-encode bar length as hue, spending the only free channel on
    information the length already carries.
  * Identity comes from the axis label, not from colour, so no legend is needed
    and the figures stay readable in greyscale print.
  * Every panel title states the direction, because "lower is better" for cost
    and "higher is better" for groundedness sit side by side in the same report.
  * Values are labelled directly; a marker should not have to measure a bar
    against a gridline.
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "comparison", "results", "comparison_results.json")
OUT = os.path.join(ROOT, "figures")

# From the validated reference palette (light mode).
BLUE = "#2a78d6"          # categorical slot 1 — the single series hue
GREY = "#b8b7b0"          # de-emphasis, for context bars
INK = "#0b0b0b"           # primary text
INK_2 = "#52514e"         # secondary text
SURFACE = "#fcfcfb"
GRID = "#e3e2dd"

ARM_ORDER = ["A", "B", "C", "D"]
ARM_LABELS = {
    "A": "A  Single LLM\n(no agents, no tools)",
    "B": "B  6 agents\n(naive)",
    "C": "C  6 agents\n(tuned)",
    "D": "D  3 agents\n(direct API)",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "text.color": INK,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def load():
    if not os.path.exists(RESULTS):
        sys.exit(f"No results at {RESULTS}. Run: python -m comparison.run_comparison")
    with open(RESULTS, encoding="utf-8") as fh:
        data = json.load(fh)
    if "arms" not in data:
        sys.exit("Results file has no 'arms' section — re-run the comparison.")
    return data


def _style_axis(ax):
    """Recessive grid and axes; the data should be the loudest thing present."""
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.yaxis.grid(False)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(length=0)


def bar_panel(ax, values, title, direction, fmt, highlight=None):
    """One horizontal bar panel: arms on y, one metric on x."""
    labels = [ARM_LABELS[c] for c in ARM_ORDER]
    ypos = range(len(ARM_ORDER))
    colours = [
        BLUE if (highlight is None or code in highlight) else GREY
        for code in ARM_ORDER
    ]

    ax.barh(list(ypos), values, color=colours, height=0.62, zorder=3)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()  # A at the top, reading order
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK, pad=8, loc="left")
    # Direction goes under the axis, not above the plot: placing it at y=1.02
    # in axes coords put it straight through the title.
    ax.set_xlabel(direction, fontsize=8.5, color=INK_2, labelpad=6)

    span = max(values) if max(values) else 1
    ax.set_xlim(0, span * 1.22)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt(v)))
    # Cap tick count so long formatted values (60,000 / $0.0500) cannot collide.
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, prune=None))

    for y, value in zip(ypos, values):
        ax.text(value + span * 0.025, y, fmt(value), va="center", ha="left",
                fontsize=9.5, color=INK, fontweight="bold")
    _style_axis(ax)


def chart_efficiency(data):
    """Four cost measures as small multiples — never two scales on one axis."""
    arms = data["arms"]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.8))

    panels = [
        ("avg_llm_calls", "LLM requests per trip", "lower is better",
         lambda v: f"{v:,.0f}"),
        ("avg_total_tokens", "Tokens per trip", "lower is better",
         lambda v: f"{v:,.0f}"),
        ("avg_cost_usd", "Cost per trip", "lower is better",
         lambda v: f"${v:,.4f}"),
        ("avg_latency", "Time per trip", "lower is better",
         lambda v: f"{v:,.0f}s"),
    ]
    for ax, (key, title, direction, fmt) in zip(axes.flat, panels):
        bar_panel(ax, [arms[c][key] for c in ARM_ORDER], title, direction, fmt)

    fig.suptitle("Cost of each architecture, measured", fontsize=13,
                 fontweight="bold", color=INK, x=0.012, ha="left", y=0.985)
    scope = _scope(data)
    fig.text(0.012, 0.945, scope, fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.02, 1, 0.92], h_pad=3.2, w_pad=2.4)
    path = os.path.join(OUT, "fig_efficiency.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def chart_groundedness(data):
    """The quality counterweight: cheapness means nothing if the data is invented."""
    arms = data["arms"]
    values = [arms[c]["avg_prices_grounded_pct"] for c in ARM_ORDER]

    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    # Emphasis rather than one flat hue: the finding is that the tool-less arm
    # scores zero, so the tool-using arms carry the accent and A recedes.
    bar_panel(ax, values,
              "Prices in the itinerary that match a real fare or nightly rate",
              "higher is better  ·  0% means every price was invented",
              lambda v: f"{v:,.0f}%",
              highlight={"B", "C", "D"})
    ax.set_xlim(0, 100)
    fig.text(0.012, 0.02, _scope(data), fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    path = os.path.join(OUT, "fig_groundedness.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def chart_tuning_effect(data):
    """B vs C: how much of the multi-agent penalty was implementation, not design."""
    arms = data["arms"]
    metrics = [
        ("avg_llm_calls", "LLM requests", lambda v: f"{v:,.0f}"),
        ("avg_total_tokens", "Tokens", lambda v: f"{v:,.0f}"),
        ("avg_cost_usd", "Cost (USD)", lambda v: f"${v:,.4f}"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))

    for ax, (key, title, fmt) in zip(axes, metrics):
        pair = ["B", "C"]
        values = [arms[c][key] for c in pair]
        ax.barh([0, 1], values, color=[GREY, BLUE], height=0.55, zorder=3)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["6 agents\nnaive", "6 agents\ntuned"], fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=10.5, fontweight="bold", loc="left", color=INK)
        span = max(values) if max(values) else 1
        ax.set_xlim(0, span * 1.3)
        # Bind fmt as a default argument. Without it every panel's formatter
        # closes over the same loop variable, so all three axes rendered with
        # whichever formatter the loop finished on — the currency one, which
        # printed "$5.0000" on the LLM-requests axis.
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _, f=fmt: f(v)))
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
        for y, value in zip([0, 1], values):
            ax.text(value + span * 0.03, y, fmt(value), va="center", fontsize=9.5,
                    color=INK, fontweight="bold")
        if values[0]:
            drop = (1 - values[1] / values[0]) * 100
            ax.text(0.98, 0.06, f"−{drop:.0f}%", transform=ax.transAxes,
                    ha="right", fontsize=12, fontweight="bold", color=BLUE)
        _style_axis(ax)

    fig.suptitle("Effect of tuning the multi-agent architecture (B → C)",
                 fontsize=12.5, fontweight="bold", color=INK, x=0.012, ha="left")
    fig.text(0.012, 0.90,
             "Same six agents and the same data path; only prompt economics changed.",
             fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.02, 1, 0.84], w_pad=3.0)
    path = os.path.join(OUT, "fig_tuning_effect.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _scope(data):
    ids = data.get("scenario_ids") or []
    prov = data.get("provenance", {})
    status = data.get("status", "")
    note = f"{len(ids)} scenario(s): {', '.join(ids)}" if ids else "scenario set unknown"
    if status == "partial":
        note += "  [PARTIAL RUN]"
    return (f"{note}  ·  model {prov.get('model', '?')}  ·  "
            f"LLM requests counted via LiteLLM callbacks, not estimated")


def main():
    data = load()
    made = [chart_efficiency(data), chart_groundedness(data), chart_tuning_effect(data)]
    for path in made:
        print("wrote", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
