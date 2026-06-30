from __future__ import annotations

import os
from typing import Any

import httpx

try:
    from .analysis import DISCLAIMER, build_rule_recommendations
    from .models import RecommendResponse
except ImportError:
    from analysis import DISCLAIMER, build_rule_recommendations
    from models import RecommendResponse


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


async def generate_recommendations(analysis: dict[str, Any], model: str | None = None) -> RecommendResponse:
    model_name = model or OLLAMA_MODEL
    fallback = _fallback_response(analysis, model_name)
    prompt = _build_prompt(analysis)

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
            response.raise_for_status()
            text = response.json().get("response", "")
    except Exception:
        return fallback

    recommendations = _parse_recommendations(text)
    if not recommendations:
        return fallback

    return RecommendResponse(
        recommendations=recommendations[:5],
        source="ollama",
        model=model_name,
        disclaimer=DISCLAIMER,
    )


def _fallback_response(analysis: dict[str, Any], model_name: str) -> RecommendResponse:
    existing = analysis.get("recommendations")
    if isinstance(existing, list) and existing:
        recommendations = [str(item) for item in existing]
    else:
        tickers = [asset.get("ticker", "") for asset in analysis.get("assets", [])]
        weights = [asset.get("weight", 0) for asset in analysis.get("assets", [])]
        optimized_weights = analysis.get("optimizedWeights", weights)
        recommendations = build_rule_recommendations(
            tickers,
            weights,
            analysis.get("metrics", {}),
            analysis.get("optimizedMetrics", analysis.get("metrics", {})),
            optimized_weights,
        )

    return RecommendResponse(
        recommendations=[
            *recommendations[:4],
            "Ollama ist aktuell nicht erreichbar; diese Hinweise stammen aus der regelbasierten Fallback-Logik.",
        ],
        source="rules",
        model=model_name,
        disclaimer=DISCLAIMER,
    )


def _build_prompt(analysis: dict[str, Any]) -> str:
    metrics = analysis.get("metrics", {})
    optimized = analysis.get("optimizedMetrics", {})
    assets = analysis.get("assets", [])
    source = analysis.get("dataSource", "Yahoo Finance via yfinance")

    return f"""
Du bist die Interpretationsebene eines Ausbildungsprojekts fuer Privatanleger.
Du darfst keine Anlageberatung geben und keine konkreten Kauf-/Verkaufsempfehlungen formulieren.
Interpretiere nur die berechneten historischen Kennzahlen.

Datenquelle: {source}
Aktuelles Portfolio: {assets}
Kennzahlen aktuell: {metrics}
Kennzahlen optimiert: {optimized}
Optimierte Gewichte: {analysis.get("optimizedWeights", [])}

Formuliere exakt vier kurze deutsche Bulletpoints.
Jeder Bulletpoint soll konkret sein und eine Kennzahl oder Gewichtung nennen.
Erklaere, dass die KI die Quant-Ergebnisse interpretiert und die Optimierung nicht ersetzt.
""".strip()


def _parse_recommendations(text: str) -> list[str]:
    recommendations: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.removeprefix("-").removeprefix("*").strip()
        if line:
            recommendations.append(line)
    return recommendations
