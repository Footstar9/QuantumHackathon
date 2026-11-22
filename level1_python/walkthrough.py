"""
Step-by-step walkthrough of Level 1 (Bit-Flip Mines).

Run it:
    python walkthrough.py                 # default: error on qubit 1
    python walkthrough.py X0              # pick the error: I, X0, X1 or X2
    python walkthrough.py X2 --pause      # wait for Enter between stages (nice for demos)

It prints the full 5-qubit state after every stage. Each line looks like
    +0.600 |000 00>
meaning "amplitude 0.600 on the configuration where data qubits q0 q1 q2
are 000 and helper qubits q3 q4 are 00".
"""

import sys

import numpy as np

import level1
import simulator as sim

# We protect the state 0.6|0> + 0.8|1>. These two numbers are deliberately
# different so you can watch them travel through the circuit untouched.
ALPHA, BETA = 0.6, 0.8
GROUPS = [3, 2]  # print as |data helpers>

error_name = next((a for a in sys.argv[1:] if not a.startswith("--")), "X1")
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
state = level1.prepare(ALPHA, BETA)
stage(
    "STAGE 0: the information we want to protect",
    f"""
Qubit q0 holds {ALPHA}|0> + {BETA}|1>. It is not "0 or 1": it is both at once,
with amplitudes {ALPHA} and {BETA}. If we measured it we would see 0 with
probability {ALPHA**2:.2f} and 1 with probability {BETA**2:.2f}, but measuring
would destroy it. Our job is to keep those two numbers safe.
All other qubits start at 0.
""",
    state,
)

# ---------------------------------------------------------------------------
state = level1.encode(state)
stage(
    "STAGE 1: encode (spread one qubit over three)",
    f"""
Two CNOT gates: "flip q1 if q0 is 1" and "flip q2 if q0 is 1".
The 0-branch stays 000 and the 1-branch becomes 111, giving
{ALPHA}|000> + {BETA}|111>.
This is NOT three copies of the state (quantum physics forbids copying).
It is one shared state where all three qubits always agree.
""",
    state,
)

# ---------------------------------------------------------------------------
state = level1.apply_error(state, error_name)
where = level1.ERRORS[error_name]
stage(
    f"STAGE 2: the mine goes off (error = {error_name})",
    ("No error this time. Nothing changes." if where is None else f"""
An X gate (bit flip) hits data qubit q{where}. Look at the kets: in BOTH
branches, q{where} is now the odd one out. The amplitudes {ALPHA} and {BETA}
have not changed, they just sit on different configurations.
We pretend not to know which qubit was hit; the circuit has to find out.
"""),
    state,
)

# ---------------------------------------------------------------------------
state = level1.extract_syndrome(state)
stage(
    "STAGE 3: ask two yes/no questions (syndrome extraction)",
    """
Four CNOTs copy two PARITIES onto the helper qubits:
  q3 = q0 XOR q1   ("do q0 and q1 disagree?")
  q4 = q1 XOR q2   ("do q1 and q2 disagree?")
Key point: both branches (the a-branch and the b-branch) give the SAME
answers, so the helpers end up with a definite value. They learned WHERE
the flip is, but nothing about the protected numbers a and b.
""",
    state,
)

# ---------------------------------------------------------------------------
syndrome, state = level1.measure_syndrome(state)
stage(
    f"STAGE 4: measure only the helpers -> syndrome = {syndrome}",
    f"""
We measure q3 and q4 (never the data qubits). Result: q3={syndrome[0]}, q4={syndrome[1]}.
Because the helpers already had a definite value, this measurement is
certain (probability 1) and does not disturb the data. The amplitudes
{ALPHA} and {BETA} are still there.
""",
    state,
)

# ---------------------------------------------------------------------------
state, fixed = level1.recover(state, syndrome)
table = "\n".join(
    f"    {s} -> {'no error' if q is None else f'flip q{q}'}"
    for s, q in level1.SYNDROME_TABLE.items()
)
stage(
    "STAGE 5: recover (look up the table, flip the guilty qubit back)",
    f"""
Lookup table:
{table}
Syndrome {syndrome} -> {'do nothing' if fixed is None else f'apply X to q{fixed}'}.
The data qubits are back to {ALPHA}|000> + {BETA}|111>.
(The helpers still show the syndrome; they would be reset before reuse.)
""",
    state,
)
f_enc = sim.fidelity(level1.logical_state(ALPHA, BETA), state, qubits=level1.DATA)

# ---------------------------------------------------------------------------
state = level1.decode(state)
stage(
    "STAGE 6: decode (undo stage 1)",
    f"""
Same two CNOTs in reverse order. q1 and q2 go back to 0 and q0 again holds
{ALPHA}|0> + {BETA}|1>.
""",
    state,
)
psi = sim.single_qubit_state(ALPHA, BETA)
f_dec = sim.fidelity(psi, state, qubits=[0])

print("\n" + "=" * 72)
print("RESULT")
print("=" * 72)
print(f"Fidelity of data qubits vs ideal a|000>+b|111> after recovery : {f_enc:.6f}")
print(f"Fidelity of q0 vs the original a|0>+b|1> after decoding       : {f_dec:.6f}")
print("(1.000000 means perfectly recovered)")

# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("LIMITATION: what if TWO qubits flip?")
print("=" * 72)
state = level1.prepare(ALPHA, BETA)
state = level1.encode(state)
state = sim.apply_gate(state, sim.X, 0)
state = sim.apply_gate(state, sim.X, 1)
state = level1.extract_syndrome(state)
syndrome, state = level1.measure_syndrome(state)
state, fixed = level1.recover(state, syndrome)
state = level1.decode(state)
print(f"Errors X0 and X1 give syndrome {syndrome}, which looks exactly like a single")
print(f"flip on q{fixed}. The circuit 'fixes' q{fixed}, so now ALL THREE qubits are flipped.")
print("The data looks healthy (000 / 111) but a and b have swapped places:")
print(sim.show(state, GROUPS))
print(f"q0 is now {BETA}|0> + {ALPHA}|1> instead of {ALPHA}|0> + {BETA}|1>. The code corrects ONE flip, not two.")
print("(This is why a real device needs errors to be rare: two at once beat this code.)")
