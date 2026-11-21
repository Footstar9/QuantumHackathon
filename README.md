# Quantum Hackathon (Qublitz 2026): Quantum Minesweeper

## Level 1: Bit-Flip Mines (plain Python + numpy)

Everything lives in [`level1_python/`](level1_python/):

| File | What it is |
| --- | --- |
| `simulator.py` | A tiny quantum simulator written from scratch: state vectors, gates (X, Y, Z, H, S, CNOT), measurement, fidelity. |
| `level1.py` | The Level 1 circuit, one function per stage. Run it for a table of all 24 cases. |
| `walkthrough.py` | Runs the circuit stage by stage and explains each step in plain language. |
| `tests/test_level1.py` | Automated tests: 4 errors × 6 test states, plus controls that show the tests can fail. |
| `level2.py` | Level 2 (phase flips). Reuses `level1.py` and adds two Hadamard layers. |
| `walkthrough_level2.py` | Stage-by-stage Level 2 walkthrough, including the H-frame stages. |
| `tests/test_level2.py` | Level 2 tests: 4 errors × 6 states, plus the limit and broken-variant checks. |

| `level3.py` | Level 3 (Y errors), helper-qubit method. Reuses `level1.py`. |
| `walkthrough_level3.py` | Stage-by-stage Level 3 walkthrough. |
| `tests/test_level3.py` | Level 3 tests: 4 errors × 6 states, plus the limit and broken-variant checks. |

(The folder is still called `level1_python` but now holds Levels 2 and 3 too.)

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

## Level 2: Phase-Flip Mines

### The idea in a few sentences (for the judges)

A phase flip Z does not flip a bit, it puts a minus sign on the |1⟩ part.
On the Level 1 codeword a|000⟩ + b|111⟩, a Z on q0, q1 or q2 gives the *same*
state a|000⟩ − b|111⟩, so the three errors are indistinguishable and the
parity checks see nothing. The fix is to change frame with Hadamards, using
H Z H = X. After encoding, we apply H to all three data qubits, so the stored
state is a|+++⟩ + b|−−−⟩. The error happens in this frame. Then we apply H
again: the hit qubit sees H Z H = X (a bit flip) and the others see H H = I.
That is exactly a Level 1 situation, so the Level 1 syndrome, lookup table
and decode run unchanged, and all 6 test states come back with fidelity 1.
Limitation: this code no longer fixes bit flips. An X in the H frame becomes
a Z on the plain codeword, which the checks cannot see. That needs Level 3.

### Circuit (5 qubits: q0–q2 data, q3–q4 helpers)

```
q0: ─[ψ]──●────●── H ── E ── H ──[ Level 1 syndrome ]── X? ──[ decode ]──
q1: ──────X────┼── H ── E ── H ──[  (4 CNOTs onto  ]── X? ──[        ]──
q2: ───────────X── H ── E ── H ──[   q3 and q4)    ]── X? ──[        ]──
       encode    enter  error leave      measure q3, q4     fix
                H frame      H frame
```

### What the Level 2 tests check

- All 4 errors (I, Z0, Z1, Z2) × 6 test states: right syndrome, right qubit fixed, fidelity 1. Plus 50 random states and a check that the syndrome never changes between runs.
- Why the H frame is needed: Z0, Z1, Z2 give identical states on the plain codeword, and the Level 1 syndrome reports (0, 0).
- **Limit:** X errors on the Level 2 code are *not* corrected for |+⟩, |−⟩, |+i⟩, |−i⟩ (fidelity 0). On |0⟩ and |1⟩ they happen to do no harm, which shows why testing only |0⟩ and |1⟩ would be misleading.
- **Broken variant:** skipping the second Hadamard layer makes recovery fail.

Run it: `cd level1_python`, then `python walkthrough_level2.py Z1 --pause` (or `Z0`, `Z2`, `I`), `python level2.py` for all 24 cases, and `python -m pytest -v` for every test of both levels.

## Level 3: Double-Crossed Mines (helper-qubit method, no Toffoli gates)

### The idea in a few sentences (for the judges)

Y = iXZ, so a Y error is a bit flip and a phase flip on the same qubit, times
an overall factor i. We use the plain Level 1 code a|000⟩ + b|111⟩. The X part
of the Y knocks one qubit out of line, so Level 1's two helper qubits and lookup
table find *which* qubit j was hit. We undo the X part with X on j. That leaves
i(a|000⟩ − b|111⟩): the Z part has flipped the sign between the two branches,
and the parity checks cannot see that. But the rules guarantee every non-trivial
error is a Y, so finding a bit flip also tells us a phase flip happened. We
apply Z on j (Z on any one data qubit would work) and get i(a|000⟩ + b|111⟩).
If the syndrome is 00 we do nothing at all, because adding a Z there would
*create* an error. Level 1's decode then finishes the job, with fidelity 1 on
all six test states.

**Global phase vs relative sign:** the leftover factor i multiplies the whole
state, so no measurement can ever detect it, and fidelity rightly ignores it.
The minus sign *between* the a and b branches is different: it turns |+⟩ into
|−⟩, which a measurement can detect. That sign is what the Z step repairs.

### Circuit (5 qubits: q0–q2 data, q3–q4 helpers)

```
q0: ─[ψ]──●────●── Y? ──[ Level 1 syndrome ]── X? ── Z? ──[ decode ]──
q1: ──────X────┼── Y? ──[  (4 CNOTs onto  ]── X? ── Z? ──[        ]──
q2: ───────────X── Y? ──[   q3 and q4)    ]── X? ── Z? ──[        ]──
       encode     error     measure q3, q4    X and Z on qubit j only
                                              if the syndrome is not 00
```

### What the Level 3 tests check

- All 4 errors (I, Y0, Y1, Y2) × 6 test states: right syndrome, right qubit, fidelity 1. Plus 50 random states and a check that the syndrome never changes between runs.
- After recovery the state is exactly i × (the original), so the only difference left is the global phase.
- **Broken variant:** skipping the Z step still passes on |0⟩ and |1⟩ but fails (fidelity 0) on |+⟩, |−⟩, |+i⟩, |−i⟩. A test using only basis states would miss this mistake.
- **Limit:** an X-only or Z-only error is *not* corrected. X alone gets an unnecessary Z added, and Z alone gives syndrome 00 so nothing is fixed. Both are outside the Level 3 rules ("any non-trivial error is a Y"). Handling X, Y and Z together needs a bigger code such as Shor's 9-qubit code.

Run it: `cd level1_python`, then `python walkthrough_level3.py Y1 --pause` (or `Y0`, `Y2`, `I`), `python level3.py` for all 24 cases, and `python -m pytest -v` for every test of all three levels.

### Porting to Qiskit later

Each function in `level1.py` is a few gates, so it maps line for line:
`apply_cnot(s, 0, 1)` → `qc.cx(0, 1)`, `apply_gate(s, X, 2)` → `qc.x(2)`, `hadamard_layer` → `qc.h([0, 1, 2])`,
`measure_syndrome` → `qc.measure([3, 4], [0, 1])`, and the lookup table becomes
classically controlled X gates (or post-processing on hardware).
One gotcha: Qiskit prints bitstrings with qubit 0 on the **right**; here qubit 0 is on the left.
