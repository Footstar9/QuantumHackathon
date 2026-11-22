"""
Automated tests. Run from the level1_python folder with:   python -m pytest
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import level1  # noqa: E402
import simulator as sim  # noqa: E402

EXPECTED_SYNDROME = {"I": (0, 0), "X0": (1, 0), "X1": (1, 1), "X2": (0, 1)}


# ---------------------------------------------------------------------------
# Simulator sanity checks
# ---------------------------------------------------------------------------

def test_x_flips_a_bit():
    state = sim.apply_gate(sim.zero_state(3), sim.X, 1)
    assert np.isclose(abs(state[0b010]), 1)


def test_hadamard_makes_equal_superposition():
    state = sim.apply_gate(sim.zero_state(1), sim.H, 0)
    assert np.allclose(state, [1 / np.sqrt(2), 1 / np.sqrt(2)])


def test_cnot_truth_table():
    for c in (0, 1):
        for t in (0, 1):
            start = sim.zero_state(2)
            if c:
                start = sim.apply_gate(start, sim.X, 0)
            if t:
                start = sim.apply_gate(start, sim.X, 1)
            out = sim.apply_cnot(start, control=0, target=1)
            expected_index = (c << 1) | (t ^ c)
            assert np.isclose(abs(out[expected_index]), 1)


def test_measurement_statistics():
    rng = np.random.default_rng(1)
    plus = sim.apply_gate(sim.zero_state(1), sim.H, 0)
    ones = sum(sim.measure(plus, 0, rng)[0] for _ in range(4000))
    assert 0.45 < ones / 4000 < 0.55


def test_encoding_gives_repetition_code():
    a, b = 0.6, 0.8
    state = level1.encode(level1.prepare(a, b))
    assert np.isclose(sim.fidelity(level1.logical_state(a, b), state, qubits=level1.DATA), 1)


# ---------------------------------------------------------------------------
# Level 1: all 4 errors x all 6 test states
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state_name", list(level1.TEST_STATES))
@pytest.mark.parametrize("error_name", list(level1.ERRORS))
def test_level1_recovers_logical_state(state_name, error_name):
    a, b = level1.TEST_STATES[state_name]
    result = level1.run(a, b, error_name, rng=np.random.default_rng(0))

    assert result["syndrome"] == EXPECTED_SYNDROME[error_name]
    assert result["fixed_qubit"] == level1.ERRORS[error_name]
    assert result["fidelity_encoded"] == pytest.approx(1, abs=1e-9)
    assert result["fidelity_decoded"] == pytest.approx(1, abs=1e-9)


@pytest.mark.parametrize("error_name", list(level1.ERRORS))
def test_syndrome_measurement_is_deterministic(error_name):
    """The syndrome must not be random: same answer for every run, every state."""
    a, b = level1.TEST_STATES["|+i>"]
    syndromes = {level1.run(a, b, error_name, rng=np.random.default_rng(seed))["syndrome"]
                 for seed in range(20)}
    assert syndromes == {EXPECTED_SYNDROME[error_name]}


def test_random_states_are_recovered():
    """Beyond the 6 required states: 50 random a|0>+b|1>."""
    rng = np.random.default_rng(42)
    for _ in range(50):
        a, b = rng.normal(size=2) + 1j * rng.normal(size=2)
        for error_name in level1.ERRORS:
            assert level1.run(a, b, error_name, rng=rng)["fidelity_decoded"] == pytest.approx(1)


# ---------------------------------------------------------------------------
# Controls: show the tests can actually fail
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("error_name", ["X0", "X1", "X2"])
def test_without_correction_state_is_lost(error_name):
    a, b = level1.TEST_STATES["|0>"]
    result = level1.run(a, b, error_name, correct=False)
    assert result["fidelity_encoded"] < 0.01


def test_phase_sensitive_check_catches_wrong_sign():
    """|+> and |-> look identical classically; fidelity must tell them apart."""
    plus = sim.single_qubit_state(1, 1)
    minus = sim.single_qubit_state(1, -1)
    assert sim.fidelity(plus, minus) < 1e-9


def test_two_flips_are_not_corrected():
    """Known limitation: two bit flips fool the code."""
    a, b = level1.TEST_STATES["|0>"]
    state = level1.encode(level1.prepare(a, b))
    state = sim.apply_gate(state, sim.X, 0)
    state = sim.apply_gate(state, sim.X, 1)
    syndrome, state = level1.measure_syndrome(level1.extract_syndrome(state))
    state, _ = level1.recover(state, syndrome)
    assert sim.fidelity(level1.logical_state(a, b), state, qubits=level1.DATA) < 0.01
