"""
Step-by-step walkthrough of Level 4 (Mystery Mines): detect the error TYPE.

Run it:
    python walkthrough_level4.py               # default: error Y1
    python walkthrough_level4.py Z3            # any of I, X0..X3, Y0..Y3, Z0..Z3
    python walkthrough_level4.py X2 --pause    # wait for Enter between stages

Printout: +0.300 |0000 000> means amplitude 0.300 on data qubits q0 q1 q2 q3 =
0000 and helper qubits q4 q5 q6 = 000.  (q4 = phase helper, q5, q6 = bit helpers)
"""

import sys

import level4
import simulator as sim

ALPHA, BETA = 0.6, 0.8
GROUPS = [4, 3]

error_name = next((a for a in sys.argv[1:] if not a.startswith("--")), "Y1")
if error_name not in level4.ERRORS:
    sys.exit(f"Unknown error {error_name!r}. Choose one of: {', '.join(level4.ERRORS)}")
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
state = level4.prepare(ALPHA, BETA)
stage(
    "STAGE 0: the secret sits on q2",
    f"q2 holds {ALPHA}|0> + {BETA}|1>. Everything else starts at 0.",
    state,
)

state = sim.apply_gate(state, sim.H, 1)
state = sim.apply_cnot(state, control=2, target=3)
stage(
    "STAGE 1a: encode, part 1 (H on q1, then CNOT q2 -> q3)",
    """
H puts q1 into "0 and 1 at once". The CNOT copies the secret's bit value onto
q3, so q2 and q3 now always agree.
""",
    state,
)

state = sim.apply_cnot(state, control=1, target=0)
state = sim.apply_cnot(state, control=1, target=2)
state = sim.apply_cnot(state, control=1, target=3)
stage(
    "STAGE 1b: encode, part 2 (CNOT q1 -> q0, q2, q3)",
    f"""
Wherever q1 is 1, flip the other three. The encoded state is
  {ALPHA} (|0000> + |1111>)/sqrt2  +  {BETA} (|0011> + |1100>)/sqrt2
Three patterns to remember, true for EVERY configuration above:
  * q0 = q1     * q2 = q3     * flipping all four bits gives the same state back
The secret is spread over all four qubits: no single qubit holds it.
""",
    state,
)

state = level4.apply_error(state, error_name)
stage(
    f"STAGE 2: the mine goes off (error = {error_name})",
    {
        "I": "No error. Nothing changes.",
        "X": "A bit flip: one qubit's 0/1 values swap, breaking 'q0 = q1' or 'q2 = q3'.",
        "Z": "A phase flip: some minus signs appear. The bit patterns are untouched,\n"
             "but 'flip all four gives the same state' is now broken.",
        "Y": "Y = iXZ: a bit flip AND minus signs (and a harmless overall i).\n"
             "It breaks both kinds of pattern.",
    }[error_name[0]],
    state,
)

state = level4.phase_check(state)
stage(
    "STAGE 3: phase check onto q4 (H, CNOT q4 -> each data qubit, H)",
    """
The helper q4 is put in "0 and 1". In its 1 part, all four data bits are
flipped. If the data does not care about being flipped (no phase error), the
two parts of q4 recombine to 0 at the final H. If a Z put a minus sign in the
way, they recombine to 1. Either way q4 ends with a definite value, and the
data qubits end up exactly as they were.
""",
    state,
)

state = level4.bit_checks(state)
stage(
    "STAGE 4: bit checks onto q5 and q6 (like Level 1)",
    """
q5 = q0 XOR q1  ("do q0 and q1 disagree?")
q6 = q2 XOR q3  ("do q2 and q3 disagree?")
""",
    state,
)

readings, state = level4.measure_helpers(state)
detected = level4.classify(readings)
bit_alarm = readings["bit01"] | readings["bit23"]
table = "\n".join(f"    {k} -> {v}" for k, v in level4.DECODE_TABLE.items())
stage(
    f"STAGE 5: measure only the helpers -> detected type {detected}",
    f"""
q4 (phase) = {readings['phase']},  q5 = {readings['bit01']},  q6 = {readings['bit23']}
bit alarm = q5 OR q6 = {bit_alarm},  phase alarm = q4 = {readings['phase']}
Decode table (bit alarm, phase alarm):
{table}
-> ({bit_alarm}, {readings['phase']}) means {detected}. The real error was {error_name}: {"CORRECT" if detected == error_name[0] else "WRONG"}.
The amplitudes {ALPHA} and {BETA} are still sitting in the data qubits:
we learned the error type without ever measuring the secret.
""",
    state,
)

expected = level4.apply_error(level4.logical_state(ALPHA, BETA), error_name)
print("\n" + "=" * 72)
print("RESULT")
print("=" * 72)
print(f"Detected {detected}, actual {error_name}.")
print(f"Fidelity of data qubits vs (error applied to the clean codeword): "
      f"{sim.fidelity(expected, state, qubits=level4.DATA):.6f}")
print("(1.000000 = our checks did not disturb the encoded secret at all)")

# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("LIMITATIONS")
print("=" * 72)
r0 = level4.run(ALPHA, BETA, "X0")["readings"]
r1 = level4.run(ALPHA, BETA, "X1")["readings"]
print(f"""1. Type, not location: X0 gives readings {tuple(r0.values())} and X1 gives
   {tuple(r1.values())}. Identical, so we cannot tell which of q0/q1 flipped.
   (Same for all four Z positions.) That is why Level 4 only asks for the type.""")
state = level4.encode(level4.prepare(ALPHA, BETA))
state = level4.apply_error(level4.apply_error(state, "X0"), "X1")
state = level4.bit_checks(level4.phase_check(state))
readings, _ = level4.measure_helpers(state)
print(f"""2. Two errors can hide: X0 and X1 together give readings {tuple(readings.values())},
   which reads as '{level4.classify(readings)}' (no error). The code assumes at most ONE error.""")
