from __future__ import annotations

import numpy as np
import pytest

from backend.analysis import _diversification_score, _shrink_covariance, optimize_portfolio


def _sample_inputs() -> tuple[np.ndarray, np.ndarray]:
    return (
        np.array([0.14, 0.13, 0.09, 0.03]),
        np.array(
            [
                [0.04, 0.018, 0.012, -0.002],
                [0.018, 0.032, 0.011, -0.001],
                [0.012, 0.011, 0.022, -0.001],
                [-0.002, -0.001, -0.001, 0.004],
            ]
        ),
    )


def test_diversification_score_uses_effective_holdings() -> None:
    assert _diversification_score(np.array([0.25, 0.25, 0.25, 0.25])) == pytest.approx(100)
    assert _diversification_score(np.array([0.35, 0.30, 0.25, 0.10])) == pytest.approx(83.63, abs=0.1)
    assert _diversification_score(np.array([0.90, 0.10])) < 30


@pytest.mark.parametrize("objective", ["max_sharpe", "min_volatility", "max_diversification"])
def test_optimizer_respects_bounds_and_full_investment(objective: str) -> None:
    mean_returns, covariance = _sample_inputs()

    weights = optimize_portfolio(mean_returns, covariance, 0.025, objective, max_weight=0.35)

    assert weights.sum() == pytest.approx(1)
    assert np.all(weights >= -1e-8)
    assert np.all(weights <= 0.35 + 1e-8)


def test_optimizer_raises_too_low_minimum_weight() -> None:
    mean_returns, covariance = _sample_inputs()

    with pytest.raises(ValueError):
        optimize_portfolio(mean_returns, covariance, 0.025, "max_sharpe", max_weight=0.35, min_weight=0.26)


def test_optimizer_raises_max_weight_when_needed() -> None:
    mean_returns, covariance = _sample_inputs()

    weights = optimize_portfolio(mean_returns, covariance, 0.025, "max_sharpe", max_weight=0.1)

    assert weights.sum() == pytest.approx(1)
    assert np.all(weights <= 0.25 + 1e-8)


def test_shrinkage_changes_off_diagonal_structure_but_preserves_diagonal() -> None:
    _, covariance = _sample_inputs()

    shrunk = np.asarray(_shrink_covariance(covariance, intensity=0.5))

    assert not np.allclose(shrunk, covariance)
    assert np.diag(shrunk) == pytest.approx(np.diag(covariance))
