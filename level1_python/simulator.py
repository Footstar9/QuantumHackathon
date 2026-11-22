"""
A tiny quantum computer simulator, written from scratch with numpy.

Big idea
--------
A classical computer with n bits is in ONE of 2**n configurations
(for 3 bits: 000, 001, ..., 111).

A quantum computer with n qubits is described by a list of 2**n numbers,
one "amplitude" per configuration. That list is called the STATE VECTOR.

    state[k] = amplitude of the configuration whose bits spell the number k

Example with 3 qubits: the state  (|000> + |111>) / sqrt(2)  is

    index:   0     1     2     3     4     5     6     7
    bits:   000   001   010   011   100   101   110   111
    amp:   0.707   0     0     0     0     0     0   0.707

Rules of the game:
  * Amplitudes can be complex numbers (that is where "phase" lives).
  * If you MEASURE, you see configuration k with probability |state[k]|**2.
    So the squared sizes must add up to 1.
  * GATES are the operations we are allowed to do. Each gate is a matrix
    that multiplies the state vector.

Qubit numbering convention used everywhere in this project
------------------------------------------------------------
Qubit 0 is the LEFTMOST character of the ket. So in |q0 q1 q2>, the
string "100" means qubit 0 is 1 and qubits 1 and 2 are 0.
This matches how the challenge PDF writes states like a|000> + b|111>.

(Heads-up for later: Qiskit numbers qubits the other way round in its
printouts, with qubit 0 on the RIGHT. Only the printing differs; the
circuit itself is the same.)
"""

import numpy as np


# ---------------------------------------------------------------------------
# 1. Single-qubit gates (2x2 matrices)
# ---------------------------------------------------------------------------
# Each column says "what does |0> become" and "what does |1> become".

I = np.array([[1, 0],
              [0, 1]], dtype=complex)        # Identity: do nothing

X = np.array([[0, 1],
              [1, 0]], dtype=complex)        # Bit flip: |0> <-> |1>  (quantum NOT)

Z = np.array([[1, 0],
              [0, -1]], dtype=complex)       # Phase flip: |1> -> -|1>, |0> unchanged

Y = np.array([[0, -1j],
              [1j, 0]], dtype=complex)       # Both at once (Y = i X Z)

H = np.array([[1, 1],
              [1, -1]], dtype=complex) / np.sqrt(2)   # Hadamard: |0> -> |+>, |1> -> |->

S = np.array([[1, 0],
              [0, 1j]], dtype=complex)       # Quarter phase: |1> -> i|1>


# ---------------------------------------------------------------------------
# 2. Making states
# ---------------------------------------------------------------------------

def zero_state(num_qubits):
    """All qubits start in |0>: amplitude 1 on configuration 00...0."""
    state = np.zeros(2 ** num_qubits, dtype=complex)
    state[0] = 1.0
    return state


def single_qubit_state(alpha, beta):
    """The 1-qubit state alpha|0> + beta|1>, normalised so probabilities add to 1."""
    state = np.array([alpha, beta], dtype=complex)
    return state / np.linalg.norm(state)


def combine(*states):
    """
    Put independent registers side by side (the "tensor product").

    combine(a, b) describes "register a, and next to it register b".
    The first argument becomes the leftmost qubits.
    """
    result = np.array([1.0], dtype=complex)
    for s in states:
        result = np.kron(result, s)
    return result


# ---------------------------------------------------------------------------
# 3. Helpers for reading bits out of an index
# ---------------------------------------------------------------------------

def get_bit(index, qubit, num_qubits):
    """Value (0 or 1) of `qubit` inside configuration number `index`."""
    # qubit 0 is the leftmost bit, i.e. the most significant one.
    shift = num_qubits - 1 - qubit
    return (index >> shift) & 1


def flip_bit(index, qubit, num_qubits):
    """Configuration number you get after flipping `qubit` in `index`."""
    shift = num_qubits - 1 - qubit
    return index ^ (1 << shift)


def bitstring(index, num_qubits):
    """Configuration number -> string of bits, e.g. 5 -> '101' for 3 qubits."""
    return format(index, f"0{num_qubits}b")


# ---------------------------------------------------------------------------
# 4. Applying gates
# ---------------------------------------------------------------------------

def apply_gate(state, gate, qubit):
    """
    Apply a 2x2 `gate` to one `qubit`, leaving every other qubit alone.

    How: build the big matrix  I (x) I (x) gate (x) I ...  where `gate` sits in
    position `qubit`, then multiply. Simple and easy to check; fast enough
    for the handful of qubits we use here.
    """
    num_qubits = int(np.log2(len(state)))
    big_matrix = np.array([[1.0]], dtype=complex)
    for q in range(num_qubits):
        piece = gate if q == qubit else I
        big_matrix = np.kron(big_matrix, piece)
    return big_matrix @ state


