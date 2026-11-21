# Quantum Hackathon (Qublitz 2026): Quantum Minesweeper

## Level 1: Bit-Flip Mines (plain Python + numpy)

Everything lives in [`level1_python/`](level1_python/):

| File | What it is |
| --- | --- |
| `simulator.py` | A tiny quantum simulator written from scratch: state vectors, gates (X, Y, Z, H, S, CNOT), measurement, fidelity. |
| `level1.py` | The Level 1 circuit, one function per stage. Run it for a table of all 24 cases. |
| `walkthrough.py` | Runs the circuit stage by stage and explains each step in plain language. |
| `tests/test_level1.py` | Automated tests: 4 errors × 6 test states, plus controls that show the tests can fail. |

### The idea in a few sentences (for the judges)

We cannot copy a qubit, but we can spread it out: two CNOT gates turn
a|0⟩ + b|1⟩ into a|000⟩ + b|111⟩, so the three qubits always agree.
A bit flip makes one qubit disagree with the other two. Instead of looking at
the data (which would destroy a and b), we ask two parity questions with
helper qubits: "do q0 and q1 disagree?" and "do q1 and q2 disagree?". Both
branches of the superposition give the same answers, so measuring the helpers
tells us *where* the flip is without revealing anything about a or b.
The two answers point to exactly one qubit (10 → q0, 11 → q1, 01 → q2,
00 → none), we flip it back, and the original state is recovered with
fidelity 1 for all six test states, including |+⟩, |−⟩, |+i⟩, |−i⟩, which
prove the *phases* survive and not just classical 0/1 values.
Limitation: two simultaneous flips fool the code (it "corrects" the wrong
qubit and swaps a and b), so it only protects against single bit flips.

### How we verify recovery

After recovery we compare the data qubits with the ideal a|000⟩ + b|111⟩,
and after decoding we compare q0 with the original a|0⟩ + b|1⟩, using the
fidelity |⟨ψ_ideal|ψ⟩|² (1 = identical). Global phase does not count; relative
phase does, which is why |+⟩ vs |−⟩ is a meaningful test.

### Circuit (5 qubits: q0–q2 data, q3–q4 helpers)

```
q0: ─[ψ]──●────●──── E ──●──────────────── X? ──●────●──
q1: ──────X────┼──── E ──┼────●────●────── X? ──┼────X──
q2: ───────────X──── E ──┼────┼────┼────●─ X? ──X───────
q3: ─────────────────────X────X────┼────┼── M ──────────
q4: ───────────────────────────────X────X── M ──────────
       encode      error    syndrome      fix   decode
```

### Run it in VS Code

1. Open the `QuantumHackathon` folder in VS Code (File → Open Folder).
2. Open a terminal: Terminal → New Terminal.
3. Install the two packages once: `pip install -r requirements.txt`
4. Go into the folder: `cd level1_python`
5. Walkthrough: `python walkthrough.py` (or `python walkthrough.py X0`, `X2`, `I`; add `--pause` to step with Enter)
6. All 24 cases: `python level1.py`
7. Tests: `python -m pytest -v`

### Porting to Qiskit later

Each function in `level1.py` is a few gates, so it maps line for line:
`apply_cnot(s, 0, 1)` → `qc.cx(0, 1)`, `apply_gate(s, X, 2)` → `qc.x(2)`,
`measure_syndrome` → `qc.measure([3, 4], [0, 1])`, and the lookup table becomes
classically controlled X gates (or post-processing on hardware).
One gotcha: Qiskit prints bitstrings with qubit 0 on the **right**; here qubit 0 is on the left.
