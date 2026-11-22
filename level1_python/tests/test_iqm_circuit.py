"""
Checks that the Qiskit version of Level 1 (iqm/run_level1_iqm.py) is correct
on a perfect simulator: every state x every error must come back right.
Skipped automatically if qiskit / qiskit-aer are not installed.
"""

import os
import sys

import pytest

pytest.importorskip("qiskit")
pytest.importorskip("qiskit_aer")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "iqm"))

import run_level1_iqm as iqm  # noqa: E402
from qiskit import transpile  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402

EXPECTED = {"I": "00", "X0": "10", "X1": "11", "X2": "01"}


@pytest.mark.parametrize("state,error", iqm.all_cases())
def test_ideal_circuit_recovers_state(state, error):
    sim = AerSimulator()
    qc = transpile(iqm.build_circuit(state, error), sim)
    counts = sim.run(qc, shots=200, seed_simulator=1).result().get_counts()
    r = iqm.analyse(state, error, counts)
    assert r["success_corrected"] == 1.0
    assert r["syndrome_correct"] == 1.0
    assert r["syndromes"][EXPECTED[error]] == 1.0


def test_switching_off_correction_breaks_z_reading():
    """Control: without the software fix, an X0 error ruins |0>, so the test can fail."""
    sim = AerSimulator()
    counts = sim.run(transpile(iqm.build_circuit("|0>", "X0"), sim), shots=200).result().get_counts()
    assert iqm.analyse("|0>", "X0", counts)["success_uncorrected"] == 0.0
