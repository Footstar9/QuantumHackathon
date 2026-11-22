"""
Draws the Level 3 (Y error, helper-qubit method) circuit as a presentation-ready PNG.

    pip install matplotlib
    python diagrams/draw_level3_circuit.py      (run from the level1_python folder)

Qubit numbering and gate order match level3.py exactly:
Level 1 encode (CNOT q0->q1, q0->q2), Y error, Level 1 syndrome
(q3 = q0 XOR q1, q4 = q1 XOR q2), X then Z on the flagged qubit
(skipped entirely if the syndrome is 00), Level 1 decode.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit_style import (BLUE, GREEN, GREY, ORANGE, RED, box_at, classical, classical_up,  # noqa: E402
                          cnot_at, error_box, legend, meter_at, new_figure, save, stage, state_note,
                          syndrome_table, wire)

Y = {0: 5.0, 1: 4.0, 2: 3.0, 3: 1.6, 4: 0.6}
X_START, X_END, HELPER_END = 1.2, 17.6, 12.1
TOP = Y[0]

fig, ax = new_figure(21, 10.2, (-0.6, 20.6), (-4.4, 8.0))

# --- wires -----------------------------------------------------------------
wire(ax, Y[0], X_START, X_END, "q0", r"$|\psi\rangle$")
wire(ax, Y[1], X_START, X_END, "q1", r"$|0\rangle$")
wire(ax, Y[2], X_START, X_END, "q2", r"$|0\rangle$")
wire(ax, Y[3], X_START, HELPER_END, "q3", r"$|0\rangle$", ORANGE)
wire(ax, Y[4], X_START, HELPER_END, "q4", r"$|0\rangle$", ORANGE)
ax.text(-0.5, 7.65, r"Level 3 (Y = iXZ errors).  Unknown qubit  $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$"
        "  on q0", fontsize=17, ha="left", va="center")
ax.text(X_START - 0.1, 2.25, "data", fontsize=12, ha="right", color=GREY, style="italic")
ax.text(X_START - 0.1, -0.05, "helpers", fontsize=12, ha="right", color=ORANGE, style="italic")

# --- stages ----------------------------------------------------------------
for x0, x1, name, color in [(1.45, 3.05, "1. Encode", BLUE), (3.3, 4.7, "2. Error", RED),
                            (4.95, 8.15, "3. Syndrome", ORANGE), (8.4, 9.5, "4. Measure", ORANGE),
                            (9.75, 11.05, "5. Fix bit", GREEN), (11.3, 12.6, "6. Fix sign", GREEN),
                            (12.85, 14.45, "7. Decode", BLUE)]:
    stage(ax, x0, x1, -0.25, 5.5, name, color)

# 1. encode (Level 1)
cnot_at(ax, 1.9, Y[0], Y[1])
cnot_at(ax, 2.6, Y[0], Y[2])
state_note(ax, 2.25, r"$\alpha|000\rangle + \beta|111\rangle$", TOP)

# 2. error
error_box(ax, 4.0, Y[0], Y[2], "E", r"$E \in \{I, Y_0, Y_1, Y_2\}$")
state_note(ax, 4.0, "e.g. $Y_0$:  " + r"$i(\alpha|100\rangle - \beta|011\rangle)$", TOP, RED, row=1)

# 3. syndrome (Level 1, unchanged)
cnot_at(ax, 5.4, Y[0], Y[3], ORANGE)
cnot_at(ax, 6.1, Y[1], Y[3], ORANGE)
cnot_at(ax, 7.0, Y[1], Y[4], ORANGE)
cnot_at(ax, 7.7, Y[2], Y[4], ORANGE)
ax.text(5.75, Y[3] - 0.5, "q3 = q0 XOR q1", fontsize=12.5, ha="center", color=ORANGE)
ax.text(7.35, Y[4] - 0.5, "q4 = q1 XOR q2", fontsize=12.5, ha="center", color=ORANGE)
state_note(ax, 6.55, "sees the X part only", TOP, ORANGE)

# 4. measure; classical bits feed BOTH corrections
for q, name in ((3, "$s_1$"), (4, "$s_2$")):
    meter_at(ax, 8.95, Y[q])
    classical(ax, 9.3, 11.95, Y[q])
    ax.text(9.95, Y[q] + 0.3, name, fontsize=14, ha="center", color=GREY)
classical_up(ax, 10.4, Y[4], Y[2] - 0.3)
classical_up(ax, 11.95, Y[4], Y[2] - 0.3)
state_note(ax, 8.95, "certain result (10 for $Y_0$)", TOP, ORANGE, row=1)

# 5. X on the flagged qubit
for q in (0, 1, 2):
    box_at(ax, 10.4, Y[q], "X?", GREEN, dashed=True)
state_note(ax, 10.4, r"$i(\alpha|000\rangle - \beta|111\rangle)$", TOP, GREEN)

# 6. Z on the same qubit (only if syndrome is not 00)
for q in (0, 1, 2):
    box_at(ax, 11.95, Y[q], "Z?", GREEN, dashed=True)
state_note(ax, 11.95, r"$i(\alpha|000\rangle + \beta|111\rangle)$", TOP, GREEN, row=1)

# 7. decode (Level 1)
cnot_at(ax, 13.3, Y[0], Y[2])
cnot_at(ax, 14.0, Y[0], Y[1])
state_note(ax, 13.65, r"$i(\alpha|0\rangle + \beta|1\rangle)$", TOP)

# outputs
ax.text(X_END + 0.15, Y[0], r"$\alpha|0\rangle + \beta|1\rangle$", fontsize=17, va="center", color=GREEN,
        weight="bold")
ax.text(X_END + 0.15, Y[0] - 0.45, "(times a global i)", fontsize=12, va="center", color=GREY)
ax.text(X_END + 0.15, Y[1], r"$|0\rangle$", fontsize=17, va="center")
ax.text(X_END + 0.15, Y[2], r"$|0\rangle$", fontsize=17, va="center")

syndrome_table(ax, 14.95, 1.95, [("s1 s2", "action"), ("0  0", "nothing at all"), ("1  0", "X, Z on q0"),
                                 ("1  1", "X, Z on q1"), ("0  1", "X, Z on q2")])

# footer + key
ax.text(-0.5, -1.5, "Y = iXZ. The helpers find the X part (which qubit); the rules promise every error is a Y, "
        "so that qubit also got a Z, which we undo.", fontsize=13.5, color=GREY)
ax.text(-0.5, -2.05, "The leftover i multiplies everything (global phase), so no measurement can see it. "
        "Verified: fidelity = 1 for all 4 errors × 6 test states.", fontsize=13.5, color=GREY)
legend(ax, -0.5, -2.95, correction="Z?")

save(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "level3_circuit.png"))
