# QuBlitz 2026 (Princeton Quantum Hackathon): our submissions

This repository holds three separate challenge entries. Each folder has its own README with the
full write-up, results and run instructions.

| Challenge | Folder | What it is |
| --- | --- | --- |
| **Quantum Minesweeper** (error correction) | [`level1_python/`](level1_python/) | Levels 1 to 4 in plain Python + numpy, 360 tests, and Level 1 run on real IQM Garnet hardware ([`level1_python/iqm/`](level1_python/iqm/)) |
| **Magic State Verification** | [`magic_state/`](magic_state/) | Level 1 Pauli tomography and Level 2 fidelity estimation from X and Z shots, with experiments and tests |
| **Quantum Create** | [`schrodingers_cargo/`](schrodingers_cargo/) | *Schrödinger's \|Cargo⟩*, a two-player browser game about Shor's 9-qubit code, with a printable handout |

## Run commands

Install Python 3 first (and [Node.js](https://nodejs.org) only for the game's tests). Run everything from the repository root.

**Quantum Minesweeper**

```
pip install -r requirements.txt
cd level1_python
python -m pytest -v               # all 360 tests
python level1.py                  # results table (also level2.py, level3.py, level4.py)
python walkthrough.py X1 --pause  # step-by-step explanation
pip install -r iqm/requirements-iqm.txt
python iqm/run_level1_iqm.py simulate   # ideal + noisy Garnet simulation (no token needed)
python iqm/run_level1_iqm.py plot       # redraw simulator vs hardware plots from saved results
cd ..
```

**Magic State Verification**

```
pip install -r magic_state/requirements.txt
python magic_state/experiments.py
python magic_state/experiments_level2.py
python -m pytest magic_state -q
```

**Quantum Create**

Open `schrodingers_cargo/index.html` in a browser (works offline, nothing to install).
Tests: `node schrodingers_cargo/tests/test_qec.js`. Rules and write-up: `schrodingers_cargo/handout.pdf`.

## Attribution

Concepts, circuit designs and direction by our team (Oscar). Code, tests and documentation were
written with the help of Claude, an AI assistant by Anthropic, and checked by running the tests.
Hardware access through IQM Resonance. Published methods are cited in each folder's README.
