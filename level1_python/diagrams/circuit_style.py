"""
Shared drawing pieces for the circuit diagrams (wires, CNOTs, boxes, meters,
stage shading, state notes, syndrome table and the legend).

Every function takes the matplotlib axes `ax` and a dict `Y` of wire heights.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Arc, FancyBboxPatch, Rectangle  # noqa: E402

BLUE = "#1f4e9c"      # data gates
PURPLE = "#6a3d9a"    # Hadamard
ORANGE = "#c8611a"    # helper / syndrome
RED = "#b3261e"       # error
GREEN = "#2e7d32"     # correction
GREY = "#555555"

LABEL_X = -0.5


def new_figure(width, height, xlim, ylim):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax


def wire(ax, y, x0, x1, label, start_label, color="black"):
    ax.plot([x0, x1], [y, y], color=color, lw=1.8, zorder=0)
    if label:
        ax.text(LABEL_X, y, label, fontsize=17, ha="left", va="center", weight="bold", color=color)
    if start_label:
        ax.text(x0 - 0.1, y, start_label, fontsize=17, ha="right", va="center", color=color)


def classical(ax, x0, x1, y):
    for d in (0.04, -0.04):
        ax.plot([x0, x1], [y + d, y + d], color=GREY, lw=1.2, zorder=0)


def classical_up(ax, x, y0, y1):
    for d in (0.04, -0.04):
        ax.plot([x + d, x + d], [y0, y1], color=GREY, lw=1.2, zorder=0)


def cnot_at(ax, x, yc, yt, color=BLUE):
    ax.plot([x, x], [yc, yt], color=color, lw=2.2, zorder=1)
    ax.add_patch(plt.Circle((x, yc), 0.09, color=color, zorder=2))
    ax.add_patch(plt.Circle((x, yt), 0.22, fc="white", ec=color, lw=2.2, zorder=2))
    ax.plot([x - 0.22, x + 0.22], [yt, yt], color=color, lw=2.2, zorder=3)
    ax.plot([x, x], [yt - 0.22, yt + 0.22], color=color, lw=2.2, zorder=3)


def box_at(ax, x, y, text, color, dashed=False, w=0.62, h=0.55, fontsize=16):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc="white", ec=color, lw=2.2,
                           ls="--" if dashed else "-", zorder=4))
    ax.text(x, y, text, fontsize=fontsize, ha="center", va="center", color=color, weight="bold", zorder=5)


def meter_at(ax, x, y, color=ORANGE):
    w, h = 0.7, 0.55
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc="white", ec=color, lw=2.2, zorder=4))
    ax.add_patch(Arc((x, y - 0.14), 0.46, 0.46, theta1=0, theta2=180, color=color, lw=1.8, zorder=5))
    ax.annotate("", xy=(x + 0.2, y + 0.2), xytext=(x, y - 0.14),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6), zorder=5)


def error_box(ax, x, y_top, y_bottom, letter, caption):
    ax.add_patch(Rectangle((x - 0.45, y_bottom - 0.4), 0.9, y_top - y_bottom + 0.8, fc="white", ec=RED,
                           lw=2.4, ls="--", zorder=4))
    ax.text(x, (y_top + y_bottom) / 2, letter, fontsize=24, ha="center", va="center", color=RED,
            weight="bold", zorder=5)
    ax.text(x, y_bottom - 0.62, caption, fontsize=13, ha="center", color=RED)


def state_note(ax, x, text, y_wire_top, color=GREY, row=0):
    yy = y_wire_top + 1.0 + 0.8 * row
    ax.text(x, yy, text, fontsize=14.5, ha="center", va="center", color=color,
            bbox=dict(boxstyle="round,pad=0.3", fc="#f4f6fa", ec="#c9d1de"))
    ax.plot([x, x], [yy - 0.28, y_wire_top + 0.3], color="#c9d1de", lw=1.2, ls=":", zorder=-1)


def stage(ax, x0, x1, y_bottom, y_top, name, color, label_drop=0.0):
    ax.add_patch(FancyBboxPatch((x0, y_bottom), x1 - x0, y_top - y_bottom, boxstyle="round,pad=0.02",
                                fc=color, ec="none", alpha=0.06, zorder=-1))
    ax.text((x0 + x1) / 2, y_bottom - 0.3 - label_drop, name, fontsize=15, ha="center", va="center", color=color,
            weight="bold")


def syndrome_table(ax, tx, ty, rows, col2=1.55, width=3.45):
    """rows: list of (bits, action), header first."""
    height = 0.47 * len(rows) + 0.2
    ax.add_patch(FancyBboxPatch((tx - 0.15, ty + 0.5 - height), width, height, boxstyle="round,pad=0.05",
                                fc="white", ec=GREEN, lw=1.8, zorder=4))
    for i, (s, a) in enumerate(rows):
        w = "bold" if i == 0 else "normal"
        ax.text(tx + 0.25, ty + 0.15 - i * 0.47, s, fontsize=14.5, va="center", weight=w,
                family="monospace", zorder=5)
        ax.text(tx + col2, ty + 0.15 - i * 0.47, a, fontsize=14.5, va="center", weight=w, zorder=5)
    ax.plot([tx, tx + width - 0.3], [ty - 0.1] * 2, color=GREEN, lw=1, zorder=5)


def legend(ax, x, y, include_h=False, correction="X?"):
    """A two-row key explaining every symbol, starting at (x, y)."""
    ax.text(x, y, "Key:", fontsize=14, va="center", weight="bold", color=GREY)
    x0 = x + 1.0

    # row 1: wire and CNOT
    ax.plot([x0, x0 + 0.7], [y, y], color="black", lw=1.8)
    ax.text(x0 + 0.9, y, "qubit wire (time runs left to right)", fontsize=13, va="center")
    cx = x0 + 6.4
    ax.add_patch(plt.Circle((cx, y), 0.09, color=BLUE))
    ax.plot([cx, cx + 0.6], [y, y], color=BLUE, lw=2.2)
    ax.add_patch(plt.Circle((cx + 0.6, y), 0.22, fc="white", ec=BLUE, lw=2.2))
    ax.plot([cx + 0.38, cx + 0.82], [y, y], color=BLUE, lw=2.2)
    ax.plot([cx + 0.6, cx + 0.6], [y - 0.22, y + 0.22], color=BLUE, lw=2.2)
    ax.text(cx + 1.05, y, "CNOT: the dot is the control; the target (circle with +) "
            "flips only when the control is 1", fontsize=13, va="center")

    # row 2: H, measure, measured bit, conditional correction
    y2 = y - 0.8
    x = x0
    if include_h:
        box_at(ax, x + 0.25, y2, "H", PURPLE, w=0.5, h=0.45, fontsize=14)
        ax.text(x + 0.7, y2, "Hadamard: |0> to |+>, |1> to |->", fontsize=13, va="center")
        x += 6.0
    meter_at(ax, x + 0.35, y2)
    ax.text(x + 0.9, y2, "measure (helpers only)", fontsize=13, va="center")
    x += 4.4
    classical(ax, x, x + 0.7, y2)
    ax.text(x + 0.9, y2, "measured bit", fontsize=13, va="center")
    x += 3.2
    if not correction:
        return
    box_at(ax, x + 0.3, y2, correction, GREEN, dashed=True, w=0.6, h=0.45, fontsize=13)
    ax.text(x + 0.75, y2, "applied only if the table says so", fontsize=13, va="center")


def save(fig, path):
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    print("saved", path)
