"""
Figure layout engine shared by every diagram and chart in the report.

Why this exists
---------------
The first generation of these diagrams estimated text width from character
count. On a proportional font that is wrong in both directions: "Illinois" and
"WWWWWWWW" have the same length and very different widths. The result was
labels overflowing their boxes, connectors drawn straight through text, and a
title colliding with the first row of content whenever a canvas got shorter.
Every one of those was found by looking at the exported PNG, which is a slow and
unreliable way to find a layout bug.

So layout here is mechanical, not estimated:

  * text is MEASURED with the actual renderer at the actual font size, and
    wrapped to a width in data units (`measure`, `wrap`),
  * boxes GROW to fit their measured contents rather than clipping them
    (`Box.fit`),
  * a header band is RESERVED at the top of every canvas and content is
    rejected if it intrudes (`Canvas.HEADER_FLOOR`),
  * connectors route ORTHOGONALLY, so a line never cuts diagonally across a
    box it does not belong to (`connect`),
  * every label carries an OPAQUE background, so a connector passing behind it
    cannot strike through the text (`label`),
  * and `Canvas.validate()` raises `LayoutError` on any overlap, any content
    outside the frame, and any text wider or taller than the box holding it.

`LayoutError` fails the build. A figure that is wrong is therefore impossible to
ship silently — which is the only way this stays true as figures change.

Export is 300 dpi (`DPI`), the floor for print-quality figures in a submitted
document.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DPI = 300

# Palette. One accent per semantic role, held constant across every figure so a
# colour means the same thing in chapter 4 as it does in chapter 6.
BLUE = "#2a78d6"
BLUE_FILL = "#e4eefb"
AQUA = "#1baf7a"
AQUA_FILL = "#e2f5ee"
ORANGE = "#eb6834"
ORANGE_FILL = "#fdeae2"
RED = "#c8362a"
RED_FILL = "#fbe6e3"
PURPLE = "#7256c4"
PURPLE_FILL = "#ece7f9"
GREY = "#8a8983"
GREY_FILL = "#efeeea"
INK = "#0b0b0b"
INK_2 = "#52514e"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
})


class LayoutError(AssertionError):
    """Raised when a figure's geometry is provably wrong. Fails the build."""


@dataclass
class Box:
    """A rounded box on the canvas, sized to fit its own measured text."""

    x: float
    y: float
    w: float
    h: float
    text: str = ""
    edge: str = BLUE
    fill: str = BLUE_FILL
    fontsize: float = 9.0
    weight: str = "normal"
    text_colour: str = INK
    name: str = ""
    # Boxes that are meant to sit inside another box (a band, a lane) are
    # excluded from the overlap check against that parent.
    inside: Optional[str] = None

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y + self.h

    def edge_point(self, side: str) -> Tuple[float, float]:
        return {
            "top": (self.cx, self.top),
            "bottom": (self.cx, self.y),
            "left": (self.x, self.cy),
            "right": (self.right, self.cy),
        }[side]


