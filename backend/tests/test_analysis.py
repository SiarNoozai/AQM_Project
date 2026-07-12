from __future__ import annotations

import asyncio

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analysis import _build_sector_allocation, _calculate_returns, _metrics, _normalize_weights
from main import app
from models import AnalyzeRequest, AssetResult, RecommendRequest
from recommendations import build_rule_recommendation_response


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


def test_build_sector_allocation_groups_weights() -> None:
    assets = [
        AssetResult(
            ticker="AAPL",
            name="Apple",
            sector="Information Technology",
            instrumentType="EQUITY",
            weight=0.35,
            expectedReturn=0.12,
            volatility=0.24,
            lastPrice=200.0,
        ),
        AssetResult(
            ticker="MSFT",
            name="Microsoft",
            sector="Information Technology",
            instrumentType="EQUITY",
            weight=0.25,
            expectedReturn=0.11,
            volatility=0.22,
            lastPrice=420.0,
        ),
        AssetResult(
            ticker="AGG",
            name="US Aggregate Bond ETF",
            sector="Fixed Income",
            instrumentType="ETF",
            weight=0.40,
            expectedReturn=0.03,
            volatility=0.06,
            lastPrice=99.0,
        ),
    ]

    allocation = _build_sector_allocation(assets)

    assert allocation[0].sector == "Information Technology"
    assert allocation[0].weight == pytest.approx(0.60)
    assert allocation[1].sector == "Fixed Income"
    assert allocation[1].tickers == ["AGG"]


def test_analyze_request_accepts_up_to_ten_positions() -> None:
    request = AnalyzeRequest(
        tickers=["AAPL", "MSFT", "SPY", "AGG", "GOOG", "JNJ", "XLF", "XLI", "XLP", "XLU"],
        weights=[10] * 10,
        startDate="2020-01-01",
        endDate="2021-01-01",
        frequency="1d",
        riskFreeRate=0.02,
        varConfidence=0.95,
    )

    assert len(request.tickers) == 10


def test_rule_recommendation_response_is_structured() -> None:
    request = RecommendRequest(
        analysis={
            "assets": [
                {"ticker": "AAPL", "name": "Apple", "sector": "Information Technology", "weight": 0.35},
                {"ticker": "MSFT", "name": "Microsoft", "sector": "Information Technology", "weight": 0.30},
                {"ticker": "SPY", "name": "S&P 500 ETF", "sector": "ETF / Multi-Sektor", "weight": 0.25},
                {"ticker": "AGG", "name": "US Aggregate Bond ETF", "sector": "Fixed Income", "weight": 0.10},
            ],
            "sectorAllocation": [
                {"sector": "Information Technology", "weight": 0.65, "tickers": ["AAPL", "MSFT"]},
                {"sector": "ETF / Multi-Sektor", "weight": 0.25, "tickers": ["SPY"]},
                {"sector": "Fixed Income", "weight": 0.10, "tickers": ["AGG"]},
            ],
            "metrics": {
                "expectedReturn": 0.11,
                "volatility": 0.22,
                "sharpeRatio": 0.48,
                "valueAtRisk": 0.021,
                "diversificationScore": 54,
            },
            "optimizedMetrics": {
                "expectedReturn": 0.10,
                "volatility": 0.18,
                "sharpeRatio": 0.61,
                "valueAtRisk": 0.018,
                "diversificationScore": 68,
            },
            "optimizedWeights": [0.24, 0.22, 0.29, 0.25],
            "riskFindings": [
                {
                    "type": "concentration",
                    "severity": "high",
                    "message": "AAPL ist mit 35.0 Prozent stark gewichtet.",
                }
            ],
        },
        focusAreas=["summary", "sector", "concentration", "diversification", "risk_drivers"],
        investorProfile={"timeHorizon": "long_term", "riskStyle": "defensive"},
        goalPreset="diversify_broadly",
        goalNote="Bitte auf Branchenbreite achten.",
    )

    response = asyncio.run(build_rule_recommendation_response(request, "llama3.1"))

    assert response.summary
    assert response.profile_fit
    assert response.analysis_highlights
    assert response.weight_adjustments
    assert response.source == "rules"


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
