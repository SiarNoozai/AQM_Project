from __future__ import annotations

import asyncio

import numpy as np

from backend.models import RecommendRequest
from backend.recommendations import _compact_analysis, _optimization_inputs, build_rule_recommendation_response, generate_recommendations


def _analysis(include_covariance: bool = True) -> dict:
    value = {
        "assets": [
            {"ticker": "AAPL", "name": "Apple", "sector": "Information Technology", "weight": 0.35, "expectedReturn": 0.14},
            {"ticker": "MSFT", "name": "Microsoft", "sector": "Information Technology", "weight": 0.30, "expectedReturn": 0.13},
            {"ticker": "SPY", "name": "SPY", "sector": "ETF / Multi-Sektor", "weight": 0.25, "expectedReturn": 0.09},
            {"ticker": "AGG", "name": "AGG", "sector": "Fixed Income", "weight": 0.10, "expectedReturn": 0.03},
        ],
        "metrics": {"expectedReturn": 0.11, "volatility": 0.22, "sharpeRatio": 0.48, "valueAtRisk": 0.02, "diversificationScore": 83},
        "optimizedMetrics": {},
        "optimizedWeights": [0.25, 0.25, 0.25, 0.25],
        "riskFindings": [],
        "sectorAllocation": [],
        "riskFreeRate": 0.025,
    }
    if include_covariance:
        value["covarianceMatrix"] = [
            [0.04, 0.018, 0.012, -0.002],
            [0.018, 0.032, 0.011, -0.001],
            [0.012, 0.011, 0.022, -0.001],
            [-0.002, -0.001, -0.001, 0.004],
        ]
    return value


def _request(analysis: dict, risk_style: str, goal: str) -> RecommendRequest:
    return RecommendRequest(
        analysis=analysis,
        focusAreas=["summary", "diversification"],
        investorProfile={"timeHorizon": "long_term", "riskStyle": risk_style},
        goalPreset=goal,
    )


def test_optimization_inputs_rejects_invalid_matrix() -> None:
    assert _optimization_inputs(_analysis(include_covariance=False)) is None
    assert "covarianceMatrix" not in _compact_analysis(_analysis(), "small")
    assert "covarianceMatrix" not in _compact_analysis(_analysis(), "large")


def test_profiles_produce_different_weight_targets() -> None:
    analysis = _analysis()
    defensive = asyncio.run(build_rule_recommendation_response(_request(analysis, "defensive", "defensive"), "test"))
    aggressive = asyncio.run(build_rule_recommendation_response(_request(analysis, "aggressive", "keep_tech_focus"), "test"))

    assert defensive.optimization_basis.objective == "min_volatility"
    assert aggressive.optimization_basis.objective == "max_sharpe"
    assert [item.suggested_weight for item in defensive.weight_adjustments] != [
        item.suggested_weight for item in aggressive.weight_adjustments
    ]


def test_missing_covariance_falls_back_to_analysis_weights() -> None:
    response = asyncio.run(build_rule_recommendation_response(_request(_analysis(False), "defensive", "defensive"), "test"))

    assert response.optimization_basis.objective == "fallback"


def test_provider_fallback_exposes_attempted_backends(monkeypatch) -> None:
    async def unavailable(*_args, **_kwargs):
        return None, "unreachable"

    monkeypatch.setattr("backend.recommendations._call_lmstudio_with_status", unavailable)
    monkeypatch.setattr("backend.recommendations._call_ollama_with_status", unavailable)

    response = asyncio.run(
        generate_recommendations(_request(_analysis(), "balanced", "balanced").model_copy(update={"llm_preference": "local"}))
    )

    assert response.source == "rules"
    assert response.fallback_reason == "no_backend_reachable"
    assert response.attempted_backends == ["LM Studio", "Ollama"]