@dataclass
class Canvas:
    """
    A figure with a reserved header band and mechanical layout validation.

    Coordinates are 0..100 in both axes regardless of the figure's physical
    size, so a layout does not shift when a canvas is resized — only the
    aspect ratio changes, and text measurement accounts for that.
    """

    width_in: float
    height_in: float
    title: str
    subtitle: str = ""
    footer: str = ""

    # Content must stay below this line. The band above it belongs to the title
    # and subtitle and nothing else, which is what makes a title/content
    # collision structurally impossible rather than a thing to check by eye.
    HEADER_FLOOR: float = 86.0
    FOOTER_CEILING: float = 0.0

    fig: plt.Figure = field(init=False)
    ax: plt.Axes = field(init=False)
    boxes: List[Box] = field(default_factory=list, init=False)
    # Every connector segment drawn, so validate() can prove that none of them
    # runs diagonally or cuts through a box it does not belong to.
    segments: List[Tuple[Tuple[float, float], Tuple[float, float], bool]] = field(
        default_factory=list, init=False)
    _checked_segments: List[Tuple[Tuple[float, float], Tuple[float, float], bool]] = \
        field(default_factory=list, init=False)
    _labels: List[Tuple[float, float, str, float, str]] = field(default_factory=list, init=False)
    _measure_cache: Dict[Tuple[str, float, str], Tuple[float, float]] = field(
        default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.fig, self.ax = plt.subplots(figsize=(self.width_in, self.height_in))
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.axis("off")
        self.ax.text(0, 99, self.title, ha="left", va="top",
                     fontsize=14, weight="bold", color=INK, zorder=5)
        if self.subtitle:
            wrapped = self.wrap(self.subtitle, 100.0, 9.5)
            self.ax.text(0, 93.5, wrapped, ha="left", va="top",
                         fontsize=9.5, color=INK_2, zorder=5, linespacing=1.5)
            # Push the content floor down if a long subtitle needs three lines,
            # so wrapping the subtitle can never eat into the content area.
            lines = wrapped.count("\n") + 1
            self.HEADER_FLOOR = min(self.HEADER_FLOOR, 93.5 - lines * 3.4 - 1.5)
        if self.footer:
            wrapped = self.wrap(self.footer, 100.0, 8.5)
            lines = wrapped.count("\n") + 1
            self.ax.text(0, 1.0, wrapped, ha="left", va="bottom",
                         fontsize=8.5, color=INK_2, zorder=5, linespacing=1.5)
            self.FOOTER_CEILING = 1.0 + lines * 3.0 + 1.0

    # ------------------------------------------------------------ measurement
    def measure(self, text: str, fontsize: float, weight: str = "normal") -> Tuple[float, float]:
        """
        Width and height of `text` in data units, from the real renderer.

        This is the whole point of the module: no character-count estimate can
        do this correctly for a proportional font.
        """
        key = (text, fontsize, weight)
        if key in self._measure_cache:
            return self._measure_cache[key]
        renderer = self.fig.canvas.get_renderer()
        artist = self.ax.text(0, 0, text, fontsize=fontsize, weight=weight,
                              linespacing=1.45)
        bbox = artist.get_window_extent(renderer=renderer)
        inverse = self.ax.transData.inverted()
        (x0, y0), (x1, y1) = inverse.transform([[bbox.x0, bbox.y0], [bbox.x1, bbox.y1]])
        artist.remove()
        size = (abs(x1 - x0), abs(y1 - y0))
        self._measure_cache[key] = size
        return size

    def wrap(self, text: str, max_w: float, fontsize: float,
             weight: str = "normal") -> str:
        """Greedy wrap to `max_w` data units, measuring each candidate line."""
        out_lines: List[str] = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                out_lines.append("")
                continue
            line = words[0]
            for word in words[1:]:
                candidate = f"{line} {word}"
                if self.measure(candidate, fontsize, weight)[0] <= max_w:
                    line = candidate
                else:
                    out_lines.append(line)
                    line = word
            out_lines.append(line)
        return "\n".join(out_lines)

    # ------------------------------------------------------------- primitives
    def box(self, x: float, y: float, w: float, h: float, text: str = "", *,
            edge: str = BLUE, fill: str = BLUE_FILL, fontsize: float = 9.0,
            weight: str = "normal", text_colour: str = INK, name: str = "",
            inside: Optional[str] = None, fit: bool = True,
            pad: float = 1.6) -> Box:
        """
        Place a box. With `fit=True` the box grows (never shrinks) so its
        wrapped text fits inside with `pad` clearance — contents are never
        clipped to preserve a hand-chosen width.
        """
        wrapped = self.wrap(text, max(w - 2 * pad, 4.0), fontsize, weight) if text else ""
        if text and fit:
            tw, th = self.measure(wrapped, fontsize, weight)
            w = max(w, tw + 2 * pad)
            h = max(h, th + 2 * pad)
        b = Box(x=x, y=y, w=w, h=h, text=wrapped, edge=edge, fill=fill,
                fontsize=fontsize, weight=weight, text_colour=text_colour,
                name=name or (text.split("\n")[0][:32] if text else f"box{len(self.boxes)}"),
                inside=inside)
        self.ax.add_patch(FancyBboxPatch(
            (b.x, b.y), b.w, b.h,
            boxstyle="round,pad=0,rounding_size=0.9",
            linewidth=1.4, edgecolor=b.edge, facecolor=b.fill, zorder=2,
        ))
        if wrapped:
            self.ax.text(b.cx, b.cy, wrapped, ha="center", va="center",
                         fontsize=fontsize, color=text_colour, weight=weight,
                         zorder=4, linespacing=1.45)
        self.boxes.append(b)
        return b

    def band(self, x: float, y: float, w: float, h: float, label_text: str = "", *,
             edge: str = GREY, fill: str = "#f6f5f2", name: str = "") -> Box:
        """A background lane. Registered so children can declare themselves inside it."""
        b = Box(x=x, y=y, w=w, h=h, edge=edge, fill=fill,
                name=name or label_text or f"band{len(self.boxes)}")
        self.ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
            linewidth=1.0, edgecolor=edge, facecolor=fill, zorder=1,
        ))
        if label_text:
            self.ax.text(x + 1.2, b.top - 1.2, label_text, ha="left", va="top",
                         fontsize=8.5, weight="bold", color=INK_2, zorder=3)
        self.boxes.append(b)
        return b

    def label(self, x: float, y: float, text: str, *, fontsize: float = 8.5,
              colour: str = INK_2, ha: str = "center", va: str = "center",
              weight: str = "normal", opaque: bool = True,
              max_w: Optional[float] = None) -> None:
        """
        Free text. Opaque by default so a connector behind it cannot strike
        through the glyphs — the defect that made three earlier figures
        unreadable.
        """
        if max_w:
            text = self.wrap(text, max_w, fontsize, weight)
        bbox = dict(boxstyle="round,pad=0.28", facecolor=SURFACE,
                    edgecolor="none", alpha=1.0) if opaque else None
        self.ax.text(x, y, text, ha=ha, va=va, fontsize=fontsize, color=colour,
                     weight=weight, zorder=6, bbox=bbox, linespacing=1.45)
        self._labels.append((x, y, text, fontsize, ha))

    # ------------------------------------------------------------- connectors
    def arrow(self, start: Tuple[float, float], end: Tuple[float, float], *,
              colour: str = GREY, lw: float = 1.4, dashed: bool = False,
              head: bool = True, diagonal: bool = False,
              crosses: bool = False) -> None:
        """
        Draw one connector segment.

        `diagonal=True` opts a segment out of the orthogonality check, and
        `crosses=True` out of the box-crossing check. Both exist for the few
        cases where a diagonal genuinely reads better — a lifeline, a bracket —
        and both have to be stated explicitly, so an accidental diagonal fails
        the build rather than reaching the document.
        """
        self.segments.append((start, end, diagonal or crosses))
        if not crosses:
            self._checked_segments.append((start, end, diagonal))
        self.ax.add_patch(FancyArrowPatch(
            start, end, arrowstyle="-|>" if head else "-", mutation_scale=12,
            linewidth=lw, color=colour, zorder=3,
            linestyle="--" if dashed else "-", shrinkA=1, shrinkB=1,
        ))

    def connect(self, a: Box, b: Box, *, colour: str = GREY, dashed: bool = False,
                text: str = "", route: str = "auto", offset: float = 0.0) -> None:
        """
        Join two boxes with an ORTHOGONAL connector.

        A diagonal line across a diagram is the fastest way to make it
        ambiguous about what connects to what, so segments here are only ever
        horizontal or vertical. `route` picks the elbow: 'v' leaves vertically,
        'h' leaves horizontally, 'auto' chooses by the dominant axis.
        """
        if route == "auto":
            route = "v" if abs(b.cy - a.cy) >= abs(b.cx - a.cx) else "h"

        if route == "v":
            y0 = a.y if b.cy < a.cy else a.top
            y1 = b.top if b.cy < a.cy else b.y
            mid = (y0 + y1) / 2 + offset
            pts = [(a.cx, y0), (a.cx, mid), (b.cx, mid), (b.cx, y1)]
        else:
            x0 = a.x if b.cx < a.cx else a.right
            x1 = b.right if b.cx < a.cx else b.x
            mid = (x0 + x1) / 2 + offset
            pts = [(x0, a.cy), (mid, a.cy), (mid, b.cy), (x1, b.cy)]

        for i in range(len(pts) - 1):
            if pts[i] == pts[i + 1]:
                continue
            last = i == len(pts) - 2
            self.arrow(pts[i], pts[i + 1], colour=colour, dashed=dashed, head=last)

        if text:
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            self.label(mx, my, text, fontsize=7.8, colour=colour)

    # ------------------------------------------------------------- validation
    def validate(self, *, allow_overlap: Sequence[Tuple[str, str]] = ()) -> None:
        """
        Fail the build if the geometry is wrong.

        Three classes of defect are caught: content outside the frame or inside
        the reserved header/footer band, boxes overlapping each other, and text
        larger than the box drawn around it.
        """
        problems: List[str] = []
        permitted = {frozenset(pair) for pair in allow_overlap}

        for b in self.boxes:
            if b.x < -0.5 or b.right > 100.5 or b.y < -0.5 or b.top > 100.5:
                problems.append(
                    f"'{b.name}' is outside the frame "
                    f"(x {b.x:.1f}..{b.right:.1f}, y {b.y:.1f}..{b.top:.1f})")
            if b.top > self.HEADER_FLOOR:
                problems.append(
                    f"'{b.name}' intrudes into the reserved header band "
                    f"(top {b.top:.1f} > floor {self.HEADER_FLOOR:.1f})")
            if b.y < self.FOOTER_CEILING:
                problems.append(
                    f"'{b.name}' intrudes into the reserved footer band "
                    f"(bottom {b.y:.1f} < ceiling {self.FOOTER_CEILING:.1f})")
            if b.text:
                tw, th = self.measure(b.text, b.fontsize, b.weight)
                if tw > b.w + 0.01 or th > b.h + 0.01:
                    problems.append(
                        f"text is clipped by '{b.name}': needs {tw:.1f}x{th:.1f}, "
                        f"box is {b.w:.1f}x{b.h:.1f}")

        for i, a in enumerate(self.boxes):
            for b in self.boxes[i + 1:]:
                if frozenset({a.name, b.name}) in permitted:
                    continue
                if a.inside == b.name or b.inside == a.name:
                    continue
                overlap_w = min(a.right, b.right) - max(a.x, b.x)
                overlap_h = min(a.top, b.top) - max(a.y, b.y)
                if overlap_w > 0.35 and overlap_h > 0.35:
                    problems.append(
                        f"'{a.name}' overlaps '{b.name}' by "
                        f"{overlap_w:.1f}x{overlap_h:.1f}")

        problems.extend(self._connector_problems())

        if problems:
            raise LayoutError(
                f"{self.title!r}: {len(problems)} layout defect(s)\n  - "
                + "\n  - ".join(problems))

    # ------------------------------------------------------- connector checks
    def _connector_problems(self) -> List[str]:
        """
        Two defects the box checks cannot see.

        A diagonal connector across a diagram makes it ambiguous what joins to
        what, and a connector that passes through an unrelated box implies a
        relationship that does not exist. Both were present in this project's
        first generation of figures and both were found by eye rather than by the
        build, which is why they are checked here.
        """
        problems: List[str] = []
        EPS = 0.35        # a segment shorter than this in one axis counts as straight
        INSET = 0.9       # how far inside a box a line must go before it counts

        for (x0, y0), (x1, y1), diagonal_ok in self._checked_segments:
            dx, dy = abs(x1 - x0), abs(y1 - y0)
            if not diagonal_ok and dx > EPS and dy > EPS:
                problems.append(
                    f"connector ({x0:.1f},{y0:.1f})->({x1:.1f},{y1:.1f}) is "
                    f"diagonal; route it orthogonally or pass diagonal=True")
                continue
            if dx > EPS and dy > EPS:
                continue  # a permitted diagonal is not checked for crossings

            for b in self.boxes:
                # A box the segment merely starts or ends on is not crossed.
                if self._touches(b, x0, y0) or self._touches(b, x1, y1):
                    continue
                if self._crosses(b, x0, y0, x1, y1, INSET):
                    problems.append(
                        f"connector ({x0:.1f},{y0:.1f})->({x1:.1f},{y1:.1f}) "
                        f"passes through '{b.name}'")
        return problems

    @staticmethod
    def _touches(b: Box, x: float, y: float, tol: float = 1.2) -> bool:
        return (b.x - tol <= x <= b.right + tol) and (b.y - tol <= y <= b.top + tol)

    @staticmethod
    def _crosses(b: Box, x0: float, y0: float, x1: float, y1: float,
                 inset: float) -> bool:
        """Does an axis-aligned segment enter the box's interior?"""
        left, right = b.x + inset, b.right - inset
        bottom, top = b.y + inset, b.top - inset
        if right <= left or top <= bottom:
            return False
        if abs(y1 - y0) <= abs(x1 - x0):        # horizontal
            if not (bottom <= y0 <= top):
                return False
            lo, hi = sorted((x0, x1))
            return lo < right and hi > left
        if not (left <= x0 <= right):           # vertical
            return False
        lo, hi = sorted((y0, y1))
        return lo < top and hi > bottom

    # ----------------------------------------------------------------- output
    def save(self, name: str, subdir: str = "diagrams") -> str:
        self.validate()
        out_dir = os.path.join(ROOT, "figures", subdir)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, name)
        self.fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.28)
        plt.close(self.fig)
        return path


