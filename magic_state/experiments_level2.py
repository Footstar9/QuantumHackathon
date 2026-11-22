"""
Level 2 experiments: estimate F_T = <T|rho|T> from X and Z shots only.

Run from the repo root:   python magic_state/experiments_level2.py
Outputs:  printed tables + magic_state/results/fidelity_level2.png
"""

import os
import numpy as np
import matplotlib

matplotlib.use("Agg")  # save to file, no window needed
import matplotlib.pyplot as plt

from tomography import T_BLOCH, bloch_from_pure, tomography, magic_fidelity
from fidelity import (
    estimate_fidelity, fidelity_experiment, true_fidelity,
)

SEED = 2026
BUDGETS = [30, 300, 3000, 30000]   # TOTAL shots (divisible by 2 and by 3, so both methods split evenly)
TRIALS = 1000                      # repeats per (state, budget)

STATES = {
    "|T> (magic)":   T_BLOCH,
    "noisy T (0.9)": 0.9 * T_BLOCH,           # T with 10% depolarising, F = 0.95
    "noisy T (0.5)": 0.5 * T_BLOCH,           # F = 0.75
    "|0>":           bloch_from_pure(1, 0),
    "|+>":           bloch_from_pure(1, 1),
    "|+i>":          bloch_from_pure(1, 1j),  # F = 0.5 although it is pure
    "|1>":           bloch_from_pure(0, 1),
    "max mixed":     np.zeros(3),
    "anti-T":        -T_BLOCH,                # orthogonal to |T>, F = 0
}

HERE = os.path.dirname(os.path.abspath(__file__))


def brief_example():
    """The worked example from the brief: 200 shots, X 84/16, Z 85/15."""
    est = estimate_fidelity({"X": (84, 16), "Z": (85, 15)})
    print("=== Brief's example (200 shots: X 84/16, Z 85/15) ===")
    print(f"r_x = {est['r_x']:.2f}, r_z = {est['r_z']:.2f}")
    print(f"F_hat = {est['F_hat']:.4f} +- {est['se']:.4f}  "
          f"95% CI [{est['ci'][0]:.3f}, {est['ci'][1]:.3f}]   (brief says ~0.988)")


def one_shot_table(rng, budget=300):
    """One estimate per state at a single budget, next to the truth."""
    print(f"\n=== One run per state, {budget} total shots ===")
    print(f"{'state':<15}{'F true':>8}{'F hat':>8}{'+- SE':>8}{'95% CI':>18}{'covers?':>9}")
    rows = []
    for name, r in STATES.items():
        f = true_fidelity(r)
        est = fidelity_experiment(r, budget, rng)
        lo, hi = est["ci"]
        print(f"{name:<15}{f:>8.3f}{est['F_hat']:>8.3f}{est['se']:>8.3f}"
              f"{f'[{lo:.3f}, {hi:.3f}]':>18}{str(lo <= f <= hi):>9}")
        rows.append((name, f, est["F_hat"], est["ci"]))
    return rows


def tomography_fidelity(r, budget, rng):
    """Level 1 route for comparison: budget/3 shots on each of X, Y, Z,
    rebuild a physical rho, then read off F_T."""
    _, r_hat, _ = tomography(r, budget // 3, rng)
    return float(magic_fidelity(r_hat))


def sweep(rng):
    """Repeated trials: RMSE, mean stated SE, CI coverage, and the
    tomography comparison, for every state and budget."""
    print(f"\n=== {TRIALS} trials per cell (budget = TOTAL shots) ===")
    print(f"{'state':<15}{'budget':>7}{'RMSE XZ':>9}{'mean SE':>9}{'coverage':>10}"
          f"{'RMSE tomo':>11}{'tomo/XZ':>9}")
    results = {}
    for name, r in STATES.items():
        f = true_fidelity(r)
        rows = []
        for b in BUDGETS:
            err, ses, cover, err_t = [], [], 0, []
            for _ in range(TRIALS):
                est = fidelity_experiment(r, b, rng)
                err.append(est["F_hat"] - f)
                ses.append(est["se"])
                cover += est["ci"][0] <= f <= est["ci"][1]
                err_t.append(tomography_fidelity(r, b, rng) - f)
            rmse = float(np.sqrt(np.mean(np.square(err))))
            rmse_t = float(np.sqrt(np.mean(np.square(err_t))))
            cov = cover / TRIALS
            rows.append((b, rmse, float(np.mean(ses)), cov, rmse_t))
            print(f"{name:<15}{b:>7}{rmse:>9.4f}{np.mean(ses):>9.4f}{100 * cov:>9.1f}%"
                  f"{rmse_t:>11.4f}{rmse_t / rmse if rmse else float('nan'):>9.2f}")
        results[name] = rows
    return results


def plot(one_shot, results):
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: estimated vs true, one run per state
    for name, f, fh, (lo, hi) in one_shot:
        a1.errorbar(f, fh, yerr=[[fh - lo], [hi - fh]], fmt="o", capsize=3, label=name)
    a1.plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
    a1.set_xlabel("true fidelity $F_T$")
    a1.set_ylabel(r"estimate $\hat F_T$ (with 95% CI)")
    a1.set_title("One run per state, 300 shots (X and Z only)")
    a1.set_xlim(-0.05, 1.05)
    a1.set_ylim(-0.05, 1.05)
    a1.grid(alpha=0.3)
    a1.legend(fontsize=7, loc="upper left")

    # Right: RMSE vs budget, XZ method vs full tomography, for |T> and a mixed state
    for name, style in [("|T> (magic)", "o"), ("max mixed", "s")]:
        rows = results[name]
        bs = [row[0] for row in rows]
        line, = a2.loglog(bs, [row[1] for row in rows], style + "-", label=f"{name}: X+Z only")
        a2.loglog(bs, [row[4] for row in rows], style + ":", color=line.get_color(),
                  label=f"{name}: full tomography")
    bs = np.array(BUDGETS, dtype=float)
    a2.loglog(bs, 0.5 / np.sqrt(bs), "k--", lw=1, label=r"$\propto 1/\sqrt{N}$")
    a2.set_xlabel("total shot budget")
    a2.set_ylabel(f"RMSE of $\\hat F_T$ over {TRIALS} trials")
    a2.set_title("Error vs budget: skipping Y helps")
    a2.grid(True, which="both", alpha=0.3)
    a2.legend(fontsize=7)

    fig.tight_layout()
    path = os.path.join(HERE, "results", "fidelity_level2.png")
    fig.savefig(path, dpi=150)
    print(f"\nPlot saved to {path}")


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    brief_example()
    one = one_shot_table(rng)
    plot(one, sweep(rng))
