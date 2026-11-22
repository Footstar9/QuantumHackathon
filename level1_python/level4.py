"""
Level 4 "Mystery Mines": DETECT the type of an unknown single-qubit error
(none, X, Y or Z) on a 4-qubit code, without measuring the secret.

Qubit layout (7 qubits in total)
--------------------------------
    q0, q1, q2, q3 : DATA qubits. The secret a|0> + b|1> starts on q2.
    q4             : helper for the PHASE check (are all four "in step"?)
    q5             : helper for the BIT check on q0 vs q1
    q6             : helper for the BIT check on q2 vs q3

Encoded state (strings are q0 q1 q2 q3)
---------------------------------------
    a (|0000> + |1111>)/sqrt2  +  b (|0011> + |1100>)/sqrt2

Notice three facts about every configuration in it:
    * q0 always equals q1          -> an X on q0 or q1 breaks this
    * q2 always equals q3          -> an X on q2 or q3 breaks this
    * flipping ALL FOUR bits maps the state onto itself
      (0000 <-> 1111, 0011 <-> 1100) -> a Z anywhere spoils this symmetry

The three checks
----------------
    BIT checks   (like Level 1):  q5 = q0 XOR q1,  q6 = q2 XOR q3
    PHASE check  (like Level 2):  H on q4, CNOT q4 -> q0, q1, q2, q3, H on q4.
                 It asks "is the state unchanged when all four bits flip?"
                 using a helper in superposition. Answer 1 = no = phase flip.

    bit alarm   = q5 OR q6     (X or Y happened)
    phase alarm = q4           (Z or Y happened)

    (bit alarm, phase alarm) -> error type
        (0, 0) -> I     (1, 0) -> X     (0, 1) -> Z     (1, 1) -> Y

Like Level 4 says, this finds the TYPE but not always the LOCATION:
an X on q0 and an X on q1 ring exactly the same alarm.
"""

import numpy as np

import level2  # only for its general apply_error("Y1") helper
import simulator as sim

DATA = [0, 1, 2, 3]
SECRET_QUBIT = 2
PHASE_HELPER = 4
BIT_HELPER_01 = 5
BIT_HELPER_23 = 6
NUM_QUBITS = 7

TEST_STATES = {
    "|0>":  (1, 0),
    "|1>":  (0, 1),
    "|+>":  (1 / np.sqrt(2), 1 / np.sqrt(2)),
    "|->":  (1 / np.sqrt(2), -1 / np.sqrt(2)),
    "|+i>": (1 / np.sqrt(2), 1j / np.sqrt(2)),
    "|-i>": (1 / np.sqrt(2), -1j / np.sqrt(2)),
}

# Every permitted error: no error, or X/Y/Z on any one of the four data qubits
ERRORS = ["I"] + [f"{p}{q}" for p in "XYZ" for q in DATA]

# (bit alarm, phase alarm) -> error type
DECODE_TABLE = {(0, 0): "I", (1, 0): "X", (0, 1): "Z", (1, 1): "Y"}

apply_error = level2.apply_error   # handles names like "I", "X0", "Y3", "Z2"


def prepare(alpha, beta):
    """Secret on q2, every other qubit at |0>."""
    psi = sim.single_qubit_state(alpha, beta)
    zero = sim.zero_state(1)
    return sim.combine(zero, zero, psi, zero, zero, zero, zero)


def encode(state):
    """
    1. H on q1                      : q1 becomes 50/50 "0 and 1"
    2. CNOT q2 -> q3                : copy the secret's bit value onto q3
    3. CNOT q1 -> q0, q1 -> q2, q1 -> q3 : when q1 is 1, flip the other three
    Result: a(|0000>+|1111>)/sqrt2 + b(|0011>+|1100>)/sqrt2
    """
    state = sim.apply_gate(state, sim.H, 1)
    state = sim.apply_cnot(state, control=2, target=3)
    state = sim.apply_cnot(state, control=1, target=0)
    state = sim.apply_cnot(state, control=1, target=2)
    state = sim.apply_cnot(state, control=1, target=3)
    return state


