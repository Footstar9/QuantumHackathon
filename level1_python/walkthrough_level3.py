"""
Step-by-step walkthrough of Level 3 (Double-Crossed Mines), helper-qubit method.

Run it:
    python walkthrough_level3.py               # default: error Y1
    python walkthrough_level3.py Y0            # pick the error: I, Y0, Y1 or Y2
    python walkthrough_level3.py Y2 --pause    # wait for Enter between stages
"""

import sys

import level1
import level3
import simulator as sim

ALPHA, BETA = 0.6, 0.8
GROUPS = [3, 2]

error_name = next((a for a in sys.argv[1:] if not a.startswith("--")), "Y1")
PAUSE = "--pause" in sys.argv
psi = sim.single_qubit_state(ALPHA, BETA)


def stage(title, explanation, state):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)
    print(explanation.strip())
    print("\nState now:")
    print(sim.show(state, GROUPS))
    if PAUSE:
        input("\n[press Enter for the next stage]")


# ---------------------------------------------------------------------------
# Why Level 1 alone fails
# ---------------------------------------------------------------------------
print("=" * 72)
print("WHY LEVEL 1 ALONE FAILS: Y on q1, fixed with Level 1's X only")
print("=" * 72)
r = level3.run(ALPHA, BETA, "Y1", fix_phase=False)
print(f"""Level 1 finds the bit-flip part (syndrome {r['syndrome']}) and flips q1 back,
but Y = i X Z also contained a Z. The data ends as i({ALPHA}|000> - {BETA}|111>):
the minus sign between the two branches is a real change.
Fidelity with the original after decoding: {r['fidelity_decoded']:.6f} (not 1).
On |+> = (|0>+|1>)/sqrt2 it is even worse: it turns into |->, fidelity
{level3.run(*level3.TEST_STATES['|+>'], 'Y1', fix_phase=False)['fidelity_decoded']:.6f}.""")
if PAUSE:
    input("\n[press Enter to start the Level 3 circuit]")

# ---------------------------------------------------------------------------
state = level1.prepare(ALPHA, BETA)
stage("STAGE 0: the information we want to protect",
      f"q0 holds {ALPHA}|0> + {BETA}|1>. All other qubits start at 0.", state)

state = level1.encode(state)
stage("STAGE 1: encode (Level 1's two CNOTs, no Hadamards this time)",
      f"{ALPHA}|000> + {BETA}|111>.", state)

state = level3.apply_error(state, error_name)
where = level3.ERRORS[error_name]
stage(
    f"STAGE 2: the mine goes off (error = {error_name})",
    ("No error this time. Nothing changes." if where is None else f"""
Y = i X Z hits q{where}. Three things happened at once:
  * X: q{where} is out of line in both branches (the syndrome will see this)
  * Z: the sign of the {BETA} branch flipped (the syndrome cannot see this)
  * i: every amplitude is multiplied by i (global phase, harmless)
That is why the amplitudes now print as imaginary numbers like +0.600i.
"""),
    state,
)

state = level1.extract_syndrome(state)
syndrome, state = level1.measure_syndrome(state)
stage(
    f"STAGE 3: Level 1 syndrome with helper qubits, unchanged -> {syndrome}",
    """
Same four CNOTs onto q3, q4, then measure only the helpers.
They locate the bit-flip part of the Y. Lookup table is Level 1's.
""",
    state,
)

state, fixed = level1.recover(state, syndrome)
stage(
    "STAGE 4a: undo the bit-flip part (X on the blamed qubit)",
    ("Syndrome (0, 0): no error, so we skip BOTH corrections." if fixed is None else f"""
X on q{fixed}. The qubits line up again, but the sign is still wrong:
i({ALPHA}|000> - {BETA}|111>). Level 1 would stop here and fail.
"""),
    state,
)

if fixed is not None:
    state = sim.apply_gate(state, sim.Z, fixed)
stage(
    "STAGE 4b: undo the phase-flip part (Z on the same qubit)",
    ("Skipped. Adding a Z when nothing went wrong would CREATE a phase error." if fixed is None else f"""
The rules promise every error is a Y, so a non-zero syndrome means a Z
happened too. Z on q{fixed} flips the sign of the |111> branch back:
i({ALPHA}|000> + {BETA}|111>). (Z on any one data qubit would do the same.)
The leftover factor i multiplies EVERYTHING, so it is a global phase:
no measurement can ever detect it. Fidelity ignores it for that reason.
"""),
    state,
)
f_enc = sim.fidelity(level1.logical_state(ALPHA, BETA), state, qubits=level3.DATA)

state = level1.decode(state)
stage("STAGE 5: Level 1 decode, unchanged",
      f"q0 is back to {ALPHA}|0> + {BETA}|1> (times the harmless global i, if Y hit).", state)

print("\n" + "=" * 72)
print("RESULT")
print("=" * 72)
print(f"Fidelity of data qubits vs a|000>+b|111> after recovery : {f_enc:.6f}")
print(f"Fidelity of q0 vs the original a|0>+b|1> after decoding : {sim.fidelity(psi, state, qubits=[0]):.6f}")

# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("LIMITATION: only works because every error is promised to be a Y")
print("=" * 72)
rx = level3.run(*level3.TEST_STATES["|+>"], "X1")
rz = level3.run(*level3.TEST_STATES["|+>"], "Z1")
print(f"""On |+>:
  X on q1 alone: syndrome {rx['syndrome']} -> we apply X AND Z, adding a phase flip
                 that never happened. Fidelity {rx['fidelity_decoded']:.6f}.
  Z on q1 alone: syndrome {rz['syndrome']} -> looks like 'no error', the sign stays wrong.
                 Fidelity {rz['fidelity_decoded']:.6f}.
Both are outside the Level 3 rules. Handling X, Y and Z together needs more
qubits (e.g. Shor's 9-qubit code).""")
