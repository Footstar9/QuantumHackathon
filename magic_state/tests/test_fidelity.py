import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fidelity
from fidelity import (
    split_budget, collect_xz_counts, estimate_fidelity, fidelity_experiment, true_fidelity,
)
from tomography import T_BLOCH, bloch_from_pure, bloch_to_rho

STATES = [
    T_BLOCH, 0.9 * T_BLOCH, 0.5 * T_BLOCH, bloch_from_pure(1, 0), bloch_from_pure(0, 1),
    bloch_from_pure(1, 1), bloch_from_pure(1, 1j), np.zeros(3), -T_BLOCH,
]


def test_brief_example_200_shots():
    est = estimate_fidelity({"X": (84, 16), "Z": (85, 15)})
    assert np.isclose(est["r_x"], 0.68) and np.isclose(est["r_z"], 0.70)
    assert round(est["F_hat"], 3) == 0.988
    assert est["shots"] == 200


def test_true_fidelity_matches_overlap_formula():
    t = np.array([np.cos(np.pi / 8), np.sin(np.pi / 8)])
    for r in STATES:
        assert np.isclose(true_fidelity(r), np.real(t @ bloch_to_rho(r) @ t))
    assert np.isclose(true_fidelity(T_BLOCH), 1)
    assert np.isclose(true_fidelity(-T_BLOCH), 0)
    assert np.isclose(true_fidelity(np.zeros(3)), 0.5)


def test_fidelity_ignores_y():
    a = estimate_fidelity({"X": (70, 30), "Z": (60, 40)})
    assert np.isclose(true_fidelity([0.4, 0.9, 0.2]), true_fidelity([0.4, -0.9, 0.2]))
    assert "Y" not in collect_xz_counts(T_BLOCH, 100, np.random.default_rng(0))
    assert a["shots"] == 200


@pytest.mark.parametrize("total,expected", [(2, (1, 1)), (200, (100, 100)), (201, (101, 100))])
def test_split_budget(total, expected):
    assert split_budget(total) == expected
    counts = collect_xz_counts(T_BLOCH, total, np.random.default_rng(0))
    assert (sum(counts["X"]), sum(counts["Z"])) == expected


def test_split_budget_rejects_tiny():
    with pytest.raises(ValueError):
        split_budget(1)


def test_clipping_to_unit_interval():
    # each r_hat is in [-1, 1], so r_x + r_z can reach 2 and raw F can exceed 1
    hi = estimate_fidelity({"X": (10, 0), "Z": (10, 0)})   # r = (1, 1), raw F = 1.207
    assert hi["F_raw"] > 1 and hi["F_hat"] == 1.0
    lo = estimate_fidelity({"X": (0, 10), "Z": (0, 10)})
    assert lo["F_raw"] < 0 and lo["F_hat"] == 0.0
    for est in (hi, lo):
        assert 0 <= est["ci"][0] <= est["ci"][1] <= 1


def test_standard_error_formula():
    est = estimate_fidelity({"X": (84, 16), "Z": (85, 15)})
    se_x = np.sqrt((1 - 0.68 ** 2) / 100)
    se_z = np.sqrt((1 - 0.70 ** 2) / 100)
    assert np.isclose(est["se"], np.sqrt(se_x ** 2 + se_z ** 2) / (2 * np.sqrt(2)))


@pytest.mark.parametrize("r", STATES)
@pytest.mark.parametrize("n", [2, 3, 10, 100, 1000])
def test_estimate_always_in_unit_interval(r, n):
    rng = np.random.default_rng(0)
    for _ in range(50):
        est = fidelity_experiment(r, n, rng)
        assert 0 <= est["F_hat"] <= 1
        assert 0 <= est["ci"][0] <= est["F_hat"] <= est["ci"][1] <= 1


@pytest.mark.parametrize("r", STATES)
def test_error_shrinks_with_budget(r):
    rng = np.random.default_rng(1)
    f = true_fidelity(r)
    rmse = [np.sqrt(np.mean([(fidelity_experiment(r, b, rng)["F_hat"] - f) ** 2
                             for _ in range(300)])) for b in [20, 200, 2000, 20000]]
    assert all(a > b for a, b in zip(rmse, rmse[1:])), rmse
    assert rmse[-1] < 0.01


@pytest.mark.parametrize("r", [0.5 * T_BLOCH, np.zeros(3), bloch_from_pure(1, 0), bloch_from_pure(1, 1j)])
def test_confidence_interval_coverage_about_95(r):
    rng = np.random.default_rng(2)
    f = true_fidelity(r)
    hits = 0
    for _ in range(2000):
        lo, hi = fidelity_experiment(r, 1000, rng)["ci"]
        hits += lo <= f <= hi
    assert 0.92 <= hits / 2000 <= 0.98


def test_stated_se_matches_spread():
    rng = np.random.default_rng(3)
    r = 0.5 * T_BLOCH
    ests = [fidelity_experiment(r, 2000, rng) for _ in range(2000)]
    spread = np.std([e["F_hat"] for e in ests])
    mean_se = np.mean([e["se"] for e in ests])
    assert abs(spread / mean_se - 1) < 0.1


def test_beats_tomography_at_equal_budget():
    from tomography import tomography, magic_fidelity
    rng = np.random.default_rng(4)
    r, b = 0.9 * T_BLOCH, 600
    f = true_fidelity(r)
    xz = np.mean([(fidelity_experiment(r, b, rng)["F_hat"] - f) ** 2 for _ in range(2000)])
    tomo = np.mean([(magic_fidelity(tomography(r, b // 3, rng)[1]) - f) ** 2 for _ in range(2000)])
    assert xz < tomo


def test_reproducible_with_seed():
    a = fidelity_experiment(T_BLOCH, 500, np.random.default_rng(2026))
    b = fidelity_experiment(T_BLOCH, 500, np.random.default_rng(2026))
    assert a == b


def test_estimator_never_sees_true_state():
    # estimate_fidelity takes only counts; the module's estimator has no state argument
    import inspect
    assert list(inspect.signature(estimate_fidelity).parameters) == ["counts", "z"]
    counts = collect_xz_counts(0.3 * T_BLOCH, 100, np.random.default_rng(0))
    assert set(counts) == {"X", "Z"} and all(isinstance(v, int) for c in counts.values() for v in c)


def test_rejects_unphysical_state():
    with pytest.raises(ValueError):
        collect_xz_counts([1, 1, 1], 100, np.random.default_rng(0))
