"""
Draws the Level 4 (error-type detection) circuit as a presentation-ready PNG.

    pip install matplotlib
    python diagrams/draw_level4_circuit.py      (run from the level1_python folder)

Qubit numbering and gate order match level4.py exactly:
q0..q3 data (secret starts on q2), q4 phase helper, q5 = q0 XOR q1, q6 = q2 XOR q3.
encode: H q1; CNOT q2->q3; CNOT q1->q0, q1->q2, q1->q3
phase check: H q4; CNOT q4->q0, q4->q1, q4->q2, q4->q3; H q4
bit checks: CNOT q0->q5, q1->q5, q2->q6, q3->q6; then measure q4, q5, q6
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit_style import (BLUE, GREEN, GREY, ORANGE, PURPLE, RED, box_at, classical,  # noqa: E402
                          cnot_at, error_box, legend, meter_at, new_figure, save, stage, state_note,
                          syndrome_table, wire)

Y = {0: 6.0, 1: 5.0, 2: 4.0, 3: 3.0, 4: 1.7, 5: 0.8, 6: -0.1}
X_START, X_END, HELPER_END = 1.2, 16.0, 15.5
TOP = Y[0]
TEAL = "#00796b"   # bit-check colour, so the two kinds of check are easy to tell apart

fig, ax = new_figure(22, 11.6, (-0.6, 21.8), (-5.2, 9.6))

# --- wires -----------------------------------------------------------------
wire(ax, Y[0], X_START, X_END, "q0", r"$|0\rangle$")
wire(ax, Y[1], X_START, X_END, "q1", r"$|0\rangle$")
wire(ax, Y[2], X_START, X_END, "q2", r"$|\psi\rangle$")
wire(ax, Y[3], X_START, X_END, "q3", r"$|0\rangle$")
wire(ax, Y[4], X_START, 14.4, "q4", r"$|0\rangle$", ORANGE)
wire(ax, Y[5], X_START, 14.4, "q5", r"$|0\rangle$", TEAL)
wire(ax, Y[6], X_START, 14.4, "q6", r"$|0\rangle$", TEAL)
ax.text(-0.5, 9.2, r"Level 4 (detect the error type).  Unknown qubit  "
        r"$|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$  starts on q2", fontsize=17, ha="left", va="center")
ax.text(X_START - 0.1, 2.55, "data", fontsize=12, ha="right", color=GREY, style="italic")
ax.text(X_START - 0.1, 2.0, "phase helper", fontsize=12, ha="right", color=ORANGE, style="italic")
ax.text(X_START - 0.1, -0.55, "bit helpers", fontsize=12, ha="right", color=TEAL, style="italic")

# --- stages ----------------------------------------------------------------
for x0, x1, name, color in [(1.45, 5.05, "1. Encode", BLUE), (5.3, 6.7, "2. Error", RED),
                            (6.95, 10.75, "3. Phase check", ORANGE), (11.0, 13.85, "4. Bit checks", TEAL),
                            (14.1, 15.1, "5. Measure", GREY)]:
    stage(ax, x0, x1, -1.05, 6.5, name, color)

# 1. encode
box_at(ax, 1.9, Y[1], "H", PURPLE)
cnot_at(ax, 2.6, Y[2], Y[3])          # q2 -> q3
cnot_at(ax, 3.3, Y[1], Y[0])          # q1 -> q0
cnot_at(ax, 4.0, Y[1], Y[2])          # q1 -> q2
cnot_at(ax, 4.7, Y[1], Y[3])          # q1 -> q3
state_note(ax, 3.25, r"$\frac{\alpha}{\sqrt{2}}(|0000\rangle + |1111\rangle) + "
           r"\frac{\beta}{\sqrt{2}}(|0011\rangle + |1100\rangle)$", TOP)

# 2. error
error_box(ax, 6.0, Y[0], Y[3], "E", r"one of $X, Y, Z$ on q0..q3, or $I$")
state_note(ax, 7.4, r"e.g. $Y_1$:  $i\,[\frac{\alpha}{\sqrt{2}}(|0100\rangle - |1011\rangle) + "
           r"\frac{\beta}{\sqrt{2}}(|0111\rangle - |1000\rangle)]$", TOP, RED, row=1)

# 3. phase check: helper q4 is the CONTROL, data qubits are targets
box_at(ax, 7.4, Y[4], "H", PURPLE)
for x, q in zip((8.1, 8.7, 9.3, 9.9), (0, 1, 2, 3)):
    cnot_at(ax, x, Y[4], Y[q], ORANGE)
box_at(ax, 10.45, Y[4], "H", PURPLE)
ax.text(9.0, Y[4] - 0.55, "q4 is the CONTROL (dot):\nit flips all four data qubits", fontsize=12,
        ha="center", va="top", color=ORANGE)
state_note(ax, 8.9, "q4 = 1 if Z or Y", TOP, ORANGE, row=0)

# 4. bit checks: data qubits are controls, helpers q5, q6 are TARGETS
cnot_at(ax, 11.4, Y[0], Y[5], TEAL)
cnot_at(ax, 12.0, Y[1], Y[5], TEAL)
cnot_at(ax, 12.8, Y[2], Y[6], TEAL)
cnot_at(ax, 13.4, Y[3], Y[6], TEAL)
ax.text(12.4, Y[6] - 0.35, "q5, q6 are TARGETS (circle with +)", fontsize=12, ha="center", va="top", color=TEAL)
state_note(ax, 12.4, "q5 = q0 XOR q1,  q6 = q2 XOR q3", TOP, TEAL, row=2)

# 5. measure helpers only
for q, c in ((4, ORANGE), (5, TEAL), (6, TEAL)):
    meter_at(ax, 14.6, Y[q], c)
    classical(ax, 14.95, 16.0, Y[q])
state_note(ax, 14.6, "e.g. $Y_1$: q4 q5 q6 = 1 1 0", TOP, GREY, row=0)

# outputs
ax.text(X_END + 0.15, Y[0] + 0.05, "data: error × codeword\n(secret NOT measured)", fontsize=14,
        va="center", color=GREEN, weight="bold")
ax.text(16.15, Y[4], "phase alarm = q4", fontsize=13.5, va="center", color=ORANGE)
ax.text(16.15, (Y[5] + Y[6]) / 2, "bit alarm = q5 OR q6", fontsize=13.5, va="center", color=TEAL)

syndrome_table(ax, 16.4, 4.2, [("bit phase", "type"), ("0    0", "I (none)"), ("1    0", "X"),
                                ("0    1", "Z"), ("1    1", "Y")], col2=2.4, width=4.4)

# footer + key
ax.text(-0.5, -2.35, "Every codeword has q0 = q1, q2 = q3, and is unchanged when all four bits flip. "
        "X breaks an equality (bit alarm), Z breaks the flip symmetry (phase alarm),", fontsize=13.5, color=GREY)
ax.text(-0.5, -2.9, "Y breaks both. The checks commute, so they can be done in either order. Type is found, "
        "location is not (e.g. X0 and X1 read the same). Verified on all 13 errors × 6 states + 50 random.",
        fontsize=13.5, color=GREY)
legend(ax, -0.5, -3.85, include_h=True, correction=None)

save(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "level4_circuit.png"))
