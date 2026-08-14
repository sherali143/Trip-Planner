"""
Generate architecture and flow diagrams.

Drawn with matplotlib rather than Graphviz because the `dot` binary is not
installed on this machine, and a figure that only renders on one developer's
setup is not much use in a report.

Layout rule used throughout: every box is placed on an explicit grid and text is
sized to fit the box it sits in. Nothing is auto-laid-out, so labels cannot drift
on top of each other when the figure is resized.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BLUE = "#2a78d6"
BLUE_FILL = "#e4eefb"
AQUA = "#1baf7a"
AQUA_FILL = "#e2f5ee"
ORANGE = "#eb6834"
ORANGE_FILL = "#fdeae2"
GREY = "#8a8983"
GREY_FILL = "#efeeea"
INK = "#0b0b0b"
INK_2 = "#52514e"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def box(ax, x, y, w, h, text, *, edge=BLUE, fill=BLUE_FILL, fontsize=9,
        weight="normal", text_colour=INK, radius=0.02):
    """A rounded box with text centred inside it."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        linewidth=1.4, edgecolor=edge, facecolor=fill, zorder=2,
    ))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=text_colour, weight=weight, zorder=3,
            linespacing=1.45)


def arrow(ax, start, end, *, colour=GREY, style="-|>", lw=1.4, dashed=False):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle=style, mutation_scale=12,
        linewidth=lw, color=colour, zorder=1,
        linestyle="--" if dashed else "-",
        shrinkA=2, shrinkB=2,
    ))


def label(ax, x, y, text, *, fontsize=8.5, colour=INK_2, ha="center", weight="normal"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize, color=colour,
            weight=weight, zorder=4)


def new_canvas(w, h, title, subtitle=None):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.text(0, 99, title, ha="left", va="top", fontsize=13.5, weight="bold", color=INK)
    if subtitle:
        ax.text(0, 94.5, subtitle, ha="left", va="top", fontsize=9, color=INK_2)
    return fig, ax


def save(fig, name):
    path = os.path.join(ROOT, "figures", name)
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", os.path.relpath(path, ROOT))
    return path


# ---------------------------------------------------------------- figure 1
def fig_system_architecture():
    fig, ax = new_canvas(12, 7.8,
                         "System architecture",
                         "Four layers. Every inter-agent message travels over the A2A "
                         "protocol; the MCP server is the only route to an external API.")

    # A dedicated left gutter holds the layer names. Nothing is ever drawn in
    # it, so a connector can never cross a label — the earlier version routed
    # arrows straight through "LAYER 2" and "LAYER 4".
    GUTTER = 15.0
    bands = [
        (76, 11, "LAYER 1\nUser interface"),
        (58, 11, "LAYER 2\nUnderstanding\nthe request"),
        (30, 16, "LAYER 3\nData retrieval"),
        (8, 11, "LAYER 4\nItinerary assembly"),
    ]
    for y, h, name in bands:
        label(ax, 0, y + h / 2, name, ha="left", fontsize=8.5, weight="bold",
              colour=INK_2)

    # Layer 1 — entry points
    box(ax, GUTTER, 76, 26, 11, "Streamlit web app\nsrc/ui/app.py",
        edge=GREY, fill=GREY_FILL)
    box(ax, GUTTER + 30, 76, 26, 11, "Command line\nrun_cli.py",
        edge=GREY, fill=GREY_FILL)

    # Layer 2 — language understanding
    box(ax, GUTTER, 58, 26, 11, "Conversational agent\ngathers trip details")
    box(ax, GUTTER + 30, 58, 26, 11, "Preferences extractor\nfree text → typed JSON")

    # Layer 3 — retrieval
    box(ax, GUTTER, 30, 26, 16, "MCP server\n12 schema-validated\ntools\nJSON-RPC over stdio",
        edge=AQUA, fill=AQUA_FILL, fontsize=8.5, weight="bold")
    box(ax, GUTTER + 31, 40.5, 24, 5.5, "fly-scraper  ·  flights",
        edge=ORANGE, fill=ORANGE_FILL, fontsize=8.5)
    box(ax, GUTTER + 31, 34.2, 24, 5.5, "Booking.com  ·  hotels",
        edge=ORANGE, fill=ORANGE_FILL, fontsize=8.5)
    box(ax, GUTTER + 31, 27.9, 24, 5.5, "Serper  ·  places",
        edge=ORANGE, fill=ORANGE_FILL, fontsize=8.5)
    box(ax, GUTTER + 60, 30, 24, 16, "HTTP cache\nrecord / replay\n+ quota guard",
        edge=AQUA, fill=AQUA_FILL, fontsize=8.5)

    # Layer 4 — assembly
    box(ax, GUTTER, 8, 56, 11,
        "Itinerary coordinator\nassembles the day-by-day plan from retrieved data only",
        fontsize=8.5)

    # Connectors, all inside the content area
    arrow(ax, (GUTTER + 13, 76), (GUTTER + 13, 69))
    arrow(ax, (GUTTER + 43, 76), (GUTTER + 43, 69))
    arrow(ax, (GUTTER + 26, 63.5), (GUTTER + 30, 63.5))
    # Extracted preferences drive the MCP server, not the APIs directly. The
    # previous straight-down arrow landed in the middle of the API column and
    # implied the extractor called them itself.
    arrow(ax, (GUTTER + 43, 58), (GUTTER + 15, 46.5), colour=BLUE)
    arrow(ax, (GUTTER + 26, 41), (GUTTER + 31, 43), colour=AQUA)
    arrow(ax, (GUTTER + 26, 38), (GUTTER + 31, 37), colour=AQUA)
    arrow(ax, (GUTTER + 26, 35), (GUTTER + 31, 30.6), colour=AQUA)
    arrow(ax, (GUTTER + 55, 38), (GUTTER + 60, 38), colour=AQUA, dashed=True)
    arrow(ax, (GUTTER + 13, 30), (GUTTER + 13, 19), colour=BLUE)

    # Connector labels are offset to one SIDE of their arrow rather than
    # centred on it, so the line never strikes through the text.
    label(ax, GUTTER + 28, 66, "A2A", fontsize=8, colour=BLUE)
    label(ax, GUTTER + 25, 55, "typed JSON", fontsize=8, colour=BLUE)
    label(ax, GUTTER + 15, 24, "retrieved data", fontsize=8, colour=BLUE, ha="left")
    # Sits above the cache box, clear of the API boxes it used to overlap.
    label(ax, GUTTER + 72, 48, "every call cached", fontsize=7.5, colour=AQUA)

    label(ax, 0, 2, "A2A protocol: 8 agent cards · 6 message types "
                    "(REQUEST · RESPONSE · QUERY · INFO · ERROR · ACK) · "
                    "permission-validated · priority-ordered delivery",
          ha="left", fontsize=8, colour=INK_2)
    return save(fig, "fig_architecture.png")


