"""
Magic State Verification, Level 1: reconstruct a single-qubit state.

The big idea
------------
Any single-qubit density matrix (pure OR mixed) can be written as

    rho = 0.5 * (I + rx*X + ry*Y + rz*Z)

where r = (rx, ry, rz) is the "Bloch vector", with |r| <= 1.
    |r| = 1  -> pure state (on the surface of the Bloch sphere)
    |r| < 1  -> mixed state (inside the sphere), |r| = 0 is maximally mixed

Each component is just the average value of that Pauli measurement:
    r_P = Tr(rho P) = <P>      for P in {X, Y, Z}

Measuring P gives +1 with probability (1 + r_P)/2 and -1 otherwise.
So if we measure P on N fresh copies and get N_plus (+1)s and N_minus (-1)s,

    r_P_hat = (N_plus - N_minus) / N

is an unbiased estimate of r_P. Do this for X, Y and Z, rebuild rho.

The file is split in two halves on purpose:
  1. SIMULATOR  - knows the true state, produces +1/-1 shots.
  2. ESTIMATOR  - sees ONLY the shot outcomes, never the true state.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Pauli matrices
# ---------------------------------------------------------------------------
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
PAULIS = {"X": X, "Y": Y, "Z": Z}
AXES = ("X", "Y", "Z")

# Target magic state |T> = cos(pi/8)|0> + sin(pi/8)|1>, Bloch vector (1/sqrt2, 0, 1/sqrt2)
T_BLOCH = np.array([np.sin(np.pi / 4), 0.0, np.cos(np.pi / 4)])


# ---------------------------------------------------------------------------
# Converting between descriptions of a state
# ---------------------------------------------------------------------------
def bloch_to_rho(r):
    """rho = 0.5 * (I + rx X + ry Y + rz Z)."""
    rx, ry, rz = r
    return 0.5 * (I2 + rx * X + ry * Y + rz * Z)


def rho_to_bloch(rho):
    """r_P = Tr(rho P). (Used only for checking results, never by the estimator.)"""
    return np.array([np.real(np.trace(rho @ PAULIS[p])) for p in AXES])


def bloch_from_pure(a, b):
    """Bloch vector of the pure state a|0> + b|1> (normalised automatically)."""
    psi = np.array([a, b], dtype=complex)
    psi = psi / np.linalg.norm(psi)
    return rho_to_bloch(np.outer(psi, psi.conj()))


def check_valid_bloch(r):
    r = np.asarray(r, dtype=float)
    if r.shape != (3,):
        raise ValueError("Bloch vector must have 3 components")
    if np.linalg.norm(r) > 1 + 1e-9:
        raise ValueError(f"|r| = {np.linalg.norm(r):.4f} > 1 is not a physical state")
    return r


# ---------------------------------------------------------------------------
# 1. SIMULATOR (knows the truth)
# ---------------------------------------------------------------------------
def simulate_shots(r_true, pauli, n_shots, rng):
    """Measure Pauli `pauli` on n_shots fresh copies of the state.

    Each shot is +1 with probability (1 + r_P)/2, else -1.
    This is exactly the brief's Pr(+1|P) = (1 + Tr(rho P))/2.
    Returns an array of n_shots values, each +1 or -1.
    """
    r_true = check_valid_bloch(r_true)
    r_p = r_true[AXES.index(pauli)]
    p_plus = (1 + r_p) / 2
    return np.where(rng.random(n_shots) < p_plus, 1, -1)


def collect_counts(r_true, n_shots, rng):
    """Run n_shots of X, n_shots of Y and n_shots of Z (3*n_shots total).

    Returns {"X": (N_plus, N_minus), "Y": ..., "Z": ...}.
    This is the ONLY thing handed to the estimator.
    """
    counts = {}
    for p in AXES:
        shots = simulate_shots(r_true, p, n_shots, rng)
        n_plus = int(np.sum(shots == 1))
        counts[p] = (n_plus, n_shots - n_plus)
    return counts


# ---------------------------------------------------------------------------
# 2. ESTIMATOR (sees only counts)
# ---------------------------------------------------------------------------
def estimate_bloch(counts):
    """Raw estimate r_P_hat = (N_plus - N_minus) / N for each axis.

    Because of shot noise this can land OUTSIDE the Bloch sphere (|r_hat| > 1),
    which would be an unphysical "density matrix" with a negative eigenvalue.
    """
    r_hat = []
    for p in AXES:
        n_plus, n_minus = counts[p]
        n = n_plus + n_minus
        r_hat.append((n_plus - n_minus) / n)
    return np.array(r_hat)


def make_physical(r_hat):
    """If |r_hat| > 1, shrink it back onto the sphere surface (length 1).

    Why this fixes things: the eigenvalues of 0.5*(I + r.sigma) are
    (1 +/- |r|)/2, so the matrix is positive semidefinite exactly when |r| <= 1.
    Rescaling to length 1 keeps the direction and gives the closest pure state.
    Returns (r_physical, was_rescaled).
    """
    length = np.linalg.norm(r_hat)
    if length > 1:
        return r_hat / length, True
    return r_hat, False


def reconstruct(counts):
    """Full Level 1 pipeline: counts -> physical density matrix rho_hat.

    Returns (rho_hat, r_hat_physical, was_rescaled).
    """
    r_raw = estimate_bloch(counts)
    r_phys, rescaled = make_physical(r_raw)
    return bloch_to_rho(r_phys), r_phys, rescaled


def tomography(r_true, n_shots, rng):
    """Convenience wrapper: simulate the experiment, then reconstruct.

    Note the hand-off: r_true goes into collect_counts (the simulator) only.
    reconstruct() never sees it.
    """
    counts = collect_counts(r_true, n_shots, rng)
    return reconstruct(counts)


# ---------------------------------------------------------------------------
# Error measures (for evaluating, used AFTER estimation)
# ---------------------------------------------------------------------------
def bloch_distance(r1, r2):
    return float(np.linalg.norm(np.asarray(r1) - np.asarray(r2)))


def trace_distance(rho1, rho2):
    """0.5 * sum |eigenvalues of (rho1 - rho2)|. For qubits this equals half the
    Bloch distance, so the two measures always agree up to a factor of 2."""
    eig = np.linalg.eigvalsh(rho1 - rho2)
    return float(0.5 * np.sum(np.abs(eig)))


def magic_fidelity(r):
    """F_T = <T|rho|T> = 0.5 * (1 + (rx + rz)/sqrt2) (from the brief)."""
    return 0.5 * (1 + (r[0] + r[2]) / np.sqrt(2))


def is_physical(rho, tol=1e-10):
    hermitian = np.allclose(rho, rho.conj().T, atol=tol)
    trace_one = abs(np.trace(rho) - 1) < tol
    psd = np.min(np.linalg.eigvalsh(rho)) >= -tol
    return hermitian and trace_one and psd


# ---------------------------------------------------------------------------
# Optional cross-check: measuring X and Y "the hardware way"
# ---------------------------------------------------------------------------
# Real devices only measure in the Z basis (|0> vs |1>). To measure X you first
# apply H; to measure Y you apply S-dagger then H. The state evolves as
# rho' = U rho U^dagger, and P(+1) is then just rho'[0,0] (chance of reading 0).
# This should give exactly (1 + r_P)/2, which is what simulate_shots uses.
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
S_DAG = np.array([[1, 0], [0, -1j]], dtype=complex)
BASIS_CHANGE = {"X": H, "Y": H @ S_DAG, "Z": I2}  # H @ S_DAG means "S-dagger first, then H"


def p_plus_via_rotation(rho, pauli):
    U = BASIS_CHANGE[pauli]
    rho_rot = U @ rho @ U.conj().T
    return float(np.real(rho_rot[0, 0]))


def simulate_shots_via_rotation(rho, pauli, n_shots, rng):
    p_plus = p_plus_via_rotation(rho, pauli)
    return np.where(rng.random(n_shots) < p_plus, 1, -1)
