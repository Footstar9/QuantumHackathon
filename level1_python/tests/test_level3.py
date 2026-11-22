"""
Level 3 tests. Run from the level1_python folder with:   python -m pytest
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import level1  # noqa: E402
import level3  # noqa: E402
import simulator as sim  # noqa: E402

EXPECTED_SYNDROME = {"I": (0, 0), "Y0": (1, 0), "Y1": (1, 1), "Y2": (0, 1)}
BASIS_STATES = ["|0>", "|1>"]
SUPERPOSITION_STATES = ["|+>", "|->", "|+i>", "|-i>"]


# ---------------------------------------------------------------------------
# The building blocks
# ---------------------------------------------------------------------------

def test_y_equals_i_x_z():
    assert np.allclose(sim.Y, 1j * sim.X @ sim.Z)


def test_global_phase_does_not_change_fidelity():
    psi = sim.single_qubit_state(0.6, 0.8)
    assert sim.fidelity(psi, 1j * psi) == pytest.approx(1)


def test_relative_sign_does_change_fidelity():
    plus, minus = sim.single_qubit_state(1, 1), sim.single_qubit_state(1, -1)
    assert sim.fidelity(plus, minus) < 1e-9


# ---------------------------------------------------------------------------
# Level 3: all 4 errors x all 6 test states
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state_name", list(level3.TEST_STATES))
@pytest.mark.parametrize("error_name", list(level3.ERRORS))
def test_level3_recovers_logical_state(state_name, error_name):
    a, b = level3.TEST_STATES[state_name]
    result = level3.run(a, b, error_name, rng=np.random.default_rng(0))

    assert result["syndrome"] == EXPECTED_SYNDROME[error_name]
    assert result["fixed_qubit"] == level3.ERRORS[error_name]
    assert result["fidelity_encoded"] == pytest.approx(1, abs=1e-9)
    assert result["fidelity_decoded"] == pytest.approx(1, abs=1e-9)


@pytest.mark.parametrize("error_name", ["Y0", "Y1", "Y2"])
def test_only_a_global_phase_is_left(error_name):
    """After recovery the data equals i * (a|000> + b|111>): same up to global phase i."""
    a, b = 0.6, 0.8
    state = level1.encode(level1.prepare(a, b))
    state = level3.apply_error(state, error_name)
    syndrome, state = level1.measure_syndrome(level1.extract_syndrome(state))
    state, _ = level3.recover(state, syndrome)
    # Expected: the clean codeword, helpers holding the syndrome bits, all times i
    helpers = sim.zero_state(2)
    if syndrome[0]:
        helpers = sim.apply_gate(helpers, sim.X, 0)
    if syndrome[1]:
        helpers = sim.apply_gate(helpers, sim.X, 1)
    expected = 1j * sim.combine(level1.logical_state(a, b), helpers)
    assert np.allclose(state, expected)          # equal amplitudes, including the i
    assert not np.allclose(state, expected / 1j)  # so the raw numbers DO differ by i


@pytest.mark.parametrize("error_name", list(level3.ERRORS))
def test_syndrome_measurement_is_deterministic(error_name):
    a, b = level3.TEST_STATES["|+i>"]
    syndromes = {level3.run(a, b, error_name, rng=np.random.default_rng(seed))["syndrome"]
                 for seed in range(20)}
    assert syndromes == {EXPECTED_SYNDROME[error_name]}


def test_random_states_are_recovered():
    rng = np.random.default_rng(3)
    for _ in range(50):
        a, b = rng.normal(size=2) + 1j * rng.normal(size=2)
        for error_name in level3.ERRORS:
            assert level3.run(a, b, error_name, rng=rng)["fidelity_decoded"] == pytest.approx(1)


# ---------------------------------------------------------------------------
# Limits and deliberately broken variants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("error_name", ["Y0", "Y1", "Y2"])
@pytest.mark.parametrize("state_name", BASIS_STATES)
def test_skipping_z_step_looks_fine_on_basis_states(state_name, error_name):
    """Without the Z step, |0> and |1> still pass: a sign on a single branch is a global phase."""
    a, b = level3.TEST_STATES[state_name]
    assert level3.run(a, b, error_name, fix_phase=False)["fidelity_decoded"] == pytest.approx(1)


@pytest.mark.parametrize("error_name", ["Y0", "Y1", "Y2"])
@pytest.mark.parametrize("state_name", SUPERPOSITION_STATES)
def test_skipping_z_step_fails_on_superpositions(state_name, error_name):
    """...but superpositions expose the wrong relative sign. This is why we test 6 states."""
    a, b = level3.TEST_STATES[state_name]
    assert level3.run(a, b, error_name, fix_phase=False)["fidelity_decoded"] < 0.01


def test_without_correction_state_is_lost():
    a, b = level3.TEST_STATES["|0>"]
    for error_name in ["Y0", "Y1", "Y2"]:
        assert level3.run(a, b, error_name, correct=False)["fidelity_encoded"] < 0.01


@pytest.mark.parametrize("error_name", ["X0", "X1", "X2", "Z0", "Z1", "Z2"])
@pytest.mark.parametrize("state_name", SUPERPOSITION_STATES)
def test_x_only_or_z_only_errors_are_not_corrected(state_name, error_name):
    """
    Outside the Level 3 rules. The recovery ASSUMES 'bit flip found' means 'Y':
      * X alone: we add a Z that was never needed -> wrong sign.
      * Z alone: syndrome (0, 0), we do nothing  -> wrong sign stays.
    """
    a, b = level3.TEST_STATES[state_name]
    assert level3.run(a, b, error_name)["fidelity_decoded"] < 0.01