# ---------------------------------------------------------------- figure 2
def fig_four_arms():
    fig, ax = new_canvas(12.5, 6.6,
                         "The four architectures compared",
                         "Same request, same APIs, same A2A protocol. Only the data-retrieval "
                         "layer differs.")

    columns = [
        # One box, not two: "no tools" is a property of the single call, not a
        # second step, and drawing an arrow to it implied a sequence.
        (1.5, "ARM A", "Single LLM", [
            ("One LLM call\n\nno tools\nno retrieval\nno A2A", GREY, GREY_FILL),
        ], "Invents its data"),
        (26, "ARM B", "6 agents — naive", [
            ("Extractor", BLUE, BLUE_FILL),
            ("Flight agent\n(ReAct loop)", ORANGE, ORANGE_FILL),
            ("Hotel agent\n(ReAct loop)", ORANGE, ORANGE_FILL),
            ("Activities agent\n(ReAct loop)", ORANGE, ORANGE_FILL),
            ("Coordinator", BLUE, BLUE_FILL),
        ], "8 tools per agent,\nraw API payloads"),
        (50.5, "ARM C", "6 agents — tuned", [
            ("Extractor", BLUE, BLUE_FILL),
            ("Flight agent", AQUA, AQUA_FILL),
            ("Hotel agent", AQUA, AQUA_FILL),
            ("Activities agent", AQUA, AQUA_FILL),
            ("Coordinator", BLUE, BLUE_FILL),
        ], "1 tool each, distilled\nresults, run in parallel"),
        (75, "ARM D", "3 agents + direct API", [
            ("Extractor", BLUE, BLUE_FILL),
            ("Python calls\n(no LLM)", AQUA, AQUA_FILL),
            ("Coordinator", BLUE, BLUE_FILL),
        ], "Retrieval is plain code"),
    ]

    col_w = 22
    for x, code, name, blocks, note in columns:
        label(ax, x + col_w / 2, 88, code, fontsize=10, weight="bold", colour=INK)
        label(ax, x + col_w / 2, 83, name, fontsize=9, colour=INK_2)

        # Stack blocks downward from y=76, sized so any column fits the canvas.
        top, bottom = 76.0, 26.0
        gap = 3.0
        n = len(blocks)
        bh = (top - bottom - gap * (n - 1)) / n
        y = top - bh
        prev_centre = None
        for text, edge, fill in blocks:
            box(ax, x, y, col_w, bh, text, edge=edge, fill=fill, fontsize=8.5)
            centre = y + bh / 2
            if prev_centre is not None:
                arrow(ax, (x + col_w / 2, prev_centre - bh / 2),
                      (x + col_w / 2, centre + bh / 2))
            prev_centre = centre
            y -= bh + gap

        label(ax, x + col_w / 2, 20, note, fontsize=8, colour=INK_2)

    # Precise about which arms this covers: arm A has no tool layer at all, so
    # it emits no A2A messages and reaches no API.
    label(ax, 50, 8, "Arms B, C and D emit the same six A2A messages and reach the same "
                     "three APIs through the same MCP server.\n"
                     "Arm A is the control: no tools, so nothing it reports was retrieved.",
          fontsize=8.5, colour=INK_2)
    return save(fig, "fig_four_arms.png")