def stack(canvas: Canvas, x: float, top: float, bottom: float, w: float,
          entries: Sequence[Tuple[str, str, str]], *, gap: float = 2.6,
          fontsize: float = 8.5, connect: bool = True,
          colour: str = GREY) -> List[Box]:
    """
    Lay a column of boxes between `top` and `bottom`, joined vertically.

    Heights are divided evenly and then each box is allowed to grow to fit its
    own text, so a long label lengthens its box instead of being clipped. The
    stack is re-packed downward afterwards so growth cannot cause an overlap.
    """
    n = len(entries)
    slot = (top - bottom - gap * (n - 1)) / n

    # Measure every entry BEFORE drawing anything, so each box's final height is
    # known up front and positions can be allocated once. Drawing first and
    # nudging afterwards is how boxes end up overlapping.
    pad = 1.6
    heights: List[float] = []
    for text, _, _ in entries:
        wrapped = canvas.wrap(text, max(w - 2 * pad, 4.0), fontsize)
        _, th = canvas.measure(wrapped, fontsize)
        heights.append(max(slot, th + 2 * pad))

    boxes: List[Box] = []
    cursor = top
    for (text, edge, fill), h in zip(entries, heights):
        boxes.append(canvas.box(x, cursor - h, w, h, text, edge=edge, fill=fill,
                                fontsize=fontsize))
        cursor -= h + gap

    if connect:
        for a, b in zip(boxes, boxes[1:]):
            canvas.arrow((a.cx, a.y), (b.cx, b.top), colour=colour)
    return boxes


def save_chart(fig, name: str) -> str:
    out_dir = os.path.join(ROOT, "figures", "results")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)
    return path
