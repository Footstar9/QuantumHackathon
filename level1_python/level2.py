"""
Level 2 "Phase-Flip Mines": correct an unknown Z error (I, Z0, Z1 or Z2).

Why Level 1 alone is not enough
-------------------------------
A Z gate does not flip a bit, it puts a minus sign on the |1> part of one qubit.
On the Level 1 codeword a|000> + b|111>, a Z on ANY of the three qubits does
the same thing: it turns it into a|000> - b|111>. The three errors are
indistinguishable, and the parity checks see nothing (000 and 111 still agree).

The trick: change the frame with Hadamards
------------------------------------------
The Hadamard gate swaps the roles of X and Z:   H X H = Z   and   H Z H = X.
So we store the data "sideways" in the H frame:

    1. encode         a|0>+b|1>  ->  a|000> + b|111>          (Level 1's CNOTs)
    2. H on q0,q1,q2  ->  a|+++> + b|--->                     (stored state)
    3. error          maybe Z on one data qubit
    4. H on q0,q1,q2  the hit qubit sees H Z H = X, the others see H H = I
                      -> we are back to a Level 1 codeword with (maybe) ONE BIT FLIP
    5. Level 1 syndrome, recovery and decode, completely unchanged.

Nothing here is new machinery: it is level1.py with two layers of Hadamards
wrapped around the error.
"""

import numpy as np

import level1
import simulator as sim

DATA = level1.DATA
TEST_STATES = level1.TEST_STATES

# The four permitted errors: name -> which data qubit gets a Z (None = no error)
ERRORS = {"I": None, "Z0": 0, "Z1": 1, "Z2": 2}


def hadamard_layer(state):
    """Apply H to each data qubit: |0> <-> |+>, |1> <-> |->."""
    for q in DATA:
        state = sim.apply_gate(state, sim.H, q)
    return state


def apply_error(state, error_name):
    """
    Inject an error named like "Z1" (gate letter + qubit number), or "I" for none.
    The challenge only uses I, Z0, Z1, Z2; X and Y names are accepted so the
    tests can probe what this code cannot fix.
    """
    if error_name == "I":
        return state
    gate = {"X": sim.X, "Y": sim.Y, "Z": sim.Z}[error_name[0]]
    return sim.apply_gate(state, gate, int(error_name[1]))


def stored_logical_state(alpha, beta):
    """The ideal stored state a|+++> + b|---> on the 3 data qubits."""
    plus = sim.single_qubit_state(1, 1)
    minus = sim.single_qubit_state(1, -1)
    psi = sim.single_qubit_state(alpha, beta)
    return psi[0] * sim.combine(plus, plus, plus) + psi[1] * sim.combine(minus, minus, minus)


def run(alpha, beta, error_name, correct=True, second_hadamard=True, rng=None):
    """
    Run the whole Level 2 circuit once. Same result dict as level1.run().

    second_hadamard=False deliberately breaks the circuit (used by the tests to
    show that the second Hadamard layer is essential).
    """
    psi = sim.single_qubit_state(alpha, beta)

    state = level1.prepare(alpha, beta)
    state = level1.encode(state)
    state = hadamard_layer(state)            # enter the H frame: a|+++> + b|--->
    state = apply_error(state, error_name)
    if second_hadamard:
        state = hadamard_layer(state)        # leave the H frame: Z became X
    state = level1.extract_syndrome(state)
    syndrome, state = level1.measure_syndrome(state, rng)
    fixed_qubit = None
    if correct:
        state, fixed_qubit = level1.recover(state, syndrome)

    fidelity_encoded = sim.fidelity(level1.logical_state(alpha, beta), state, qubits=DATA)
    state = level1.decode(state)
    fidelity_decoded = sim.fidelity(psi, state, qubits=[0])

    return {
        "syndrome": syndrome,
        "fixed_qubit": fixed_qubit,
        "fidelity_encoded": fidelity_encoded,
        "fidelity_decoded": fidelity_decoded,
        "final_state": state,
    }


if __name__ == "__main__":
    print(f"{'state':>6} {'error':>5} {'syndrome':>9} {'fixed':>6} {'fidelity':>9}")
    for state_name, (a, b) in TEST_STATES.items():
        for error_name in ERRORS:
            r = run(a, b, error_name)
            fixed = "-" if r["fixed_qubit"] is None else f"q{r['fixed_qubit']}"
            print(f"{state_name:>6} {error_name:>5} {str(r['syndrome']):>9} "
                  f"{fixed:>6} {r['fidelity_decoded']:>9.6f}")