# ---------------------------------------------------------------- figure 3
def fig_a2a_flow():
    fig, ax = new_canvas(11, 6.4,
                         "A2A message flow for one trip",
                         "Six typed messages. Every one is validated against the sending "
                         "and receiving agent's card before delivery.")

    senders = [
        ("preferences_extractor", "REQUEST", "extracted preferences"),
        ("flight_data_provider", "RESPONSE", "flight results"),
        ("hotel_data_provider", "RESPONSE", "hotel results"),
        ("attraction_data_provider", "RESPONSE", "attraction results"),
        ("restaurant_data_provider", "RESPONSE", "restaurant results"),
        ("itinerary_coordinator", "RESPONSE", "final itinerary"),
    ]

    top = 78.0
    row_h = 11.0
    for i, (sender, mtype, payload) in enumerate(senders):
        y = top - i * row_h
        label(ax, 0.5, y, f"{i + 1}", fontsize=9, weight="bold", colour=INK_2, ha="left")
        box(ax, 4, y - 3.6, 30, 7.2, sender, edge=BLUE, fill=BLUE_FILL, fontsize=8.5)
        arrow(ax, (35, y), (57, y), colour=BLUE)
        label(ax, 46, y + 3.0, mtype, fontsize=7.5, weight="bold", colour=BLUE)
        label(ax, 46, y - 3.2, payload, fontsize=7.5, colour=INK_2)
        target = "user" if i == len(senders) - 1 else "itinerary_coordinator"
        box(ax, 58, y - 3.6, 30, 7.2, target, edge=AQUA, fill=AQUA_FILL, fontsize=8.5)

    label(ax, 46, 5,
          "Message types: REQUEST · RESPONSE · QUERY · INFO · ERROR · ACK      "
          "Delivery is priority-ordered.",
          fontsize=8, colour=INK_2)
    return save(fig, "fig_a2a_flow.png")


# ---------------------------------------------------------------- figure 4
def fig_mcp_lifecycle():
    # Taller canvas than the content needs: at 4.2in the title and subtitle
    # collided, because they are placed in data coordinates that compress as the
    # figure gets shorter.
    fig, ax = new_canvas(12.5, 5.4,
                         "MCP tool call lifecycle",
                         "Each stage can reject the call. The cache sits in front of the "
                         "network, so a repeated query costs nothing.")

    stages = [
        ("1\nSchema\nvalidation", BLUE, BLUE_FILL),
        ("2\nCache\nlookup", AQUA, AQUA_FILL),
        ("3\nQuota\nguard", AQUA, AQUA_FILL),
        ("4\nLive API call\n+ retry", ORANGE, ORANGE_FILL),
        ("5\nDistil to\ntop results", BLUE, BLUE_FILL),
        ("6\nCache write\n+ return", AQUA, AQUA_FILL),
    ]
    # 6 boxes + 5 gaps must fit inside 0..100, with a margin: the previous
    # width ran the last box off the right-hand edge.
    x0, w, gap = 1.0, 13.6, 2.6
    x = x0
    for i, (text, edge, fill) in enumerate(stages):
        box(ax, x, 46, w, 26, text, edge=edge, fill=fill, fontsize=8.5)
        if i:
            arrow(ax, (x - gap, 59), (x, 59))
        x += w + gap

    # The early return belongs to stage 2 (cache lookup), not stage 1.
    cache_x = x0 + (w + gap) + w / 2
    arrow(ax, (cache_x, 46), (cache_x, 37), colour=AQUA, dashed=True)
    label(ax, cache_x, 33, "cache hit returns here — no network, no quota spent",
          fontsize=8, colour=AQUA)

    label(ax, 50, 16,
          "Only 2xx responses are cached, so a quota error is never stored as if it "
          "were data.\nRequest headers are excluded from the cache, so no API key "
          "is written to disk.",
          fontsize=8, colour=INK_2)
    return save(fig, "fig_mcp_lifecycle.png")


def main():
    fig_system_architecture()
    fig_four_arms()
    fig_a2a_flow()
    fig_mcp_lifecycle()


if __name__ == "__main__":
    main()
