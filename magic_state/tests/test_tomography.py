import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tomography import (
    T_BLOCH, bloch_from_pure, bloch_to_rho, rho_to_bloch, tomography, collect_counts,
    reconstruct, estimate_bloch, make_physical, is_physical, trace_distance,
    bloch_distance, p_plus_via_rotation, magic_fidelity,
)

STATES = [
    bloch_from_pure(1, 0), bloch_from_pure(0, 1), bloch_from_pure(1, 1),
    bloch_from_pure(1, 1j), T_BLOCH, np.zeros(3), np.array([0.5, 0, 0.5]),
    np.array([0.6, 0.55, 0.57]),
]


@pytest.mark.parametrize("r", STATES)
@pytest.mark.parametrize("n", [1, 5, 10, 100, 1000])
def test_output_always_physical(r, n):
    rng = np.random.default_rng(0)
    for _ in range(50):
        rho_hat, r_hat, _ = tomography(r, n, rng)
        assert np.allclose(rho_hat, rho_hat.conj().T)          # Hermitian
        assert np.isclose(np.trace(rho_hat).real, 1)            # trace 1
        assert np.min(np.linalg.eigvalsh(rho_hat)) >= -1e-12    # PSD
        assert np.linalg.norm(r_hat) <= 1 + 1e-12


def test_rescaling_triggers_and_fixes_unphysical_estimate():
    counts = {"X": (10, 0), "Y": (10, 0), "Z": (10, 0)}  # raw r = (1,1,1), |r| = 1.73
    assert np.linalg.norm(estimate_bloch(counts)) > 1
    assert np.min(np.linalg.eigvalsh(bloch_to_rho(estimate_bloch(counts)))) < 0  # unphysical before
    rho_hat, r_hat, rescaled = reconstruct(counts)
    assert rescaled
    assert np.isclose(np.linalg.norm(r_hat), 1)
    assert is_physical(rho_hat)


def test_no_rescaling_inside_sphere():
    r, rescaled = make_physical(np.array([0.3, 0.2, 0.1]))
    assert not rescaled and np.allclose(r, [0.3, 0.2, 0.1])


def test_estimator_formula():
    counts = {"X": (84, 16), "Y": (50, 50), "Z": (85, 15)}  # numbers from the brief
    assert np.allclose(estimate_bloch(counts), [0.68, 0.0, 0.70])


@pytest.mark.parametrize("r", STATES)
def test_error_shrinks_with_shots(r):
    rng = np.random.default_rng(1)
    errs = []
    for n in [10, 100, 1000, 10000]:
        errs.append(np.mean([trace_distance(tomography(r, n, rng)[0], bloch_to_rho(r))
                             for _ in range(100)]))
    assert all(a > b for a, b in zip(errs, errs[1:])), errs
    assert errs[-1] < 0.02


def test_seed_reproducible():
    a = tomography(T_BLOCH, 500, np.random.default_rng(42))[0]
    b = tomography(T_BLOCH, 500, np.random.default_rng(42))[0]
    c = tomography(T_BLOCH, 500, np.random.default_rng(43))[0]
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_estimator_never_sees_true_state():
    # reconstruct takes only counts: the same counts give the same answer for any truth
    counts = collect_counts(T_BLOCH, 100, np.random.default_rng(3))
    assert np.array_equal(reconstruct(counts)[0], reconstruct(dict(counts))[0])


@pytest.mark.parametrize("r", STATES)
def test_rotation_cross_check_matches_formula(r):
    rho = bloch_to_rho(r)
    for i, p in enumerate("XYZ"):
        assert np.isclose(p_plus_via_rotation(rho, p), (1 + r[i]) / 2)


def test_helpers():
    assert np.allclose(T_BLOCH, bloch_from_pure(np.cos(np.pi / 8), np.sin(np.pi / 8)))
    assert np.isclose(magic_fidelity(T_BLOCH), 1)
    assert np.allclose(rho_to_bloch(bloch_to_rho([0.1, -0.2, 0.3])), [0.1, -0.2, 0.3])
    r1, r2 = np.array([0.1, 0.2, 0.3]), np.array([-0.2, 0.0, 0.5])
    assert np.isclose(trace_distance(bloch_to_rho(r1), bloch_to_rho(r2)), bloch_distance(r1, r2) / 2)
    with pytest.raises(ValueError):
        tomography([1, 1, 0], 10, np.random.default_rng(0))