def decode(state):
    """Undo encode() (gates in reverse order). Only meaningful when there is no error."""
    state = sim.apply_cnot(state, control=1, target=3)
    state = sim.apply_cnot(state, control=1, target=2)
    state = sim.apply_cnot(state, control=1, target=0)
    state = sim.apply_cnot(state, control=2, target=3)
    state = sim.apply_gate(state, sim.H, 1)
    return state


def logical_state(alpha, beta):
    """The ideal encoded 4-qubit state, used to check our work."""
    psi = sim.single_qubit_state(alpha, beta)
    ideal = np.zeros(16, dtype=complex)
    ideal[0b0000] = ideal[0b1111] = psi[0] / np.sqrt(2)
    ideal[0b0011] = ideal[0b1100] = psi[1] / np.sqrt(2)
    return ideal


def phase_check(state):
    """
    Phase check onto q4: H, then CNOT from the helper onto each data qubit, then H.

    In plain words: the helper is put into "both 0 and 1". In its 1 part, all
    four data bits get flipped. If flipping all four leaves the data unchanged
    (no phase error), the two parts recombine and the final H gives 0. If a Z
    put a minus sign in the way, they recombine to 1.
    """
    state = sim.apply_gate(state, sim.H, PHASE_HELPER)
    for q in DATA:
        state = sim.apply_cnot(state, control=PHASE_HELPER, target=q)
    state = sim.apply_gate(state, sim.H, PHASE_HELPER)
    return state


def bit_checks(state):
    """Parities onto q5 (q0 XOR q1) and q6 (q2 XOR q3), exactly like Level 1."""
    state = sim.apply_cnot(state, control=0, target=BIT_HELPER_01)
    state = sim.apply_cnot(state, control=1, target=BIT_HELPER_01)
    state = sim.apply_cnot(state, control=2, target=BIT_HELPER_23)
    state = sim.apply_cnot(state, control=3, target=BIT_HELPER_23)
    return state


def measure_helpers(state, rng=None):
    """Measure q4, q5, q6. Returns ({'phase', 'bit01', 'bit23'}, state_after)."""
    phase, state = sim.measure(state, PHASE_HELPER, rng)
    b01, state = sim.measure(state, BIT_HELPER_01, rng)
    b23, state = sim.measure(state, BIT_HELPER_23, rng)
    return {"phase": phase, "bit01": b01, "bit23": b23}, state


def classify(readings):
    """Turn the three helper readings into an error type using DECODE_TABLE."""
    bit_alarm = readings["bit01"] | readings["bit23"]
    phase_alarm = readings["phase"]
    return DECODE_TABLE[(bit_alarm, phase_alarm)]


def run(alpha, beta, error_name, rng=None):
    """
    Run the whole Level 4 circuit once.

    Returns the readings, the detected type, and `fidelity_with_error`: how
    close the data qubits are, AFTER our measurements, to (error applied to
    the ideal codeword). 1.0 means our checks did not disturb the secret at all.
    """
    state = prepare(alpha, beta)
    state = encode(state)
    state = apply_error(state, error_name)
    state = phase_check(state)
    state = bit_checks(state)
    readings, state = measure_helpers(state, rng)

    # What the data "should" be: the error applied to the clean codeword
    expected = level2.apply_error(logical_state(alpha, beta), error_name)
    fidelity_with_error = sim.fidelity(expected, state, qubits=DATA)

    return {
        "readings": readings,
        "detected": classify(readings),
        "fidelity_with_error": fidelity_with_error,
        "final_state": state,
    }


if __name__ == "__main__":
    print("Readings are (phase q4, bit q5, bit q6). Secret state |+i>; every state gives the same readings.\n")
    print(f"{'error':>5} {'readings':>10} {'detected':>9} {'correct?':>9} {'data untouched':>15}")
    a, b = TEST_STATES["|+i>"]
    for error_name in ERRORS:
        r = run(a, b, error_name)
        rd = r["readings"]
        ok = "yes" if r["detected"] == error_name[0] else "NO"
        print(f"{error_name:>5} {str((rd['phase'], rd['bit01'], rd['bit23'])):>10} "
              f"{r['detected']:>9} {ok:>9} {r['fidelity_with_error']:>15.6f}")
