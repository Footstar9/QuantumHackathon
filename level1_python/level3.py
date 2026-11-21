"""
Level 3 "Double-Crossed Mines": correct an unknown Y error (I, Y0, Y1 or Y2).

Method: helper (ancilla) qubits + measured syndrome, no Toffoli gates.

The key fact:   Y = i X Z
-------------------------
A Y error is a phase flip (Z) AND a bit flip (X) on the same qubit, plus an
overall factor i. On the Level 1 codeword:

    Y_j (a|000> + b|111>)  =  i X_j (a|000> - b|111>)

    * the X part moves qubit j out of line  -> Level 1's syndrome can see it
    * the Z part flips the sign of b        -> invisible to the syndrome
    * the i is a GLOBAL phase (it multiplies everything), physically invisible

The recipe
----------
    1. encode            Level 1's two CNOTs: a|000> + b|111>
    2. error             maybe Y on one data qubit
    3. syndrome          Level 1's two helper qubits and lookup table, unchanged
    4. if syndrome != (0, 0), it points at qubit j:
         a. X on j       undoes the bit-flip part:  i (a|000> - b|111>)
         b. Z on j       undoes the sign:           i (a|000> + b|111>)
       if syndrome == (0, 0): do NOTHING (adding a Z here would CREATE an error)
    5. decode            Level 1's decode, unchanged

Why step 4b is allowed: the challenge guarantees every non-trivial error is a
Y, so "a bit flip was found" also tells us "a phase flip happened too".
Without that guarantee (independent X and Z errors) this recipe would fail.
"""

import level1
import level2  # only for its general apply_error("Y1") helper
import simulator as sim

DATA = level1.DATA
TEST_STATES = level1.TEST_STATES

# The four permitted errors: name -> which data qubit gets a Y (None = no error)
ERRORS = {"I": None, "Y0": 0, "Y1": 1, "Y2": 2}

apply_error = level2.apply_error   # accepts "I", "X0".."Z2", so tests can probe limits


def recover(state, syndrome, fix_phase=True):
    """
    Level 3 recovery. Returns (state, qubit_fixed).

    fix_phase=False skips the Z step (used by the tests to show it is needed).
    """
    state, qubit = level1.recover(state, syndrome)   # X on qubit j (or nothing)
    if qubit is not None and fix_phase:
        # A Z on ANY one data qubit flips the sign of the |111> branch, so any of
        # q0, q1, q2 would work. We use the same qubit j so that X then Z on j
        # exactly mirrors the Y that hit it (Y = iXZ).
        state = sim.apply_gate(state, sim.Z, qubit)
    return state, qubit


def run(alpha, beta, error_name, correct=True, fix_phase=True, rng=None):
    """Run the whole Level 3 circuit once. Same result dict as level1.run()."""
    psi = sim.single_qubit_state(alpha, beta)

    state = level1.prepare(alpha, beta)
    state = level1.encode(state)
    state = apply_error(state, error_name)
    state = level1.extract_syndrome(state)
    syndrome, state = level1.measure_syndrome(state, rng)
    fixed_qubit = None
    if correct:
        state, fixed_qubit = recover(state, syndrome, fix_phase=fix_phase)

    # fidelity ignores the leftover global phase i, as it should
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
    print(f"{'state':>6} {'error':>5} {'syndrome':>9} {'fixed':>9} {'fidelity':>9}")
    for state_name, (a, b) in TEST_STATES.items():
        for error_name in ERRORS:
            r = run(a, b, error_name)
            q = r["fixed_qubit"]
            fixed = "-" if q is None else f"X,Z q{q}"
            print(f"{state_name:>6} {error_name:>5} {str(r['syndrome']):>9} "
                  f"{fixed:>9} {r['fidelity_decoded']:>9.6f}")
