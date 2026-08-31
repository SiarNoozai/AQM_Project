from __future__ import annotations

import asyncio
import json

from backend.conversation import answer_question, build_digest, build_rule_answer, build_rule_goal_proposal, generate_goal_chat_reply
from backend.models import AskRequest, ChatMessage, GoalChatRequest


def _analysis() -> dict:
    return {
        "mode": "demo",
        "dataSource": "Demo",
        "startDate": "2020-01-01",
        "endDate": "2024-01-01",
        "riskFreeRate": 0.025,
        "varConfidence": 0.95,
        "assets": [
            {"ticker": "AAPL", "name": "Apple", "sector": "Information Technology", "weight": 0.6, "expectedReturn": 0.1, "volatility": 0.2},
            {"ticker": "AGG", "name": "AGG", "sector": "Fixed Income", "weight": 0.4, "expectedReturn": 0.03, "volatility": 0.06},
        ],
        "metrics": {
            "expectedReturn": 0.07,
            "annualizedReturnGeometric": 0.06,
            "volatility": 0.15,
            "sharpeRatio": 0.3,
            "valueAtRisk": 0.02,
            "valueAtRiskHorizonDays": 1,
            "valueAtRiskMethod": "historisch",
            "diversificationScore": 50,
            "effectiveHoldings": 1.9,
            "diversificationRatio": 1.1,
        },
        "optimizedMetrics": {"sharpeRatio": 0.35, "volatility": 0.1},
        "optimizedWeights": [0.5, 0.5],
        "sectorAllocation": [],
        "riskFindings": [],
        "recommendations": [],
    }


def test_goal_rules_recognize_retirement_and_low_risk() -> None:
    proposal, reply, _, confidence = build_rule_goal_proposal(
        [ChatMessage(role="user", content="Ich will fuer die Rente sparen und moechte moeglichst wenig Risiko")]
    )

    assert proposal is not None
    assert proposal.time_horizon == "long_term"
    assert proposal.risk_style == "defensive"
    assert proposal.goal_preset == "defensive"
    assert confidence == "high"
    assert "langfristig" in reply


def test_digest_excludes_raw_ballast() -> None:
    digest = build_digest({**_analysis(), "frontier": [], "performance": [], "covarianceMatrix": [[1]]})

    assert "frontier" not in digest
    assert "performance" not in digest
    assert "covarianceMatrix" not in digest


def test_rule_answer_uses_actual_sharpe_value() -> None:
    answer, used_metrics = build_rule_answer("Was ist die Sharpe Ratio?", build_digest(_analysis()))

    assert "0,30" in answer
    assert "sharpeRatio" in used_metrics


def test_validation_falls_back_for_foreign_ticker(monkeypatch) -> None:
    async def foreign_answer(*_args, **_kwargs):
        return json.dumps({"answer": "MSFT wird steigen.", "usedMetrics": ["sharpeRatio"]})

    monkeypatch.setattr("backend.conversation._call_ollama", foreign_answer)
    response = asyncio.run(
        answer_question(AskRequest(question="Was ist meine Sharpe Ratio?", analysis=_analysis(), llm_preference="local"))
    )

    assert response.source == "rules"
    assert response.fallback_reason == "validation_failed"
    assert "0,30" in response.answer


def test_validation_falls_back_for_trade_instruction(monkeypatch) -> None:
    async def trade_answer(*_args, **_kwargs):
        return json.dumps({"answer": "Kaufen Sie AAPL jetzt.", "usedMetrics": ["sharpeRatio"]})

    monkeypatch.setattr("backend.conversation._call_ollama", trade_answer)
    response = asyncio.run(
        answer_question(AskRequest(question="Was ist meine Sharpe Ratio?", analysis=_analysis(), llm_preference="local"))
    )

    assert response.source == "rules"
    assert response.fallback_reason == "validation_failed"


def test_goal_chat_rejects_trade_language_from_model(monkeypatch) -> None:
    async def unsafe_goal_answer(*_args, **_kwargs):
        return json.dumps({"reply": "Kaufen Sie AAPL jetzt.", "proposal": None, "confidence": "medium"})

    monkeypatch.setattr("backend.conversation._call_ollama", unsafe_goal_answer)
    request = GoalChatRequest(messages=[ChatMessage(role="user", content="Ich möchte langfristig vorsichtig investieren.")])

    response = asyncio.run(generate_goal_chat_reply(request))

    assert response.source == "rules"
    assert response.fallback_reason == "validation_failed"
