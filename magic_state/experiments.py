"""
Level 1 experiments: reconstruct several states and show how the error
shrinks as the number of shots N grows.

Run from the repo root:   python magic_state/experiments.py
Outputs:  a printed table + magic_state/results/error_vs_shots.png
"""

import os
import numpy as np
import matplotlib

matplotlib.use("Agg")  # save to file, no window needed
import matplotlib.pyplot as plt

from tomography import (
    T_BLOCH, bloch_from_pure, bloch_to_rho, tomography, collect_counts,
    bloch_distance, trace_distance, magic_fidelity, is_physical,
    p_plus_via_rotation, simulate_shots, simulate_shots_via_rotation,
)

SEED = 2026
SHOT_LIST = [10, 100, 1000, 10000]  # shots PER AXIS (total = 3 x this)
TRIALS = 200                        # repeats per (state, N) to average out luck

STATES = {
    "|0>":             bloch_from_pure(1, 0),
    "|+>":             bloch_from_pure(1, 1),
    "|+i>":            bloch_from_pure(1, 1j),
    "|T> (magic)":     T_BLOCH,
    "max mixed":       np.array([0.0, 0.0, 0.0]),
    "mixed (.5,0,.5)": np.array([0.5, 0.0, 0.5]),
    "near surface":    np.array([0.6, 0.55, 0.57]),  # |r| ~ 0.995
}

HERE = os.path.dirname(os.path.abspath(__file__))


def single_demo(rng):
    """One reconstruction of the magic state, printed in full."""
    n = 1000
    rho_hat, r_hat, rescaled = tomography(T_BLOCH, n, rng)
    print(f"\n=== Single demo: |T> with N = {n} shots per axis ===")
    print("true Bloch vector :", np.round(T_BLOCH, 4))
    print("estimated         :", np.round(r_hat, 4), "(rescaled)" if rescaled else "")
    print("estimated rho_hat :\n", np.round(rho_hat, 4))
    print("eigenvalues       :", np.round(np.linalg.eigvalsh(rho_hat), 4))
    print("physical?         :", is_physical(rho_hat))
    print(f"trace distance    : {trace_distance(rho_hat, bloch_to_rho(T_BLOCH)):.4f}")
    print(f"F_T true / est    : {magic_fidelity(T_BLOCH):.4f} / {magic_fidelity(r_hat):.4f}")


def cross_check(rng):
    """Show the 'rotate then measure Z' method gives the same probabilities."""
    print("\n=== Cross-check: direct formula vs. rotate-then-measure-Z ===")
    print(f"{'state':<16}{'axis':<6}{'(1+r_P)/2':>11}{'rho_rot[0,0]':>14}{'shots agree?':>14}")
    for name, r in STATES.items():
        rho = bloch_to_rho(r)
        for i, p in enumerate("XYZ"):
            direct = (1 + r[i]) / 2
            rotated = p_plus_via_rotation(rho, p)
            a = simulate_shots(r, p, 5000, np.random.default_rng(1)).mean()
            b = simulate_shots_via_rotation(rho, p, 5000, np.random.default_rng(1)).mean()
            print(f"{name:<16}{p:<6}{direct:>11.4f}{rotated:>14.4f}{str(np.isclose(a, b)):>14}")


def sweep(rng):
    """Average error vs N for every state, over TRIALS repeats."""
    results = {}
    print(f"\n=== Mean error over {TRIALS} trials (N = shots per axis) ===")
    print(f"{'state':<16}{'N':>7}{'Bloch dist':>12}{'trace dist':>12}{'rescaled %':>12}{'all physical':>14}")
    for name, r_true in STATES.items():
        rho_true = bloch_to_rho(r_true)
        rows = []
        for n in SHOT_LIST:
            bd, td, resc, phys = [], [], 0, True
            for _ in range(TRIALS):
                rho_hat, r_hat, rescaled = tomography(r_true, n, rng)
                bd.append(bloch_distance(r_hat, r_true))
                td.append(trace_distance(rho_hat, rho_true))
                resc += rescaled
                phys &= is_physical(rho_hat)
            rows.append((n, np.mean(bd), np.mean(td)))
            print(f"{name:<16}{n:>7}{np.mean(bd):>12.4f}{np.mean(td):>12.4f}"
                  f"{100 * resc / TRIALS:>11.0f}%{str(phys):>14}")
        results[name] = rows
    return results


def plot(results):
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    for name, rows in results.items():
        ns = [r[0] for r in rows]
        ax.loglog(ns, [r[2] for r in rows], "o-", label=name, alpha=0.85)
    ns = np.array(SHOT_LIST, dtype=float)
    ax.loglog(ns, 0.5 / np.sqrt(ns), "k--", label=r"$\propto 1/\sqrt{N}$")
    ax.set_xlabel("shots per Pauli axis, N")
    ax.set_ylabel(f"mean trace distance (over {TRIALS} trials)")
    ax.set_title("Level 1 tomography: error falls like 1/sqrt(N)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = os.path.join(HERE, "results", "error_vs_shots.png")
    fig.savefig(path, dpi=150)
    print(f"\nPlot saved to {path}")


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    single_demo(rng)
    cross_check(rng)
    plot(sweep(rng))
