"""
Draws the Level 2 (phase-flip) circuit as a presentation-ready PNG.

    pip install matplotlib
    python diagrams/draw_level2_circuit.py      (run from the level1_python folder)

Qubit numbering and gate order match level2.py exactly:
encode (CNOT q0->q1, q0->q2), H on q0,q1,q2, error, H on q0,q1,q2, then
Level 1's syndrome (q3 = q0 XOR q1, q4 = q1 XOR q2), correction and decode.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit_style import (BLUE, GREEN, GREY, ORANGE, PURPLE, RED, box_at, classical,  # noqa: E402
                          classical_up, cnot_at, error_box, legend, meter_at, new_figure, save, stage,
                          state_note, syndrome_table, wire)

Y = {0: 5.0, 1: 4.0, 2: 3.0, 3: 1.6, 4: 0.6}
X_START, X_END, HELPER_END = 1.2, 19.0, 13.6
TOP = Y[0]

fig, ax = new_figure(22, 10.2, (-0.6, 21.8), (-4.4, 8.8))

# --- wires -----------------------------------------------------------------
wire(ax, Y[0], X_START, X_END, "q0", r"$|\psi\rangle$")
wire(ax, Y[1], X_START, X_END, "q1", r"$|0\rangle$")
wire(ax, Y[2], X_START, X_END, "q2", r"$|0\rangle$")
wire(ax, Y[3], X_START, HELPER_END, "q3", r"$|0\rangle$", ORANGE)
wire(ax, Y[4], X_START, HELPER_END, "q4", r"$|0\rangle$", ORANGE)
ax.text(-0.5, 8.45, r"Level 2 (phase flips).  Unknown qubit  $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$"
        "  on q0", fontsize=17, ha="left", va="center")
ax.text(X_START - 0.1, 2.25, "data", fontsize=12, ha="right", color=GREY, style="italic")
ax.text(X_START - 0.1, -0.05, "helpers", fontsize=12, ha="right", color=ORANGE, style="italic")

# --- stages ----------------------------------------------------------------
for i, (x0, x1, name, color) in enumerate([
        (1.45, 3.05, "1. Encode", BLUE), (3.3, 4.5, "2. H in", PURPLE),
        (4.75, 6.15, "3. Error", RED), (6.4, 7.6, "4. H out", PURPLE),
        (7.85, 11.05, "5. Syndrome", ORANGE), (11.3, 12.4, "6. Measure", ORANGE),
        (12.65, 14.15, "7. Correct", GREEN), (14.4, 16.0, "8. Decode", BLUE)]):
    stage(ax, x0, x1, -0.25, 5.5, name, color, label_drop=0.45 if i in (1, 3) else 0.0)

# 1. encode: CNOT q0->q1, CNOT q0->q2 (exactly Level 1)
cnot_at(ax, 1.9, Y[0], Y[1])
cnot_at(ax, 2.6, Y[0], Y[2])
state_note(ax, 2.25, r"$\alpha|000\rangle + \beta|111\rangle$", TOP)

# 2. H on all three data qubits
for q in (0, 1, 2):
    box_at(ax, 3.9, Y[q], "H", PURPLE)
state_note(ax, 3.9, r"$\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$", TOP, PURPLE, row=1)

# 3. error
error_box(ax, 5.45, Y[0], Y[2], "E", r"$E \in \{I, Z_0, Z_1, Z_2\}$")
state_note(ax, 5.45, "e.g. $Z_1$:  " + r"$\alpha|{+}{-}{+}\rangle + \beta|{-}{+}{-}\rangle$", TOP, RED)

# 4. H again: HZH = X on the hit qubit, HH = I elsewhere
for q in (0, 1, 2):
    box_at(ax, 7.0, Y[q], "H", PURPLE)
state_note(ax, 7.0, r"$HZH = X$:  $\alpha|010\rangle + \beta|101\rangle$", TOP, PURPLE, row=2)

# 5. syndrome (Level 1, unchanged)
cnot_at(ax, 8.3, Y[0], Y[3], ORANGE)
cnot_at(ax, 9.0, Y[1], Y[3], ORANGE)
cnot_at(ax, 9.9, Y[1], Y[4], ORANGE)
cnot_at(ax, 10.6, Y[2], Y[4], ORANGE)
ax.text(8.65, Y[3] - 0.5, "q3 = q0 XOR q1", fontsize=12.5, ha="center", color=ORANGE)
ax.text(10.25, Y[4] - 0.5, "q4 = q1 XOR q2", fontsize=12.5, ha="center", color=ORANGE)
state_note(ax, 9.45, "parities copied to helpers", TOP, ORANGE)

# 6. measure
for q, name in ((3, "$s_1$"), (4, "$s_2$")):
    meter_at(ax, 11.85, Y[q])
    classical(ax, 12.2, 13.4, Y[q])
    ax.text(12.85, Y[q] + 0.3, name, fontsize=14, ha="center", color=GREY)
classical_up(ax, 13.4, Y[4], Y[2] - 0.3)
state_note(ax, 11.85, "certain result (11 for $Z_1$)", TOP, ORANGE, row=1)

# 7. correct
for q in (0, 1, 2):
    box_at(ax, 13.4, Y[q], "X?", GREEN, dashed=True)
state_note(ax, 13.4, r"$\alpha|000\rangle + \beta|111\rangle$", TOP, GREEN)

# 8. decode
cnot_at(ax, 14.85, Y[0], Y[2])
cnot_at(ax, 15.55, Y[0], Y[1])
state_note(ax, 15.2, r"$\alpha|0\rangle + \beta|1\rangle$ on q0", TOP, row=1)

# outputs
ax.text(X_END + 0.15, Y[0], r"$\alpha|0\rangle + \beta|1\rangle$", fontsize=17, va="center", color=GREEN,
        weight="bold")
ax.text(X_END + 0.15, Y[1], r"$|0\rangle$", fontsize=17, va="center")
ax.text(X_END + 0.15, Y[2], r"$|0\rangle$", fontsize=17, va="center")

syndrome_table(ax, 16.5, 1.95, [("s1 s2", "phase flip on"), ("0  0", "none"), ("1  0", "q0 (X on q0)"),
                                ("1  1", "q1 (X on q1)"), ("0  1", "q2 (X on q2)")])

# footer + key
ax.text(-0.5, -1.75, "A Z on q0, q1 or q2 gives the SAME state on α|000⟩+β|111⟩, so we store the data in the "
        "H frame (α|+++⟩+β|−−−⟩). There a Z swaps + and −,", fontsize=13.5, color=GREY)
ax.text(-0.5, -2.3, "and the second H layer turns it into a bit flip (HZH = X), which Level 1's helpers "
        "locate. Verified: fidelity = 1 for all 4 errors × 6 test states.", fontsize=13.5, color=GREY)
legend(ax, -0.5, -3.3, include_h=True)

save(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "level2_circuit.png"))
