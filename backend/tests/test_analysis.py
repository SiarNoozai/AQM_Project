from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analysis import (
    _build_strategy_results,
    _calculate_returns,
    _metrics,
    _normalize_weights,
    _risk_contributions,
)
from main import app


def test_calculate_returns_daily() -> None:
    prices = pd.DataFrame({"AAPL": [100.0, 110.0, 121.0], "MSFT": [50.0, 55.0, 60.5]})

    returns = _calculate_returns(prices, "1d")

    assert returns.shape == (2, 2)
    assert returns.iloc[0]["AAPL"] == pytest.approx(0.10)
    assert returns.iloc[1]["MSFT"] == pytest.approx(0.10)


def test_metrics_and_weight_normalization() -> None:
    returns = pd.DataFrame(
        {
            "AAPL": [0.01, 0.02, -0.01, 0.03],
            "MSFT": [0.00, 0.01, 0.02, -0.01],
        }
    )
    mean_returns = returns.mean() * 252
    covariance = returns.cov() * 252
    weights = _normalize_weights(np.array([60.0, 40.0]))

    metrics = _metrics(mean_returns, covariance, returns, weights, 0.02, 0.95)

    assert weights.sum() == pytest.approx(1.0)
    assert metrics.expected_return > 0
    assert metrics.volatility > 0
    assert isinstance(metrics.sharpe_ratio, float)
    assert metrics.value_at_risk >= 0


def test_risk_contributions_sum_to_one() -> None:
    covariance = pd.DataFrame(
        [[0.04, 0.01], [0.01, 0.09]],
        index=["AAPL", "MSFT"],
        columns=["AAPL", "MSFT"],
    )
    weights = np.array([0.5, 0.5])

    contributions = _risk_contributions(["AAPL", "MSFT"], weights, covariance)

    total = sum(item.percent_contribution for item in contributions.values())
    assert total == pytest.approx(1.0)
    assert contributions["MSFT"].percent_contribution > contributions["AAPL"].percent_contribution


def test_strategy_results_include_required_variants() -> None:
    returns = pd.DataFrame(
        {
            "AAPL": [0.01, 0.02, -0.01, 0.03, 0.01],
            "MSFT": [0.00, 0.01, 0.02, -0.01, 0.02],
            "AGG": [0.001, 0.002, 0.0, 0.001, 0.001],
        }
    )
    mean_returns = returns.mean() * 252
    covariance = returns.cov() * 252
    current = np.array([0.5, 0.3, 0.2])
    optimized = np.array([0.34, 0.33, 0.33])

    strategies = _build_strategy_results(
        ["AAPL", "MSFT", "AGG"],
        current,
        mean_returns,
        covariance,
        returns,
        0.02,
        0.95,
        optimized,
    )

    assert {strategy.id for strategy in strategies} == {
        "low_volatility",
        "diversified",
        "return_oriented",
        "max_sharpe",
    }
    assert all(sum(strategy.weights) == pytest.approx(1.0) for strategy in strategies)


def test_api_health_and_validation_error() -> None:
    client = TestClient(app)

    assert client.get("/api/health").status_code == 200
    response = client.post(
        "/api/analyze",
        json={
            "tickers": ["AAPL", "MSFT"],
            "weights": [100],
            "startDate": "2020-01-01",
            "endDate": "2021-01-01",
            "frequency": "1d",
            "riskFreeRate": 0.02,
            "varConfidence": 0.95,
        },
    )

    assert response.status_code == 422


def test_api_ask_uses_rule_fallback() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/ask",
        json={
            "question": "Was bedeutet der VaR?",
            "analysis": {
                "metrics": {"valueAtRisk": 0.021, "sharpeRatio": 0.8},
                "assets": [],
                "riskFindings": [],
                "strategies": [],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "Value at Risk" in body["answer"]
    assert "keine Anlageberatung" in body["answer"]
