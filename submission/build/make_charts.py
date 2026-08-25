"""Draws the results charts from the measured data."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

from evaluation import measured
from evaluation.measured import ARM_ORDER
from submission.build.figlib import (AQUA, BLUE, DPI, GREY, INK, INK_2, ORANGE, RED,
                            ROOT, save_chart)

GRID = "#e3e2dd"
SURFACE = "#fcfcfb"

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


def _style_axis(ax) -> None:
    """Recessive grid and axes; the data should be the loudest thing present."""
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.yaxis.grid(False)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(length=0)


def _scope() -> str:
    c = measured.coverage()
    note = (f"{c['scenarios_measured']} of {c['scenarios_designed']} designed "
            f"scenarios ({', '.join(c['scenario_ids'])}), "
            f"{c['repeats_per_arm']} runs of each architecture")
    if c["has_repeats"]:
        note += "  ·  every bar is a mean over those runs"
    else:
        note += "  [no repeats, so run-to-run variance is unmeasured]"
    return (f"{note}  ·  model {c['model']}  ·  API layer in {c['api_mode']} mode  ·  "
            f"LLM requests counted via LiteLLM callbacks, not estimated")


def _error_bars(metric: str):
    """
    Asymmetric error bars from the recorded 95% intervals.

    Returned in the two-row shape matplotlib expects. None when the run had no
    repeats, so a chart never draws a whisker it cannot justify.
    """
    if not measured.coverage()["has_repeats"]:
        return None
    lo, hi = [], []
    for code in ARM_ORDER:
        try:
            b = measured.spread(code, metric)
        except measured.MissingMeasurement:
            return None
        lo.append(max(0.0, b["mean"] - b["ci95_low"]))
        hi.append(max(0.0, b["ci95_high"] - b["mean"]))
    return [lo, hi]


def bar_panel(ax, values, title, direction, fmt, *, labels=None,
              colours=None, xmax=None, xerr=None) -> None:
    labels = labels or [ARM_LABELS[c] for c in ARM_ORDER]
    ypos = list(range(len(labels)))
    ax.barh(ypos, values, color=colours or BLUE, height=0.62, zorder=3,
            xerr=xerr, error_kw=dict(ecolor=INK, elinewidth=1.1, capsize=3,
                                     capthick=1.1, zorder=4))
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK, pad=8, loc="left")
    ax.set_xlabel(direction, fontsize=8.5, color=INK_2, labelpad=6)

    span = xmax or (max(values) if max(values) else 1)
    ax.set_xlim(0, span * (1.0 if xmax else 1.22))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _, f=fmt: f(v)))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    # Place each value label beyond its whisker rather than at the bar end,
    # otherwise the text sits on top of the error bar and neither is readable.
    upper = xerr[1] if xerr else [0] * len(values)
    for y, value, err in zip(ypos, values, upper):
        ax.text(value + err + span * 0.025, y, fmt(value), va="center", ha="left",
                fontsize=9.5, color=INK, fontweight="bold")
    _style_axis(ax)


# ------------------------------------------------------- 1. cost efficiency
def chart_efficiency() -> str:
    """Four cost measures as small multiples — never two scales on one axis."""
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0))
    panels = [
        ("avg_llm_calls", "LLM requests per trip", lambda v: f"{v:,.0f}"),
        ("avg_total_tokens", "Tokens per trip", lambda v: f"{v:,.0f}"),
        ("avg_cost_usd", "Cost per trip", lambda v: f"${v:,.4f}"),
        ("avg_latency", "Wall-clock time per trip", lambda v: f"{v:,.0f}s"),
    ]
    metric_for = {"avg_llm_calls": "llm_calls", "avg_total_tokens": "total_tokens",
                  "avg_cost_usd": "cost_usd", "avg_latency": "latency"}
    for ax, (key, title, fmt) in zip(axes.flat, panels):
        bar_panel(ax, [measured.arm_metric(c, key) for c in ARM_ORDER],
                  title, "lower is better  ·  whiskers are 95% intervals", fmt,
                  xerr=_error_bars(metric_for[key]))

    fig.suptitle("Cost of each architecture, measured", fontsize=13,
                 fontweight="bold", color=INK, x=0.012, ha="left", y=0.985)
    fig.text(0.012, 0.945, _scope(), fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.02, 1, 0.92], h_pad=3.4, w_pad=2.6)
    return save_chart(fig, "efficiency.png")


# ----------------------------------------------------- 2. why tuning worked
def chart_token_decomposition() -> str:
    """
    Where each arm's tokens go.

    The ranking chart says the tuned arm is cheaper; this one says why. Prompt
    and completion tokens are separated because they are not interchangeable:
    prompt tokens are re-sent context and tool schemas, completion tokens are
    the itinerary itself, and on this model output costs several times input.
    """
    # Means across repeats, so the totals here match the results table exactly.
    prompt = [measured.token_split(c)["prompt_tokens"] for c in ARM_ORDER]
    completion = [measured.token_split(c)["completion_tokens"] for c in ARM_ORDER]

    fig, ax = plt.subplots(figsize=(10.4, 4.2))
    ypos = list(range(len(ARM_ORDER)))
    ax.barh(ypos, prompt, color=ORANGE, height=0.6, zorder=3,
            label="prompt tokens — re-sent context and tool schemas")
    ax.barh(ypos, completion, left=prompt, color=BLUE, height=0.6, zorder=3,
            label="completion tokens — the itinerary text itself")
    ax.set_yticks(ypos)
    ax.set_yticklabels([ARM_LABELS[c] for c in ARM_ORDER], fontsize=9)
    ax.invert_yaxis()
    ax.set_title("Where the tokens go", fontsize=12, fontweight="bold",
                 loc="left", color=INK, pad=8)
    ax.set_xlabel("tokens per trip  ·  lower is better", fontsize=8.5,
                  color=INK_2, labelpad=6)
    total = max(p + c for p, c in zip(prompt, completion))
    ax.set_xlim(0, total * 1.28)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    for y, (p, comp) in enumerate(zip(prompt, completion)):
        share = p / (p + comp) * 100 if (p + comp) else 0
        ax.text(p + comp + total * 0.015, y,
                f"{p + comp:,}   ({share:.0f}% prompt)",
                va="center", ha="left", fontsize=9.5, fontweight="bold", color=INK)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    _style_axis(ax)
    fig.text(0.012, 0.015, _scope(), fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.07, 1, 1])
    return save_chart(fig, "token_decomposition.png")


def chart_tuning_effect() -> str:
    """B vs C: how much of the multi-agent penalty was implementation, not design."""
    metrics = [
        ("avg_llm_calls", "LLM requests", lambda v: f"{v:,.0f}"),
        ("avg_total_tokens", "Tokens", lambda v: f"{v:,.0f}"),
        ("avg_cost_usd", "Cost (USD)", lambda v: f"${v:,.4f}"),
        ("avg_latency", "Seconds", lambda v: f"{v:,.0f}s"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(13.6, 3.8))

    metric_for = {"avg_llm_calls": "llm_calls", "avg_total_tokens": "total_tokens",
                  "avg_cost_usd": "cost_usd", "avg_latency": "latency"}
    for ax, (key, title, fmt) in zip(axes, metrics):
        values = [measured.arm_metric(c, key) for c in ("B", "C")]
        # Whiskers here too. The shared scope line promises 95% intervals, and a
        # chart that omits them while the caption claims them is worse than one
        # without the claim.
        xerr = None
        if measured.coverage()["has_repeats"]:
            spans = [measured.spread(c, metric_for[key]) for c in ("B", "C")]
            xerr = [[max(0.0, b["mean"] - b["ci95_low"]) for b in spans],
                    [max(0.0, b["ci95_high"] - b["mean"]) for b in spans]]
        ax.barh([0, 1], values, color=[GREY, BLUE], height=0.55, zorder=3,
                xerr=xerr, error_kw=dict(ecolor=INK, elinewidth=1.1, capsize=3,
                                         capthick=1.1, zorder=4))
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["6 agents\nnaive", "6 agents\ntuned"], fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=10.5, fontweight="bold", loc="left", color=INK)
        span = max(values) if max(values) else 1
        ax.set_xlim(0, span * 1.34)
        # fmt is bound as a default argument. Without it every panel's formatter
        # closes over the same loop variable, so all four axes render with
        # whichever formatter the loop finished on.
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _, f=fmt: f(v)))
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
        upper = xerr[1] if xerr else [0, 0]
        for y, value, err in zip([0, 1], values, upper):
            ax.text(value + err + span * 0.03, y, fmt(value), va="center",
                    fontsize=9.5, color=INK, fontweight="bold")
        if values[0]:
            drop = (1 - values[1] / values[0]) * 100
            ax.text(0.98, 0.06, f"-{drop:.0f}%", transform=ax.transAxes,
                    ha="right", fontsize=13, fontweight="bold", color=BLUE)
        _style_axis(ax)

    fig.suptitle("Effect of tuning the multi-agent architecture (B to C)",
                 fontsize=12.5, fontweight="bold", color=INK, x=0.012, ha="left")
    fig.text(0.012, 0.90,
             "Same six roles, same data path, same model. Only prompt economics changed.",
             fontsize=8.5, color=INK_2, ha="left")
    fig.text(0.012, 0.015, _scope(), fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.08, 1, 0.84], w_pad=3.2)
    return save_chart(fig, "tuning_effect.png")


# --------------------------------------------------------- 3. groundedness
def chart_groundedness() -> str:
    """
    The quality counterweight: cheapness means nothing if the data is invented.

    Two panels because the two signals are not equally strong. Price matching is
    robust — landing within 2% of a real quoted fare is not something prior
    knowledge delivers. Name matching is weak: a model with no tool access can
    name the obvious airline for a route. Showing them together, with that
    stated, prevents the weaker signal from carrying the claim.
    """
    # Means across every repeat, so this chart cannot disagree with the table in
    # Section 6.2. Reading run one instead put 50% here and 56% in the text.
    prices = [measured.arm_metric(c, "avg_prices_grounded_pct") for c in ARM_ORDER]
    quoted = [measured.groundedness(c)["prices_quoted"] for c in ARM_ORDER]
    airlines = [measured.arm_metric(c, "avg_airlines_grounded") /
                max(measured.groundedness(c)["airlines_available"], 1) * 100
                for c in ARM_ORDER]

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.0))

    bar_panel(axes[0], prices,
              "Quoted prices that match a real fare or nightly rate",
              "higher is better  ·  overlapping whiskers mean the gap is within noise",
              lambda v: f"{v:,.0f}%",
              colours=[GREY, BLUE, BLUE, BLUE], xmax=100,
              xerr=_error_bars("prices_grounded_pct"))
    for y, (pct, n) in enumerate(zip(prices, quoted)):
        axes[0].text(2, y + 0.40, f"{n} prices quoted in run 1", fontsize=7.4,
                     color=INK_2, va="center")

    bar_panel(axes[1], airlines,
              "Airlines named that appear in the flight results",
              "weak evidence — the obvious airline for a route is guessable",
              lambda v: f"{v:,.0f}%",
              colours=[GREY, BLUE, BLUE, BLUE], xmax=100)

    fig.suptitle("Groundedness: is the itinerary built from retrieved data?",
                 fontsize=12.5, fontweight="bold", color=INK, x=0.012, ha="left")
    fig.text(0.012, 0.015, _scope(), fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.07, 1, 0.91], w_pad=3.0)
    return save_chart(fig, "groundedness.png")


# ---------------------------------------------------- 4. protocol conformance
def chart_protocol_conformance() -> str:
    """
    Every conformance check, pass or fail, named.

    Drawn as a categorical pass/fail strip rather than a percentage, because "3
    of 9" invites the reader to average defects of very different severity. A
    reader should see which check failed, not a score.
    """
    checks = measured.protocol()["a2a_checks"] + measured.protocol()["mcp_checks"]
    # Drop the parenthetical citation from the display label. Truncating with an
    # ellipsis instead left "(proposal S3.10 ta..." on the chart, which reads as
    # a rendering bug rather than an editorial choice.
    labels = [f"{c['id']}   {c['claim'].split(' (')[0]}" for c in checks]
    passed = [c["passed"] for c in checks]

    fig, ax = plt.subplots(figsize=(13.0, 4.6))
    ypos = list(range(len(checks)))
    ax.barh(ypos, [1] * len(checks),
            color=[AQUA if p else RED for p in passed], height=0.6, zorder=3)
    ax.set_yticks(ypos)
    ax.set_yticklabels([""] * len(checks))
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    for y, (text, ok) in enumerate(zip(labels, passed)):
        wrapped = text if len(text) < 96 else text[:93] + "..."
        ax.text(0.012, y, wrapped, va="center", ha="left", fontsize=8.6,
                color="white", fontweight="bold" if not ok else "normal", zorder=5)
        ax.text(1.008, y, "PASS" if ok else "FAIL", va="center", ha="left",
                fontsize=9, fontweight="bold", color=AQUA if ok else RED,
                transform=ax.get_yaxis_transform())
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)

    s = measured.protocol_summary()
    fig.suptitle("Protocol conformance: A2A and MCP", fontsize=12.5,
                 fontweight="bold", color=INK, x=0.012, ha="left")
    fig.text(0.012, 0.90,
             f"{s['passed']} of {s['total_checks']} checks pass. "
             f"Failing: {', '.join(s['failed_ids'])}. "
             f"No network, no LLM, no API key required — so this is the one part of "
             f"the evaluation that is not quota-limited.",
             fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.02, 0.945, 0.86])
    return save_chart(fig, "protocol_conformance.png")


# ------------------------------------------------------------ 5. budget gate
def chart_budget_gate() -> str:
    """
    The gate's decision on all twenty scenarios, plus why it got one wrong.

    Left panel: each scenario's budget as a multiple of the estimated minimum.
    A ratio below 1.0 must be refused. Plotting the ratio rather than the raw
    budget puts every scenario on one comparable scale and makes the decision
    boundary a single vertical line.

    Right panel: the calibration failure that explains the miss — the model's
    "cheapest bookable" flight anchor against fares the API actually returned.
    """
    rows = measured.budget_gate()["decision_table"]
    rows = sorted(rows, key=lambda r: r["budget_vs_minimum"])
    labels = [f"{r['scenario']}  {r['destination'][:12]}" for r in rows]
    ratios = [r["budget_vs_minimum"] for r in rows]
    colours = []
    for r in rows:
        if not r["agrees"]:
            colours.append(RED)
        elif r["gate_refused"]:
            colours.append(ORANGE)
        else:
            colours.append(BLUE)

    fig = plt.figure(figsize=(13.4, 6.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.65, 1.0], wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])

    ypos = list(range(len(rows)))
    ax.barh(ypos, ratios, color=colours, height=0.66, zorder=3)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.invert_yaxis()
    ax.axvline(1.0, color=INK, linewidth=1.4, zorder=4)
    # Annotate above the first bar. The y axis is inverted, so the top of the
    # plot is a NEGATIVE index — placing this at len(rows) put it through the
    # bottom bar instead.
    ax.text(1.06, -0.95, "decision boundary: budget = estimated minimum",
            fontsize=8, color=INK_2, va="center", ha="left")
    # The word beside each bar is the gate's own verdict, which it reaches against
    # its COMFORTABLE estimate, while the bar length is a ratio against the MINIMUM.
    # Two denominators, so the words need not run in the same order as the bars —
    # SC-16 reads "workable" between two "comfortable" bars for that reason. Saying
    # so on the axis stops it looking like a plotting error.
    ax.set_xlabel("stated budget as a multiple of the estimated minimum cost\n"
                  "(the word beside each bar is the gate's own verdict, which it\n"
                  "judges against its comfortable estimate, not against this minimum)",
                  fontsize=8.2, color=INK_2, labelpad=6)
    ax.set_title("Every scenario against the feasibility floor", fontsize=11,
                 fontweight="bold", loc="left", color=INK, pad=8)
    ax.set_xlim(0, max(ratios) * 1.16)
    for y, r in zip(ypos, rows):
        note = "refused" if r["gate_refused"] else r["verdict"].replace("_", " ")
        ax.text(r["budget_vs_minimum"] + max(ratios) * 0.012, y, note,
                va="center", fontsize=7.8,
                color=RED if not r["agrees"] else INK_2,
                fontweight="bold" if not r["agrees"] else "normal")
    _style_axis(ax)

    # Right: the calibration failure behind the miss.
    ax2 = fig.add_subplot(gs[0, 1])
    e = measured.gate_external_validity()
    names = ["model's 'cheapest\nbookable' anchor",
             "cheapest fare the\nAPI actually returned",
             "median fare the\nAPI actually returned"]
    values = [e["estimated_minimum"], e["cheapest_real_fare"], e["median_real_fare"]]
    ax2.barh([0, 1, 2], values, color=[RED, AQUA, GREY], height=0.6, zorder=3)
    ax2.set_yticks([0, 1, 2])
    ax2.set_yticklabels(names, fontsize=8.4)
    ax2.invert_yaxis()
    ax2.set_title(f"Why: the flight anchor is too low\n{e['route']}, "
                  f"{e['fares_recorded']} recorded fares",
                  fontsize=11, fontweight="bold", loc="left", color=INK, pad=8)
    ax2.set_xlim(0, max(values) * 1.3)
    ax2.set_xlabel("US dollars, return, one traveller", fontsize=8.5,
                   color=INK_2, labelpad=6)
    for y, v in zip([0, 1, 2], values):
        ax2.text(v + max(values) * 0.02, y, f"${v:,.0f}", va="center",
                 fontsize=9.5, fontweight="bold", color=INK)
    # Sits in the empty band directly beneath the anchor bar, in data
    # coordinates. In axes coordinates it landed on top of the median-fare bar.
    ax2.text(max(values) * 0.02, 0.62,
             f"{e['minimum_anchor_error_pct']:+.0f}% against the cheapest real fare",
             fontsize=9.5, fontweight="bold", color=RED, va="center", ha="left")
    _style_axis(ax2)

    a = measured.gate_agreement()
    misses = measured.gate_misses()
    miss_text = (", ".join(m["scenario"] for m in misses) or "none")
    fig.suptitle("Budget feasibility gate: 20 scenarios, no LLM, no API calls",
                 fontsize=12.5, fontweight="bold", color=INK, x=0.012, ha="left")
    fig.text(0.012, 0.935,
             f"Cohen's kappa {a['cohens_kappa']} against designed intent "
             f"(accuracy {a['accuracy_pct']}% is flattered by {a['true_negative']} of "
             f"{a['n']} cases being affordable). Missed: {miss_text}.",
             fontsize=8.5, color=INK_2, ha="left")
    fig.tight_layout(rect=[0, 0.02, 1, 0.90])
    return save_chart(fig, "budget_gate.png")


CHARTS = [
    chart_efficiency,
    chart_token_decomposition,
    chart_tuning_effect,
    chart_groundedness,
    chart_protocol_conformance,
    chart_budget_gate,
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    failures = 0
    for builder in CHARTS:
        try:
            path = builder()
            print(f"  ok   {os.path.relpath(path, ROOT)}")
        except Exception as exc:
            failures += 1
            print(f"  FAIL {builder.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(CHARTS) - failures}/{len(CHARTS)} charts written at {DPI} dpi")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
