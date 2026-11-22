"""
Level 1 "Bit-Flip Mines": the 3-qubit repetition code, built on simulator.py.

Qubit layout (5 qubits in total)
--------------------------------
    q0, q1, q2  : DATA qubits. Together they hold ONE protected (logical) qubit.
    q3          : helper ("ancilla") that checks: do q0 and q1 agree?
    q4          : helper ("ancilla") that checks: do q1 and q2 agree?

The five stages
---------------
    1. encode   a|0> + b|1>    ->   a|000> + b|111>
    2. error    maybe flip one data qubit (I, X0, X1 or X2)
    3. syndrome copy the two "do they agree?" answers onto q3, q4 and measure them
    4. recover  look the answer up in a table and flip the guilty qubit back
    5. decode   undo step 1 so q0 holds a|0> + b|1> again

Every step uses only X gates, CNOT gates and measurements, so it maps
one-to-one onto a Qiskit circuit later (see PORTING notes in the README).
"""

import numpy as np

import simulator as sim

DATA = [0, 1, 2]
ANCILLA_01 = 3   # parity of q0 and q1
ANCILLA_12 = 4   # parity of q1 and q2
NUM_QUBITS = 5

# The six test states required by the challenge: name -> (alpha, beta)
TEST_STATES = {
    "|0>":  (1, 0),
    "|1>":  (0, 1),
    "|+>":  (1 / np.sqrt(2), 1 / np.sqrt(2)),
    "|->":  (1 / np.sqrt(2), -1 / np.sqrt(2)),
    "|+i>": (1 / np.sqrt(2), 1j / np.sqrt(2)),
    "|-i>": (1 / np.sqrt(2), -1j / np.sqrt(2)),
}

# The four permitted errors: name -> which data qubit gets an X (None = no error)
ERRORS = {"I": None, "X0": 0, "X1": 1, "X2": 2}

# Syndrome lookup table: (result of q3, result of q4) -> qubit to fix
#   q3 = 1 means q0 and q1 disagree, q4 = 1 means q1 and q2 disagree.
#   q0 flipped -> only the q0/q1 check fails      -> (1, 0)
#   q1 flipped -> both checks fail (q1 is in both) -> (1, 1)
#   q2 flipped -> only the q1/q2 check fails      -> (0, 1)
SYNDROME_TABLE = {
    (0, 0): None,
    (1, 0): 0,
    (1, 1): 1,
    (0, 1): 2,
}


def prepare(alpha, beta):
    """The state to protect sits on q0; every other qubit starts at |0>."""
    psi = sim.single_qubit_state(alpha, beta)
    return sim.combine(psi, sim.zero_state(NUM_QUBITS - 1))


def encode(state):
    """a|0>+b|1> on q0  ->  a|000> + b|111> on q0 q1 q2 (two CNOTs copy the bit value)."""
    state = sim.apply_cnot(state, control=0, target=1)
    state = sim.apply_cnot(state, control=0, target=2)
    return state


def apply_error(state, error_name):
    """Inject one of the permitted errors I, X0, X1, X2."""
    qubit = ERRORS[error_name]
    if qubit is not None:
        state = sim.apply_gate(state, sim.X, qubit)
    return state


def extract_syndrome(state):
    """
    Compute the two parities onto the ancillas.

    After this, q3 = q0 XOR q1 and q4 = q1 XOR q2. The trick: in
    a|000> + b|111> both branches have the SAME parities, so the ancillas
    learn "where is the odd one out" but nothing about a or b.
    """
    state = sim.apply_cnot(state, control=0, target=ANCILLA_01)
    state = sim.apply_cnot(state, control=1, target=ANCILLA_01)
    state = sim.apply_cnot(state, control=1, target=ANCILLA_12)
    state = sim.apply_cnot(state, control=2, target=ANCILLA_12)
    return state


def measure_syndrome(state, rng=None):
    """Measure the two ancillas. Returns ((s1, s2), state_after)."""
    s1, state = sim.measure(state, ANCILLA_01, rng)
    s2, state = sim.measure(state, ANCILLA_12, rng)
    return (s1, s2), state


def recover(state, syndrome):
    """Flip back the qubit the lookup table blames (if any)."""
    qubit = SYNDROME_TABLE[syndrome]
    if qubit is not None:
        state = sim.apply_gate(state, sim.X, qubit)
    return state, qubit


def decode(state):
    """Undo encode(): CNOTs in reverse order, so q1, q2 return to |0>."""
    state = sim.apply_cnot(state, control=0, target=2)
    state = sim.apply_cnot(state, control=0, target=1)
    return state


def logical_state(alpha, beta):
    """The ideal encoded 3-qubit state a|000> + b|111> (used to check our work)."""
    psi = sim.single_qubit_state(alpha, beta)
    ideal = np.zeros(8, dtype=complex)
    ideal[0b000] = psi[0]
    ideal[0b111] = psi[1]
    return ideal


def run(alpha, beta, error_name, correct=True, rng=None):
    """
    Run the whole Level 1 circuit once.

    Returns a dict with the syndrome, which qubit was fixed, and two fidelities:
      * fidelity_encoded : data qubits after recovery vs. ideal a|000>+b|111>
      * fidelity_decoded : q0 after decoding vs. the original a|0>+b|1>
    Set correct=False to skip recovery (useful to show what goes wrong without it).
    """
    psi = sim.single_qubit_state(alpha, beta)

    state = prepare(alpha, beta)
    state = encode(state)
    state = apply_error(state, error_name)
    state = extract_syndrome(state)
    syndrome, state = measure_syndrome(state, rng)
    fixed_qubit = None
    if correct:
        state, fixed_qubit = recover(state, syndrome)

    fidelity_encoded = sim.fidelity(logical_state(alpha, beta), state, qubits=DATA)
    state = decode(state)
    fidelity_decoded = sim.fidelity(psi, state, qubits=[0])

    return {
        "syndrome": syndrome,
        "fixed_qubit": fixed_qubit,
        "fidelity_encoded": fidelity_encoded,
        "fidelity_decoded": fidelity_decoded,
        "final_state": state,
    }


if __name__ == "__main__":
    # Quick summary table: every error x every test state.
    print(f"{'state':>6} {'error':>5} {'syndrome':>9} {'fixed':>6} {'fidelity':>9}")
    for state_name, (a, b) in TEST_STATES.items():
        for error_name in ERRORS:
            r = run(a, b, error_name)
            fixed = "-" if r["fixed_qubit"] is None else f"q{r['fixed_qubit']}"
            print(f"{state_name:>6} {error_name:>5} {str(r['syndrome']):>9} "
                  f"{fixed:>6} {r['fidelity_decoded']:>9.6f}")
