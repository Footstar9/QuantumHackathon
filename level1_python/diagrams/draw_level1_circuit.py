"""
Draws the Level 1 circuit as a presentation-ready PNG.

    pip install matplotlib
    python diagrams/draw_level1_circuit.py      (run from the level1_python folder)

Qubit numbering and gate order match level1.py exactly:
q0, q1, q2 = data; q3 = helper for (q0, q1); q4 = helper for (q1, q2).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit_style import (BLUE, GREEN, GREY, ORANGE, RED, box_at, classical, classical_up,  # noqa: E402
                          cnot_at, error_box, legend, meter_at, new_figure, save, stage, state_note,
                          syndrome_table, wire)

Y = {0: 5.0, 1: 4.0, 2: 3.0, 3: 1.6, 4: 0.6}   # wire heights
X_START, X_END, HELPER_END = 1.2, 16.0, 10.6
TOP = Y[0]

fig, ax = new_figure(19, 10.2, (-0.6, 18.6), (-4.4, 8.0))

# --- wires -----------------------------------------------------------------
wire(ax, Y[0], X_START, X_END, "q0", r"$|\psi\rangle$")
wire(ax, Y[1], X_START, X_END, "q1", r"$|0\rangle$")
wire(ax, Y[2], X_START, X_END, "q2", r"$|0\rangle$")
wire(ax, Y[3], X_START, HELPER_END, "q3", r"$|0\rangle$", ORANGE)
wire(ax, Y[4], X_START, HELPER_END, "q4", r"$|0\rangle$", ORANGE)
ax.text(-0.5, 7.65, r"Level 1 (bit flips).  Unknown qubit  $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$  on q0",
        fontsize=17, ha="left", va="center")
ax.text(X_START - 0.1, 2.25, "data", fontsize=12, ha="right", color=GREY, style="italic")
ax.text(X_START - 0.1, -0.05, "helpers", fontsize=12, ha="right", color=ORANGE, style="italic")

# --- stages ----------------------------------------------------------------
for x0, x1, name, color in [(1.45, 3.05, "1. Encode", BLUE), (3.3, 4.7, "2. Error", RED),
                            (4.95, 8.15, "3. Syndrome", ORANGE), (8.4, 9.5, "4. Measure", ORANGE),
                            (9.75, 11.25, "5. Correct", GREEN), (11.5, 13.1, "6. Decode", BLUE)]:
    stage(ax, x0, x1, -0.25, 5.5, name, color)

# 1. encode: CNOT q0->q1, CNOT q0->q2
cnot_at(ax, 1.9, Y[0], Y[1])
cnot_at(ax, 2.6, Y[0], Y[2])
state_note(ax, 2.25, r"$\alpha|000\rangle + \beta|111\rangle$", TOP)

# 2. error
error_box(ax, 4.0, Y[0], Y[2], "E", r"$E \in \{I, X_0, X_1, X_2\}$")
state_note(ax, 4.0, "e.g. $X_1$:  " + r"$\alpha|010\rangle + \beta|101\rangle$", TOP, RED, row=1)

# 3. syndrome: q3 = q0 XOR q1, q4 = q1 XOR q2
cnot_at(ax, 5.4, Y[0], Y[3], ORANGE)
cnot_at(ax, 6.1, Y[1], Y[3], ORANGE)
cnot_at(ax, 7.0, Y[1], Y[4], ORANGE)
cnot_at(ax, 7.7, Y[2], Y[4], ORANGE)
ax.text(5.75, Y[3] - 0.5, "q3 = q0 XOR q1", fontsize=12.5, ha="center", color=ORANGE)
ax.text(7.35, Y[4] - 0.5, "q4 = q1 XOR q2", fontsize=12.5, ha="center", color=ORANGE)
state_note(ax, 6.55, "parities copied to helpers", TOP, ORANGE)

# 4. measure helpers, classical bits feed the correction
for q, name in ((3, "$s_1$"), (4, "$s_2$")):
    meter_at(ax, 8.95, Y[q])
    classical(ax, 9.3, 10.5, Y[q])
    ax.text(9.95, Y[q] + 0.3, name, fontsize=14, ha="center", color=GREY)
classical_up(ax, 10.5, Y[4], Y[2] - 0.3)
state_note(ax, 8.95, "certain result (11 for $X_1$)", TOP, ORANGE, row=1)

# 5. correct
for q in (0, 1, 2):
    box_at(ax, 10.5, Y[q], "X?", GREEN, dashed=True)
state_note(ax, 10.5, r"$\alpha|000\rangle + \beta|111\rangle$", TOP, GREEN)

# 6. decode: CNOT q0->q2, CNOT q0->q1 (reverse of encode)
cnot_at(ax, 11.95, Y[0], Y[2])
cnot_at(ax, 12.65, Y[0], Y[1])
state_note(ax, 12.3, r"$\alpha|0\rangle + \beta|1\rangle$ on q0", TOP, row=1)

# outputs
ax.text(X_END + 0.15, Y[0], r"$\alpha|0\rangle + \beta|1\rangle$", fontsize=17, va="center", color=GREEN,
        weight="bold")
ax.text(X_END + 0.15, Y[1], r"$|0\rangle$", fontsize=17, va="center")
ax.text(X_END + 0.15, Y[2], r"$|0\rangle$", fontsize=17, va="center")

syndrome_table(ax, 13.6, 1.95, [("s1 s2", "action"), ("0  0", "no error"), ("1  0", "flip q0"),
                                ("1  1", "flip q1"), ("0  1", "flip q2")])

# footer + key
ax.text(-0.5, -1.5, "Helpers learn WHERE the flip is (parities), never α or β: both branches of the "
        "superposition give the same parities,", fontsize=13.5, color=GREY)
ax.text(-0.5, -2.05, "so measuring q3, q4 does not collapse the secret. "
        "Recovery verified with fidelity = 1 for all 4 errors × 6 test states.", fontsize=13.5, color=GREY)
legend(ax, -0.5, -2.95)

save(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "level1_circuit.png"))
