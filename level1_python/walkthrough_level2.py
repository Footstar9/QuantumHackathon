"""
Step-by-step walkthrough of Level 2 (Phase-Flip Mines).

Run it:
    python walkthrough_level2.py               # default: error Z1
    python walkthrough_level2.py Z0            # pick the error: I, Z0, Z1 or Z2
    python walkthrough_level2.py Z2 --pause    # wait for Enter between stages

Same printout style as walkthrough.py:  +0.600 |000 00>  means amplitude 0.600
on data qubits q0 q1 q2 = 000 and helper qubits q3 q4 = 00.
"""

import sys

import level1
import level2
import simulator as sim

ALPHA, BETA = 0.6, 0.8
GROUPS = [3, 2]

error_name = next((a for a in sys.argv[1:] if not a.startswith("--")), "Z1")
PAUSE = "--pause" in sys.argv


def stage(title, explanation, state):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)
    print(explanation.strip())
    print("\nState now:")
    print(sim.show(state, GROUPS))
    if PAUSE:
        input("\n[press Enter for the next stage]")


# ---------------------------------------------------------------------------
# Why Level 1 is not enough
# ---------------------------------------------------------------------------
print("=" * 72)
print("WHY LEVEL 1 FAILS: a phase flip on the plain codeword a|000> + b|111>")
print("=" * 72)
plain = level1.encode(level1.prepare(ALPHA, BETA))
for q in level2.DATA:
    hit = sim.apply_gate(plain, sim.Z, q)
    print(f"\nZ on q{q}:")
    print(sim.show(hit, GROUPS))
print(f"""
All three give the SAME state {ALPHA}|000> - {BETA}|111>: Z only adds a minus
sign to the |111> branch, whichever qubit it hits. The parity checks see
000 and 111 (all agree) and report "no error", yet the sign is wrong.
We need a way to make Z errors look like bit flips.""")
if PAUSE:
    input("\n[press Enter to start the Level 2 circuit]")

# ---------------------------------------------------------------------------
state = level1.prepare(ALPHA, BETA)
stage(
    "STAGE 0: the information we want to protect",
    f"q0 holds {ALPHA}|0> + {BETA}|1>. All other qubits start at 0.",
    state,
)

state = level1.encode(state)
stage(
    "STAGE 1: encode (exactly Level 1's two CNOTs)",
    f"Same as Level 1: {ALPHA}|000> + {BETA}|111>.",
    state,
)

state = level2.hadamard_layer(state)
stage(
    "STAGE 2: enter the H frame (Hadamard on q0, q1, q2)",
    f"""
H turns |0> into |+> and |1> into |->, so the stored state is
{ALPHA}|+++> + {BETA}|--->.
Written out in 0s and 1s it looks messy (8 configurations), because each
|+> and |-> is itself a mix of 0 and 1. The two numbers {ALPHA} and {BETA}
are hidden in the signs. Check: the fidelity with a|+++> + b|---> is
{sim.fidelity(level2.stored_logical_state(ALPHA, BETA), state, qubits=level2.DATA):.6f}.
""",
    state,
)

state = level2.apply_error(state, error_name)
where = level2.ERRORS[error_name]
stage(
    f"STAGE 3: the mine goes off (error = {error_name})",
    ("No error this time. Nothing changes." if where is None else f"""
A Z gate hits q{where}. In the H frame, Z swaps |+> and |-> on that qubit
(Z|+> = |->), so in both branches q{where} is now the odd one out:
{ALPHA}|...> + {BETA}|...> with q{where} pointing the other way.
In the 0/1 printout you only see some minus signs move around.
"""),
    state,
)

state = level2.hadamard_layer(state)
stage(
    "STAGE 4: leave the H frame (Hadamard on q0, q1, q2 again)",
    ("No error: H H = I, so we are back to the plain codeword." if where is None else f"""
On q{where}: H Z H = X, so the phase flip has turned into a BIT FLIP.
On the other qubits: H H = I, nothing happens.
This is now exactly the situation of Level 1: one flipped bit on q{where}.
"""),
    state,
)

state = level1.extract_syndrome(state)
syndrome, state = level1.measure_syndrome(state)
stage(
    f"STAGE 5: Level 1 syndrome, unchanged -> syndrome = {syndrome}",
    """
Same four CNOTs and measurement of q3, q4 as Level 1.
  q3 = q0 XOR q1,  q4 = q1 XOR q2
The answer is certain and reveals nothing about a or b.
""",
    state,
)

state, fixed = level1.recover(state, syndrome)
stage(
    "STAGE 6: Level 1 recovery, unchanged",
    f"Syndrome {syndrome} -> {'do nothing' if fixed is None else f'apply X to q{fixed}'}.",
    state,
)
f_enc = sim.fidelity(level1.logical_state(ALPHA, BETA), state, qubits=level2.DATA)

state = level1.decode(state)
stage(
    "STAGE 7: Level 1 decode, unchanged",
    f"q0 is back to {ALPHA}|0> + {BETA}|1>.",
    state,
)
psi = sim.single_qubit_state(ALPHA, BETA)

print("\n" + "=" * 72)
print("RESULT")
print("=" * 72)
print(f"Fidelity of data qubits vs a|000>+b|111> after recovery : {f_enc:.6f}")
print(f"Fidelity of q0 vs the original a|0>+b|1> after decoding : {sim.fidelity(psi, state, qubits=[0]):.6f}")

# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("LIMITATION: this code cannot fix BIT flips any more")
print("=" * 72)
r = level2.run(ALPHA, BETA, "X1")
print(f"""An X on q1 in the H frame becomes H X H = Z after the second Hadamard
layer, i.e. a phase flip on the plain codeword. As shown at the top, the
parity checks cannot see that: syndrome = {r['syndrome']}, nothing is fixed, and
q0 ends as {ALPHA}|0> - {BETA}|1>. Fidelity = {r['fidelity_decoded']:.6f} (not 1).
Level 1 fixes X but not Z; Level 2 fixes Z but not X. Level 3 needs both.""")
