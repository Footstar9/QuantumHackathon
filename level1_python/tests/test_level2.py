"""
Level 2 tests. Run from the level1_python folder with:   python -m pytest
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import level1  # noqa: E402
import level2  # noqa: E402
import simulator as sim  # noqa: E402

EXPECTED_SYNDROME = {"I": (0, 0), "Z0": (1, 0), "Z1": (1, 1), "Z2": (0, 1)}
SUPERPOSITION_STATES = ["|+>", "|->", "|+i>", "|-i>"]


# ---------------------------------------------------------------------------
# The building blocks
# ---------------------------------------------------------------------------

def test_hzh_equals_x():
    assert np.allclose(sim.H @ sim.Z @ sim.H, sim.X)
    assert np.allclose(sim.H @ sim.X @ sim.H, sim.Z)


def test_stored_state_is_plus_plus_plus_minus_minus_minus():
    a, b = 0.6, 0.8
    state = level2.hadamard_layer(level1.encode(level1.prepare(a, b)))
    ideal = level2.stored_logical_state(a, b)
    assert sim.fidelity(ideal, state, qubits=level2.DATA) == pytest.approx(1)


def test_plain_codeword_cannot_tell_z_errors_apart():
    """Why Level 2 needs the H frame: Z0, Z1, Z2 give the same state on a|000>+b|111>."""
    plain = level1.encode(level1.prepare(0.6, 0.8))
    hit = [sim.apply_gate(plain, sim.Z, q) for q in level2.DATA]
    assert np.allclose(hit[0], hit[1]) and np.allclose(hit[1], hit[2])
    # ...and Level 1's syndrome sees nothing wrong
    syndrome, _ = level1.measure_syndrome(level1.extract_syndrome(hit[0]))
    assert syndrome == (0, 0)


# ---------------------------------------------------------------------------
# Level 2: all 4 errors x all 6 test states
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state_name", list(level2.TEST_STATES))
@pytest.mark.parametrize("error_name", list(level2.ERRORS))
def test_level2_recovers_logical_state(state_name, error_name):
    a, b = level2.TEST_STATES[state_name]
    result = level2.run(a, b, error_name, rng=np.random.default_rng(0))

    assert result["syndrome"] == EXPECTED_SYNDROME[error_name]
    assert result["fixed_qubit"] == level2.ERRORS[error_name]
    assert result["fidelity_encoded"] == pytest.approx(1, abs=1e-9)
    assert result["fidelity_decoded"] == pytest.approx(1, abs=1e-9)


@pytest.mark.parametrize("error_name", list(level2.ERRORS))
def test_syndrome_measurement_is_deterministic(error_name):
    a, b = level2.TEST_STATES["|+i>"]
    syndromes = {level2.run(a, b, error_name, rng=np.random.default_rng(seed))["syndrome"]
                 for seed in range(20)}
    assert syndromes == {EXPECTED_SYNDROME[error_name]}


def test_random_states_are_recovered():
    rng = np.random.default_rng(7)
    for _ in range(50):
        a, b = rng.normal(size=2) + 1j * rng.normal(size=2)
        for error_name in level2.ERRORS:
            assert level2.run(a, b, error_name, rng=rng)["fidelity_decoded"] == pytest.approx(1)


# ---------------------------------------------------------------------------
# Limits and deliberately broken variants
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state_name", SUPERPOSITION_STATES)
@pytest.mark.parametrize("error_name", ["X0", "X1", "X2"])
def test_bit_flips_are_not_corrected(state_name, error_name):
    """
    An X in the H frame becomes Z on the plain codeword, which the parity checks
    cannot see. Syndrome says 'no error' and the relative sign is lost.
    """
    a, b = level2.TEST_STATES[state_name]
    result = level2.run(a, b, error_name)
    assert result["syndrome"] == (0, 0)
    assert result["fidelity_decoded"] < 0.01


@pytest.mark.parametrize("state_name", ["|0>", "|1>"])
@pytest.mark.parametrize("error_name", ["X0", "X1", "X2"])
def test_bit_flips_invisible_on_basis_states(state_name, error_name):
    """
    Same X errors leave |0> and |1> untouched (a sign on b=0 or a=0 changes nothing).
    This is why testing ONLY |0> and |1> would wrongly suggest Level 2 fixes X.
    """
    a, b = level2.TEST_STATES[state_name]
    assert level2.run(a, b, error_name)["fidelity_decoded"] == pytest.approx(1)


def test_without_correction_state_is_lost():
    a, b = level2.TEST_STATES["|0>"]
    for error_name in ["Z0", "Z1", "Z2"]:
        result = level2.run(a, b, error_name, correct=False)
        assert result["fidelity_encoded"] < 0.01


@pytest.mark.parametrize("error_name", list(level2.ERRORS))
def test_skipping_second_hadamard_breaks_it(error_name):
    """Without leaving the H frame, the checks measure garbage: some test state is lost."""
    fidelities = []
    for a, b in level2.TEST_STATES.values():
        r = level2.run(a, b, error_name, second_hadamard=False, rng=np.random.default_rng(0))
        fidelities.append(r["fidelity_decoded"])
    assert min(fidelities) < 0.9