def apply_cnot(state, control, target):
    """
    Controlled-NOT: flip `target` only in configurations where `control` is 1.

    Classical picture: target = target XOR control.
    Quantum bonus: it acts on every configuration of a superposition at once,
    which is exactly how we copy "the bit value" onto extra qubits without
    learning what it is.
    """
    num_qubits = int(np.log2(len(state)))
    new_state = np.zeros_like(state)
    for index, amplitude in enumerate(state):
        if get_bit(index, control, num_qubits) == 1:
            new_index = flip_bit(index, target, num_qubits)
        else:
            new_index = index
        new_state[new_index] += amplitude
    return new_state


# ---------------------------------------------------------------------------
# 5. Measurement
# ---------------------------------------------------------------------------

def probability_of_one(state, qubit):
    """Chance that measuring `qubit` gives 1 (sum of |amp|^2 where that bit is 1)."""
    num_qubits = int(np.log2(len(state)))
    return sum(abs(amp) ** 2
               for index, amp in enumerate(state)
               if get_bit(index, qubit, num_qubits) == 1)


def measure(state, qubit, rng=None):
    """
    Measure one qubit. Returns (outcome, state_after).

    1. Work out the probability of seeing 1.
    2. Roll a (weighted) die to pick the outcome.
    3. "Collapse": throw away every configuration that disagrees with the
       outcome, then rescale what is left so probabilities add to 1 again.

    The OTHER qubits are not measured. Any superposition among them that is
    consistent with the outcome survives. Error correction relies on this.
    """
    if rng is None:
        rng = np.random.default_rng()
    num_qubits = int(np.log2(len(state)))

    p1 = probability_of_one(state, qubit)
    outcome = 1 if rng.random() < p1 else 0

    new_state = state.copy()
    for index in range(len(state)):
        if get_bit(index, qubit, num_qubits) != outcome:
            new_state[index] = 0
    new_state = new_state / np.linalg.norm(new_state)
    return outcome, new_state


# ---------------------------------------------------------------------------
# 6. Comparing states
# ---------------------------------------------------------------------------

def reduced_density_matrix(state, keep_qubits):
    """
    Describe only the qubits in `keep_qubits`, ignoring ("tracing out") the rest.

    You can think of it as: "if someone hid the other qubits from me, what
    could I still say about these ones?" The answer is a small matrix rho.
    """
    num_qubits = int(np.log2(len(state)))
    tensor = state.reshape([2] * num_qubits)
    drop = [q for q in range(num_qubits) if q not in keep_qubits]
    # Bring kept qubits to the front, dropped ones to the back, then flatten.
    tensor = np.transpose(tensor, list(keep_qubits) + drop)
    matrix = tensor.reshape(2 ** len(keep_qubits), 2 ** len(drop))
    return matrix @ matrix.conj().T


def fidelity(target_state, state, qubits=None):
    """
    How close is `state` to `target_state`?  1.0 = identical, 0.0 = opposite.

    If `qubits` is given, only those qubits of `state` are compared with the
    (smaller) `target_state`; the rest are ignored.
    Global phase (multiplying everything by the same e^{i theta}) is
    physically invisible and does not lower the fidelity.
    """
    if qubits is None:
        return abs(np.vdot(target_state, state)) ** 2
    rho = reduced_density_matrix(state, qubits)
    return float(np.real(np.vdot(target_state, rho @ target_state)))


# ---------------------------------------------------------------------------
# 7. Pretty printing
# ---------------------------------------------------------------------------

def _format_amplitude(amp):
    re, im = np.real(amp), np.imag(amp)
    if abs(im) < 1e-9:
        return f"{re:+.3f}"
    if abs(re) < 1e-9:
        return f"{im:+.3f}i"
    return f"({re:+.3f}{im:+.3f}i)"


def show(state, groups=None):
    """
    Return a readable string listing only the configurations that are present.

    `groups` lets you put spaces between registers, e.g. groups=[3, 2] prints
    |010 11> so data qubits and helper qubits are easy to tell apart.
    """
    num_qubits = int(np.log2(len(state)))
    lines = []
    for index, amp in enumerate(state):
        if abs(amp) < 1e-9:
            continue
        bits = bitstring(index, num_qubits)
        if groups:
            parts, start = [], 0
            for size in groups:
                parts.append(bits[start:start + size])
                start += size
            bits = " ".join(parts)
        lines.append(f"  {_format_amplitude(amp)} |{bits}>   (probability {abs(amp) ** 2:.3f})")
    return "\n".join(lines)
