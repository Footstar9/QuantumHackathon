"""
Draws the Level 1 circuit as a presentation-ready PNG.

    pip install matplotlib
    python diagrams/draw_level1_circuit.py      (run from the level1_python folder)

Qubit numbering and gate order match level1.py exactly:
q0, q1, q2 = data; q3 = helper for (q0, q1); q4 = helper for (q1, q2).
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle, Arc  # noqa: E402

BLUE = "#1f4e9c"      # data gates
ORANGE = "#c8611a"    # helper / syndrome
RED = "#b3261e"       # error
GREEN = "#2e7d32"     # correction
GREY = "#555555"

Y = {0: 5.0, 1: 4.0, 2: 3.0, 3: 1.6, 4: 0.6}   # wire heights
X_START, X_END = 1.2, 16.0
HELPER_END = 10.6

fig, ax = plt.subplots(figsize=(19, 8.8))
ax.set_xlim(-0.6, 18.6)
ax.set_ylim(-2.9, 8.0)
ax.axis("off")
fig.patch.set_facecolor("white")


def wire(q, label, start_label, color="black", end=X_END):
    ax.plot([X_START, end], [Y[q], Y[q]], color=color, lw=1.8, zorder=0)
    ax.text(-0.5, Y[q], label, fontsize=17, ha="left", va="center", weight="bold", color=color)
    ax.text(X_START - 0.1, Y[q], start_label, fontsize=17, ha="right", va="center", color=color)


def cnot(x, control, target, color=BLUE):
    ax.plot([x, x], [Y[control], Y[target]], color=color, lw=2.2, zorder=1)
    ax.add_patch(plt.Circle((x, Y[control]), 0.09, color=color, zorder=2))
    ax.add_patch(plt.Circle((x, Y[target]), 0.22, fill=True, fc="white", ec=color, lw=2.2, zorder=2))
    ax.plot([x - 0.22, x + 0.22], [Y[target]] * 2, color=color, lw=2.2, zorder=3)
    ax.plot([x, x], [Y[target] - 0.22, Y[target] + 0.22], color=color, lw=2.2, zorder=3)


def box(x, q, text, color, dashed=False, w=0.62, h=0.55):
    ax.add_patch(Rectangle((x - w / 2, Y[q] - h / 2), w, h, fc="white", ec=color, lw=2.2,
                           ls="--" if dashed else "-", zorder=4))
    ax.text(x, Y[q], text, fontsize=16, ha="center", va="center", color=color, weight="bold", zorder=5)


def meter(x, q):
    w, h = 0.7, 0.55
    ax.add_patch(Rectangle((x - w / 2, Y[q] - h / 2), w, h, fc="white", ec=ORANGE, lw=2.2, zorder=4))
    ax.add_patch(Arc((x, Y[q] - 0.14), 0.46, 0.46, theta1=0, theta2=180, color=ORANGE, lw=1.8, zorder=5))
    ax.annotate("", xy=(x + 0.2, Y[q] + 0.2), xytext=(x, Y[q] - 0.14),
                arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.6), zorder=5)


def state_note(x, text, color=GREY, row=0):
    yy = 6.0 + 0.8 * row
    ax.text(x, yy, text, fontsize=14.5, ha="center", va="center", color=color,
            bbox=dict(boxstyle="round,pad=0.3", fc="#f4f6fa", ec="#c9d1de"))
    ax.plot([x, x], [yy - 0.28, 5.3], color="#c9d1de", lw=1.2, ls=":", zorder=-1)


def stage(x0, x1, name, color):
    ax.add_patch(FancyBboxPatch((x0, -0.25), x1 - x0, 5.75, boxstyle="round,pad=0.02",
                                fc=color, ec="none", alpha=0.06, zorder=-1))
    ax.text((x0 + x1) / 2, -0.55, name, fontsize=15, ha="center", va="center", color=color, weight="bold")


# --- wires ---------------------------------------------------------------
wire(0, "q0", r"$|\psi\rangle$")
wire(1, "q1", r"$|0\rangle$")
wire(2, "q2", r"$|0\rangle$")
wire(3, "q3", r"$|0\rangle$", ORANGE, HELPER_END)
wire(4, "q4", r"$|0\rangle$", ORANGE, HELPER_END)
ax.text(-0.5, 7.65, r"Unknown qubit  $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$  on q0",
        fontsize=17, ha="left", va="center")
ax.text(X_START - 0.1, 2.25, "data", fontsize=12, ha="right", color=GREY, style="italic")
ax.text(X_START - 0.1, -0.05, "helpers", fontsize=12, ha="right", color=ORANGE, style="italic")

# --- stage backgrounds ---------------------------------------------------
stage(1.45, 3.05, "1. Encode", BLUE)
stage(3.3, 4.7, "2. Error", RED)
stage(4.95, 8.15, "3. Syndrome", ORANGE)
stage(8.4, 9.5, "4. Measure", ORANGE)
stage(9.75, 11.25, "5. Correct", GREEN)
stage(11.5, 13.1, "6. Decode", BLUE)

# --- 1. encode: CNOT q0->q1, CNOT q0->q2 --------------------------------
cnot(1.9, 0, 1)
cnot(2.6, 0, 2)
state_note(2.25, r"$\alpha|000\rangle + \beta|111\rangle$")

# --- 2. error -------------------------------------------------------------
ax.add_patch(Rectangle((3.55, Y[2] - 0.4), 0.9, Y[0] - Y[2] + 0.8, fc="white", ec=RED, lw=2.4,
                       ls="--", zorder=4))
ax.text(4.0, Y[1], "E", fontsize=24, ha="center", va="center", color=RED, weight="bold", zorder=5)
ax.text(4.0, Y[2] - 0.62, r"$E \in \{I, X_0, X_1, X_2\}$", fontsize=13, ha="center", color=RED)
state_note(4.0, "e.g. $X_1$:  " + r"$\alpha|010\rangle + \beta|101\rangle$", RED, row=1)

# --- 3. syndrome: q3 = q0 XOR q1, q4 = q1 XOR q2 ------------------------
cnot(5.4, 0, 3, ORANGE)
cnot(6.1, 1, 3, ORANGE)
cnot(7.0, 1, 4, ORANGE)
cnot(7.7, 2, 4, ORANGE)
ax.text(5.75, Y[3] - 0.5, "q3 = q0 XOR q1", fontsize=12.5, ha="center", color=ORANGE)
ax.text(7.35, Y[4] - 0.5, "q4 = q1 XOR q2", fontsize=12.5, ha="center", color=ORANGE)
state_note(6.55, "parities copied to helpers", ORANGE)

# --- 4. measure helpers ---------------------------------------------------
meter(8.95, 3)
meter(8.95, 4)
# classical wires from the meters to the correction
for q in (3, 4):
    ax.plot([9.3, 10.5], [Y[q] + 0.04, Y[q] + 0.04], color=GREY, lw=1.2)
    ax.plot([9.3, 10.5], [Y[q] - 0.04, Y[q] - 0.04], color=GREY, lw=1.2)
ax.plot([10.46, 10.46], [Y[4], Y[2] - 0.3], color=GREY, lw=1.2)
ax.plot([10.54, 10.54], [Y[4], Y[2] - 0.3], color=GREY, lw=1.2)
ax.text(9.95, Y[3] + 0.3, "$s_1$", fontsize=14, ha="center", color=GREY)
ax.text(9.95, Y[4] + 0.3, "$s_2$", fontsize=14, ha="center", color=GREY)
state_note(8.95, "certain result (11 for $X_1$)", ORANGE, row=1)

# --- 5. correct -------------------------------------------------------------
for q in (0, 1, 2):
    box(10.5, q, "X?", GREEN, dashed=True)
state_note(10.5, r"$\alpha|000\rangle + \beta|111\rangle$", GREEN)

# --- 6. decode: CNOT q0->q2, CNOT q0->q1 (reverse of encode) --------------
cnot(11.95, 0, 2)
cnot(12.65, 0, 1)
state_note(12.3, r"$\alpha|0\rangle + \beta|1\rangle$ on q0", row=1)

# --- outputs ---------------------------------------------------------------
ax.text(X_END + 0.15, Y[0], r"$\alpha|0\rangle + \beta|1\rangle$", fontsize=17, va="center", color=GREEN,
        weight="bold")
ax.text(X_END + 0.15, Y[1], r"$|0\rangle$", fontsize=17, va="center")
ax.text(X_END + 0.15, Y[2], r"$|0\rangle$", fontsize=17, va="center")

# --- syndrome table --------------------------------------------------------
tx, ty = 13.6, 1.95
rows = [("s1 s2", "action"), ("0  0", "no error"), ("1  0", "flip q0"), ("1  1", "flip q1"), ("0  1", "flip q2")]
ax.add_patch(FancyBboxPatch((tx - 0.15, ty - 2.05), 3.45, 2.55, boxstyle="round,pad=0.05",
                            fc="white", ec=GREEN, lw=1.8, zorder=4))
for i, (s, a) in enumerate(rows):
    w = "bold" if i == 0 else "normal"
    ax.text(tx + 0.25, ty + 0.15 - i * 0.47, s, fontsize=14.5, va="center", weight=w, family="monospace", zorder=5)
    ax.text(tx + 1.55, ty + 0.15 - i * 0.47, a, fontsize=14.5, va="center", weight=w, zorder=5)
ax.plot([tx, tx + 3.15], [ty - 0.1] * 2, color=GREEN, lw=1, zorder=5)

# --- footer -------------------------------------------------------------
ax.text(-0.5, -1.5, "Helpers learn WHERE the flip is (parities), never α or β: both branches of the "
        "superposition give the same parities,", fontsize=13.5, color=GREY)
ax.text(-0.5, -2.05, "so measuring q3, q4 does not collapse the secret. "
        "Recovery verified with fidelity = 1 for all 4 errors × 6 test states.", fontsize=13.5, color=GREY)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "level1_circuit.png")
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print("saved", out)
