"""
Plots comparing simulation and IQM hardware for Level 1.
Run through:  python iqm/run_level1_iqm.py plot

Makes two pictures in iqm/results/:
  success_sim_vs_hardware.png   how often the secret comes back right, per state and error
  syndromes_sim_vs_hardware.png which syndrome the helpers reported, per error
Any results file that does not exist yet (e.g. hardware.json) is just left out.
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SOURCES = [  # file, legend label, colour
    ("ideal.json", "Ideal simulator", "#2a78d6"),
    ("noisy_fake_garnet.json", "Noisy simulator (IQM Garnet model)", "#eb6834"),
    ("hardware.json", "IQM hardware", "#1baf7a"),
]
STATES = ["|0>", "|1>", "|+>", "|->", "|+i>", "|-i>"]
ERRORS = ["I", "X0", "X1", "X2"]
SYNDROMES = ["00", "10", "11", "01"]
SYNDROME_MEANING = {"00": "none", "10": "q0", "11": "q1", "01": "q2"}
INK, MUTED, GRID = "#222222", "#666666", "#e6e6e6"


def pretty(s):
    return s.replace("|", "$|$").replace(">", r"$\rangle$")


def load(results_dir):
    found = []
    for fname, label, colour in SOURCES:
        path = os.path.join(results_dir, fname)
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            rows = {(r["state"], r["error"]): r for r in data["rows"]}
            if fname == "hardware.json" and data.get("computer"):
                label = f"IQM hardware ({data['computer']})"
            found.append((label, colour, rows, data["shots"]))
    return found


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK)
    ax.yaxis.grid(True, color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def plot_success(found, results_dir):
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharey=True)
    x = np.arange(len(STATES))
    n = len(found)
    width = 0.8 / (n + 1)
    hardware = next((f for f in found if f[0].startswith("IQM hardware")), None)

    for ax, err in zip(axes.flat, ERRORS):
        for i, (label, colour, rows, _) in enumerate(found):
            vals = [rows[(s, err)]["success_corrected"] for s in STATES]
            ax.bar(x + (i - n / 2) * width, vals, width * 0.92, color=colour, label=label)
        if hardware:
            vals = [hardware[2][(s, err)]["success_uncorrected"] for s in STATES]
            ax.bar(x + (n - n / 2) * width, vals, width * 0.92, facecolor="white",
                   edgecolor=hardware[1], hatch="///", linewidth=1.2,
                   label="IQM hardware, correction switched off")
        ax.axhline(0.5, color=MUTED, linestyle=":", linewidth=1)
        ax.set_title("No error (I)" if err == "I" else f"Bit flip on q{err[1]} ({err})",
                     color=INK, fontsize=13, loc="left")
        ax.set_xticks(x - width / 2)
        ax.set_xticklabels([pretty(s) for s in STATES], fontsize=12)
        ax.set_ylim(0, 1.05)
        style(ax)
    for ax in axes[:, 0]:
        ax.set_ylabel("Fraction of shots where the\nsecret state came back right", color=INK)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False, fontsize=11)
    fig.suptitle("Level 1 bit-flip code: simulation vs IQM hardware "
                 "(dotted line = random guessing)", color=INK, fontsize=15, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    path = os.path.join(results_dir, "success_sim_vs_hardware.png")
    fig.savefig(path, dpi=150, facecolor="white")
    print(f"saved {os.path.relpath(path)}")


def plot_syndromes(found, results_dir):
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.6), sharey=True)
    x = np.arange(len(SYNDROMES))
    n = len(found)
    width = 0.8 / n
    for ax, err in zip(axes, ERRORS):
        for i, (label, colour, rows, _) in enumerate(found):
            # average over the six test states (the syndrome should not depend on the state)
            vals = [np.mean([rows[(s, err)]["syndromes"][k] for s in STATES]) for k in SYNDROMES]
            ax.bar(x + (i - (n - 1) / 2) * width, vals, width * 0.92, color=colour, label=label)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{k}\n(fix {SYNDROME_MEANING[k]})" for k in SYNDROMES], fontsize=10)
        ax.set_title(f"Injected error: {err}", color=INK, fontsize=13, loc="left")
        ax.set_ylim(0, 1.05)
        style(ax)
    axes[0].set_ylabel("Fraction of shots", color=INK)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False, fontsize=11)
    fig.suptitle("Which syndrome the helper qubits q3, q4 reported", color=INK, fontsize=15,
                 x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.93))
    path = os.path.join(results_dir, "syndromes_sim_vs_hardware.png")
    fig.savefig(path, dpi=150, facecolor="white")
    print(f"saved {os.path.relpath(path)}")


def main(results_dir):
    found = load(results_dir)
    if not found:
        raise SystemExit("No results yet. Run `python iqm/run_level1_iqm.py simulate` first.")
    plot_success(found, results_dir)
    plot_syndromes(found, results_dir)
