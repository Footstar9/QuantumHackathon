"""
Level 4 tests. Run from the level1_python folder with:   python -m pytest
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import level4  # noqa: E402
import simulator as sim  # noqa: E402


# ---------------------------------------------------------------------------
# The code itself
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state_name", list(level4.TEST_STATES))
def test_encoder_gives_four_qubit_code(state_name):
    a, b = level4.TEST_STATES[state_name]
    state = level4.encode(level4.prepare(a, b))
    assert sim.fidelity(level4.logical_state(a, b), state, qubits=level4.DATA) == pytest.approx(1)


@pytest.mark.parametrize("state_name", list(level4.TEST_STATES))
def test_decode_returns_secret_when_no_error(state_name):
    a, b = level4.TEST_STATES[state_name]
    state = level4.decode(level4.encode(level4.prepare(a, b)))
    psi = sim.single_qubit_state(a, b)
    assert sim.fidelity(psi, state, qubits=[level4.SECRET_QUBIT]) == pytest.approx(1)


def test_codeword_is_unchanged_by_flipping_all_four():
    """The pattern the phase check relies on."""
    ideal = level4.logical_state(0.6, 0.8)
    flipped = ideal
    for q in range(4):
        flipped = sim.apply_gate(flipped, sim.X, q)
    assert np.allclose(flipped, ideal)


# ---------------------------------------------------------------------------
# Every error type x every qubit x 6 secret states
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state_name", list(level4.TEST_STATES))
@pytest.mark.parametrize("error_name", level4.ERRORS)
def test_error_type_is_detected(state_name, error_name):
    a, b = level4.TEST_STATES[state_name]
    result = level4.run(a, b, error_name, rng=np.random.default_rng(0))
    assert result["detected"] == error_name[0]   # "I", "X", "Y" or "Z"


@pytest.mark.parametrize("state_name", list(level4.TEST_STATES))
@pytest.mark.parametrize("error_name", level4.ERRORS)
def test_checks_do_not_disturb_the_secret(state_name, error_name):
    """After measuring the helpers, the data is exactly (error x clean codeword)."""
    a, b = level4.TEST_STATES[state_name]
    result = level4.run(a, b, error_name, rng=np.random.default_rng(0))
    assert result["fidelity_with_error"] == pytest.approx(1, abs=1e-9)


@pytest.mark.parametrize("error_name", level4.ERRORS)
def test_readings_are_deterministic(error_name):
    """Same readings for every random seed and every secret state: nothing is left to chance."""
    seen = set()
    for (a, b) in level4.TEST_STATES.values():
        for seed in range(5):
            r = level4.run(a, b, error_name, rng=np.random.default_rng(seed))["readings"]
            seen.add(tuple(r.values()))
    assert len(seen) == 1


def test_random_secrets():
    rng = np.random.default_rng(11)
    for _ in range(20):
        a, b = rng.normal(size=2) + 1j * rng.normal(size=2)
        for error_name in level4.ERRORS:
            r = level4.run(a, b, error_name, rng=rng)
            assert r["detected"] == error_name[0]
            assert r["fidelity_with_error"] == pytest.approx(1)


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

def test_location_is_not_identified():
    """X0 and X1 ring the same alarm; all four Z positions ring the same alarm."""
    a, b = level4.TEST_STATES["|+>"]
    reading = lambda e: tuple(level4.run(a, b, e)["readings"].values())  # noqa: E731
    assert reading("X0") == reading("X1")
    assert reading("X2") == reading("X3")
    assert len({reading(f"Z{q}") for q in range(4)}) == 1


@pytest.mark.parametrize("pair", [("X0", "X1"), ("Z0", "Z1"), ("X2", "X3")])
def test_two_errors_can_go_unnoticed(pair):
    a, b = level4.TEST_STATES["|+>"]
    state = level4.encode(level4.prepare(a, b))
    for e in pair:
        state = level4.apply_error(state, e)
    readings, _ = level4.measure_helpers(level4.bit_checks(level4.phase_check(state)))
    assert level4.classify(readings) == "I"


def test_phase_check_is_needed():
    """With bit checks alone, Z errors are invisible (they would read as 'I')."""
    a, b = level4.TEST_STATES["|+>"]
    state = level4.apply_error(level4.encode(level4.prepare(a, b)), "Z2")
    state = level4.bit_checks(state)  # phase check skipped
    readings, _ = level4.measure_helpers(state)
    assert readings["bit01"] == readings["bit23"] == 0
