"""
Magic State Verification, Level 2: estimate the fidelity F_T with |T>.

The big idea
------------
The fidelity of a state rho with the magic state |T> is

    F_T = <T| rho |T> = 0.5 * (1 + (r_x + r_z) / sqrt(2))

(|T> has Bloch vector (1/sqrt2, 0, 1/sqrt2), and for qubits
<psi|rho|psi> = 0.5 * (1 + r_psi . r)).

F_T does NOT depend on r_y. So measuring Y is wasted shots. Instead we
spend the whole budget on X and Z (half each), estimate

    r_x_hat = (N+ - N-)/N_x,   r_z_hat = (N+ - N-)/N_z,

and plug them in. That is the whole estimator.

Error bar
---------
Each r_P_hat is an average of N independent +-1 outcomes, so its
standard error is  SE(r_P) = sqrt((1 - r_P^2) / N).
F_T is a linear function of r_x and r_z with slope 1/(2 sqrt2) on each, and
the X and Z shots are independent, so

    SE(F) = (1 / (2 sqrt2)) * sqrt(SE_x^2 + SE_z^2).

We report F_hat +- 1.96 * SE(F) as an approximate 95% confidence interval.
(We plug in r_hat for the unknown r, the usual "plug-in" error bar.)

As in Level 1, the simulator (which knows the truth) and the estimator
(which sees only counts) are kept separate. We reuse the Level 1 simulator.
"""

import numpy as np

from tomography import simulate_shots, check_valid_bloch, magic_fidelity

SQRT2 = np.sqrt(2)
Z95 = 1.96  # two-sided 95% normal quantile


# ---------------------------------------------------------------------------
# 1. SIMULATOR (knows the truth) - reuses Level 1's simulate_shots
# ---------------------------------------------------------------------------
def split_budget(total_shots):
    """Split a total shot budget between X and Z. Odd budgets give X the extra shot."""
    if total_shots < 2:
        raise ValueError("need at least 2 shots (one for X and one for Z)")
    n_x = (total_shots + 1) // 2
    return n_x, total_shots - n_x


def collect_xz_counts(r_true, total_shots, rng):
    """Spend `total_shots` measuring X and Z only (no Y).

    Returns {"X": (N_plus, N_minus), "Z": (N_plus, N_minus)}.
    This is the ONLY thing handed to the estimator.
    """
    r_true = check_valid_bloch(r_true)
    counts = {}
    for pauli, n in zip(("X", "Z"), split_budget(total_shots)):
        shots = simulate_shots(r_true, pauli, n, rng)
        n_plus = int(np.sum(shots == 1))
        counts[pauli] = (n_plus, n - n_plus)
    return counts


# ---------------------------------------------------------------------------
# 2. ESTIMATOR (sees only counts)
# ---------------------------------------------------------------------------
def _axis_estimate(n_plus, n_minus):
    """r_hat = (N+ - N-)/N and its standard error sqrt((1 - r_hat^2)/N)."""
    n = n_plus + n_minus
    if n == 0:
        raise ValueError("an axis has zero shots")
    r = (n_plus - n_minus) / n
    se = np.sqrt(max(0.0, 1 - r * r) / n)
    return r, se


def estimate_fidelity(counts, z=Z95):
    """Counts on X and Z -> fidelity estimate with error bar.

    Returns a dict with:
        F_hat   : estimate, clipped to [0, 1]
        F_raw   : the same number before clipping
        se      : standard error of F
        ci      : (low, high) = F_hat +- z*se, also clipped to [0, 1]
        r_x, r_z, se_x, se_z, shots
    """
    r_x, se_x = _axis_estimate(*counts["X"])
    r_z, se_z = _axis_estimate(*counts["Z"])
    f_raw = 0.5 * (1 + (r_x + r_z) / SQRT2)
    f_hat = float(np.clip(f_raw, 0.0, 1.0))
    se = float(np.sqrt(se_x ** 2 + se_z ** 2) / (2 * SQRT2))
    ci = (float(np.clip(f_hat - z * se, 0, 1)), float(np.clip(f_hat + z * se, 0, 1)))
    return {
        "F_hat": f_hat, "F_raw": float(f_raw), "se": se, "ci": ci,
        "r_x": r_x, "r_z": r_z, "se_x": se_x, "se_z": se_z,
        "shots": sum(counts["X"]) + sum(counts["Z"]),
    }


def fidelity_experiment(r_true, total_shots, rng):
    """Convenience wrapper: simulate, then estimate.
    r_true goes only into the simulator; estimate_fidelity never sees it."""
    return estimate_fidelity(collect_xz_counts(r_true, total_shots, rng))


def true_fidelity(r_true):
    """The answer we compare against (used only for evaluation)."""
    return float(magic_fidelity(np.asarray(r_true, dtype=float)))
