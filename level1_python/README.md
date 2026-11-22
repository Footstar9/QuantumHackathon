# Quantum Minesweeper (Qublitz 2026 error-correction challenge)

All four levels are done in plain Python + numpy (a small simulator we wrote
ourselves), and Level 1 was also run on real IQM quantum hardware (Garnet).

## Results summary

| Level | Errors | Code | Result in simulation |
| --- | --- | --- | --- |
| 1 Bit-Flip Mines | X on one of 3 qubits | 3-qubit repetition code, 2 helper qubits | All 4 errors × 6 test states recovered with fidelity 1 |
| 2 Phase-Flip Mines | Z on one of 3 qubits | Level 1 wrapped in Hadamard layers | All 4 errors × 6 test states recovered with fidelity 1 |
| 3 Double-Crossed Mines | Y on one of 3 qubits | Level 1 syndrome, then X and Z on the blamed qubit | All 4 errors × 6 test states recovered (up to a global phase i) |
| 4 Mystery Mines | I, X, Y or Z on one of 4 qubits | 4-qubit code, 2 bit checks + 1 phase check | All 13 cases × 6 test states classified correctly |
| IQM hardware | Level 1 | 24 circuits, 1000 shots each on IQM Garnet | Average success 89.2% (noisy simulator 89.9%, ideal 100%) |

**Evidence the corrections work:** `python -m pytest -v` in this folder runs
360 automated tests (all pass). Each level checks every allowed error on the
six test states |0⟩, |1⟩, |+⟩, |−⟩, |+i⟩, |−i⟩ plus 50 random states, and also
includes "broken variant" and "limit" tests that show the checks really can
fail. On hardware, for |0⟩, |1⟩, |+i⟩ and |−i⟩, an X error on q0 left uncorrected
gives only 4 to 10% success, and with our correction it gives 84 to 88%. Details and the
explanation of simulator vs hardware are in [`iqm/README.md`](iqm/README.md).

Circuit diagrams for every level are in [`diagrams/`](diagrams/).

## Files

| File | What it is |
| --- | --- |
| `simulator.py` | A tiny quantum simulator written from scratch: state vectors, gates (X, Y, Z, H, S, CNOT), measurement, fidelity. |
| `level1.py` | The Level 1 circuit, one function per stage. Run it for a table of all 24 cases. |
| `walkthrough.py` | Runs the circuit stage by stage and explains each step in plain language. |
| `level2.py`, `walkthrough_level2.py` | Level 2 (phase flips). Reuses `level1.py` and adds two Hadamard layers. |
| `level3.py`, `walkthrough_level3.py` | Level 3 (Y errors), helper-qubit method. Reuses `level1.py`. |
| `level4.py`, `walkthrough_level4.py` | Level 4 (detect error type) on a 4-qubit code. |
| `tests/` | Automated tests for all four levels and for the IQM circuits. |
| `diagrams/` | Circuit diagrams (PNG) and the scripts that draw them. |
| `iqm/` | The Level 1 run on IQM hardware: script, saved results and plots. |

## How to reproduce

From the repository root:

```
pip install -r requirements.txt
cd level1_python
python -m pytest -v            # all tests
python level1.py               # table of all 24 Level 1 cases (same for level2.py, level3.py, level4.py)
python walkthrough.py X1 --pause   # step-by-step explanation (also walkthrough_level2/3/4.py)
```

For the IQM part see [`iqm/README.md`](iqm/README.md).

## Attribution

Circuit designs for Levels 2 to 4 are Oscar's own. Code, tests and
documentation were written with the help of Claude (an AI assistant by
Anthropic) and checked by running the tests. Hardware access: IQM Resonance.

## Level 1: Bit-Flip Mines (plain Python + numpy)

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

## Level 4: Mystery Mines (detect the error type)

### The idea in a few sentences (for the judges)

We spread the secret a|0⟩ + b|1⟩ (starting on q2) over four qubits:
a(|0000⟩ + |1111⟩)/√2 + b(|0011⟩ + |1100⟩)/√2. Every configuration in it has
three patterns: q0 = q1, q2 = q3, and flipping all four bits gives the same
state back. A bit flip (X) breaks q0 = q1 or q2 = q3. A phase flip (Z) leaves
the bits alone but breaks the flip-all-four symmetry with a minus sign. A Y
(= iXZ) breaks both. Three helper qubits check the patterns: two parity
checks, as in Level 1, give the **bit alarm**, and one phase check (helper in
superposition, CNOT onto all four data qubits) gives the **phase alarm**.
(bit, phase) = (0,0) → I, (1,0) → X, (0,1) → Z, (1,1) → Y. Every check reads
a pattern shared by both the a and b parts, so the secret is never measured.

### Encoder and checks (data q0–q3, helpers q4 phase, q5 and q6 bit)

```
encode : H q1 ; CNOT q2→q3 ; CNOT q1→q0 ; CNOT q1→q2 ; CNOT q1→q3
error  : X, Y or Z on one data qubit (or none)
phase  : H q4 ; CNOT q4→q0, q4→q1, q4→q2, q4→q3 ; H q4 ; measure q4
bits   : CNOT q0→q5, q1→q5 ; CNOT q2→q6, q3→q6 ; measure q5, q6
decode : bit alarm = q5 OR q6, phase alarm = q4, then the table above
```

### Results

All 13 cases (no error, plus X, Y and Z on each of the 4 qubits) × 6 secret
states are classified correctly, and 50 random secrets give the same result.
The readings never depend on the secret or on chance. After the helpers are
measured, the data qubits are exactly (error × clean codeword), with fidelity 1,
so detection did not destroy the secret.

| Error | q4 q5 q6 | Detected |
| --- | --- | --- |
| I | 0 0 0 | I |
| X0, X1 | 0 1 0 | X |
| X2, X3 | 0 0 1 | X |
| Y0, Y1 | 1 1 0 | Y |
| Y2, Y3 | 1 0 1 | Y |
| Z0–Z3 | 1 0 0 | Z |

**Limits (also tested):** the type is found but not always the location: X0 and
X1 look the same, and all four Z positions look the same. Two errors can cancel
out: X0 + X1 reads as "no error". Without the phase check, Z errors are invisible.

Run it: `cd level1_python`, then `python walkthrough_level4.py Y1 --pause` (any of `I`, `X0`–`X3`, `Y0`–`Y3`, `Z0`–`Z3`), `python level4.py` for the table, and `python -m pytest -v` for every test.

### Porting to Qiskit later

Each function in `level1.py` is a few gates, so it maps line for line:
`apply_cnot(s, 0, 1)` → `qc.cx(0, 1)`, `apply_gate(s, X, 2)` → `qc.x(2)`, `hadamard_layer` → `qc.h([0, 1, 2])`,
`measure_syndrome` → `qc.measure([3, 4], [0, 1])`, and the lookup table becomes
classically controlled X gates (or post-processing on hardware).
One gotcha: Qiskit prints bitstrings with qubit 0 on the **right**; here qubit 0 is on the left.
