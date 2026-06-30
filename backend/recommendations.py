from __future__ import annotations

import os
from typing import Any

import httpx

try:
    from .analysis import DISCLAIMER, build_rule_recommendations
    from .models import AskResponse, RecommendResponse, ReportSection
except ImportError:
    from analysis import DISCLAIMER, build_rule_recommendations
    from models import AskResponse, RecommendResponse, ReportSection


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
        report=_build_rule_report(analysis),
        source="ollama",
        model=model_name,
        disclaimer=DISCLAIMER,
    )


async def answer_question(analysis: dict[str, Any], question: str, model: str | None = None) -> AskResponse:
    model_name = model or OLLAMA_MODEL
    fallback = _fallback_answer(analysis, question, model_name)
    prompt = _build_question_prompt(analysis, question)

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.15},
                },
            )
            response.raise_for_status()
            text = str(response.json().get("response", "")).strip()
    except Exception:
        return fallback

    if not text:
        return fallback
    if "anlageberatung" not in text.lower():
        text = f"{text}\n\nHinweis: Dies ist keine Anlageberatung, sondern eine Erklaerung der berechneten Kennzahlen."
    return AskResponse(answer=text, source="ollama", model=model_name, disclaimer=DISCLAIMER)


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

    behavioral_message = _behavioral_message(analysis)
    visible_recommendations = recommendations[:4]
    if behavioral_message and behavioral_message not in visible_recommendations:
        visible_recommendations.append(behavioral_message)

    return RecommendResponse(
        recommendations=[
            *visible_recommendations,
            "Ollama ist aktuell nicht erreichbar; diese Hinweise stammen aus der regelbasierten Fallback-Logik.",
        ],
        report=_build_rule_report(analysis),
        source="rules",
        model=model_name,
        disclaimer=DISCLAIMER,
    )


def _build_rule_report(analysis: dict[str, Any]) -> list[ReportSection]:
    metrics = analysis.get("metrics", {})
    optimized = analysis.get("optimizedMetrics", {})
    assets = analysis.get("assets", [])
    allocation = analysis.get("assetAllocation", {})
    findings = analysis.get("riskFindings", [])
    strategies = analysis.get("strategies", [])
    top_risk = _top_risk_asset(assets)

    return [
        ReportSection(
            title="Kurze Zusammenfassung",
            content=(
                f"Das Portfolio erreicht historisch eine Rendite von {_pct(metrics.get('expectedReturn'))} "
                f"bei einer Volatilitaet von {_pct(metrics.get('volatility'))} und einer Sharpe Ratio von "
                f"{_num(metrics.get('sharpeRatio'))}."
            ),
        ),
        ReportSection(title="Portfoliozusammensetzung", content=_asset_summary(assets)),
        ReportSection(
            title="Rendite- und Risikoanalyse",
            content=(
                f"Der historische Value at Risk betraegt {_pct(metrics.get('valueAtRisk'))}. "
                f"Die Max-Sharpe-Variante kommt auf Sharpe {_num(optimized.get('sharpeRatio'))}."
            ),
        ),
        ReportSection(title="Diversifikation und Asset Allocation", content=_allocation_summary(allocation)),
        ReportSection(title="Wichtigste Risikotreiber", content=top_risk),
        ReportSection(
            title="Erklaerung der Sharpe Ratio",
            content="Die Sharpe Ratio setzt historische Mehrrendite ins Verhaeltnis zur Volatilitaet. Hoeher bedeutet in dieser Rueckrechnung mehr Rendite je Risikoeinheit.",
        ),
        ReportSection(
            title="Erklaerung des Value at Risk",
            content="Der Value at Risk beschreibt einen historischen Verlustschwellenwert fuer ein gewaehltes Konfidenzniveau. Er ist keine garantierte Verlustobergrenze.",
        ),
        ReportSection(title="Vergleich alternativer Gewichtungen", content=_strategy_summary(strategies)),
        ReportSection(title="Behavioral-Finance-Hinweise", content=_behavioral_message(analysis) or "Keine besondere Behavioral-Auffaelligkeit berechnet."),
        ReportSection(title="Grenzen der Analyse", content="Die Analyse nutzt historische Kursdaten und teilweise nur verfuegbare oder abgeschaetzte Metadaten. Sie erzeugt keine Prognose."),
        ReportSection(title="Hinweis: keine Anlageberatung", content=DISCLAIMER),
    ]


def _fallback_answer(analysis: dict[str, Any], question: str, model_name: str) -> AskResponse:
    normalized = question.lower()
    metrics = analysis.get("metrics", {})
    assets = analysis.get("assets", [])
    findings = analysis.get("riskFindings", [])

    if "var" in normalized or "value at risk" in normalized:
        answer = (
            f"Der Value at Risk liegt hier bei {_pct(metrics.get('valueAtRisk'))}. "
            "Er zeigt, welcher historische Tagesverlust beim gewaehlten Konfidenzniveau ueberschritten wurde. "
            "Das ist keine Garantie und keine Verlustobergrenze."
        )
    elif "sharpe" in normalized:
        answer = (
            f"Die Sharpe Ratio betraegt {_num(metrics.get('sharpeRatio'))}. "
            "Sie vergleicht historische Mehrrendite mit Schwankungsrisiko; hoehere Werte bedeuten rueckblickend mehr Rendite je Risikoeinheit."
        )
    elif "risiko" in normalized or "riskant" in normalized or "beitrag" in normalized:
        answer = _top_risk_asset(assets)
    elif "divers" in normalized:
        relevant = next((item for item in findings if isinstance(item, dict) and item.get("type") in {"diversification", "correlation", "allocation"}), None)
        answer = str(relevant.get("message")) if relevant else "Die Diversifikation wird ueber Gewichtungen, Korrelationen und Asset Allocation bewertet."
    else:
        answer = "Die Rueckfrage wird auf Basis der berechneten Kennzahlen beantwortet. Stelle am besten konkret nach VaR, Sharpe Ratio, Diversifikation oder Risikotreibern."

    return AskResponse(
        answer=f"{answer}\n\nHinweis: Dies ist keine Anlageberatung, sondern eine Erklaerung der berechneten Kennzahlen.",
        source="rules",
        model=model_name,
        disclaimer=DISCLAIMER,
    )


def _behavioral_message(analysis: dict[str, Any]) -> str | None:
    findings = analysis.get("riskFindings", [])
    if not isinstance(findings, list):
        return None
    for finding in findings:
        if isinstance(finding, dict) and finding.get("type") == "behavioral":
            return str(finding.get("message", "")).strip() or None
    return None


def _build_prompt(analysis: dict[str, Any]) -> str:
    metrics = analysis.get("metrics", {})
    optimized = analysis.get("optimizedMetrics", {})
    assets = analysis.get("assets", [])
    allocation = analysis.get("assetAllocation", {})
    risk_findings = analysis.get("riskFindings", [])
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
Asset Allocation: {allocation}
Regelbasierte Auffaelligkeiten: {risk_findings}

Formuliere exakt fuenf kurze deutsche Bulletpoints.
Jeder Bulletpoint soll konkret sein und eine Kennzahl, Gewichtung, Auffaelligkeit oder Behavioral-Finance-Beobachtung nennen.
Erklaere, dass die KI die Quant-Ergebnisse interpretiert und die Optimierung nicht ersetzt.
""".strip()


def _build_question_prompt(analysis: dict[str, Any], question: str) -> str:
    return f"""
Du beantwortest Rueckfragen zu einem Portfolioanalyse-Tool.
Nutze ausschliesslich den strukturierten Kontext. Erfinde keine Finanzdaten, keine Kurse und keine Prognosen.
Keine Kauf- oder Verkaufsempfehlungen. Immer kurz erwaehnen: keine Anlageberatung.

Rueckfrage: {question}
Kennzahlen: {analysis.get("metrics", {})}
Assets: {analysis.get("assets", [])}
Asset Allocation: {analysis.get("assetAllocation", {})}
Risikohinweise: {analysis.get("riskFindings", [])}
Strategien: {analysis.get("strategies", [])}

Antworte auf Deutsch in maximal 120 Woertern.
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


def _asset_summary(assets: list[Any]) -> str:
    if not assets:
        return "Keine Asset-Daten verfuegbar."
    parts = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        parts.append(
            f"{asset.get('ticker', '')}: {_pct(asset.get('weight'))}, "
            f"{asset.get('assetClass', 'unbekannt')}, {asset.get('sector', 'unbekannt')}"
        )
    return "; ".join(parts) or "Keine Asset-Daten verfuegbar."


def _allocation_summary(allocation: dict[str, Any]) -> str:
    if not isinstance(allocation, dict):
        return "Keine Asset-Allocation-Daten verfuegbar."
    asset_classes = allocation.get("byAssetClass", {})
    sectors = allocation.get("bySector", {})
    return f"Nach Anlageklasse: {_map_summary(asset_classes)}. Nach Sektor: {_map_summary(sectors)}."


def _strategy_summary(strategies: list[Any]) -> str:
    if not strategies:
        return "Keine alternativen Strategien berechnet."
    parts = []
    for strategy in strategies:
        if not isinstance(strategy, dict):
            continue
        metrics = strategy.get("metrics", {})
        parts.append(
            f"{strategy.get('name', 'Strategie')}: Rendite {_pct(metrics.get('expectedReturn'))}, "
            f"Volatilitaet {_pct(metrics.get('volatility'))}, Sharpe {_num(metrics.get('sharpeRatio'))}"
        )
    return "; ".join(parts)


def _top_risk_asset(assets: list[Any]) -> str:
    risk_assets = [asset for asset in assets if isinstance(asset, dict) and isinstance(asset.get("riskContribution"), dict)]
    if not risk_assets:
        return "Es liegen keine Risikobeitraege je Position vor."
    top = max(risk_assets, key=lambda asset: float(asset.get("riskContribution", {}).get("percentContribution", 0)))
    contribution = top.get("riskContribution", {}).get("percentContribution")
    return (
        f"Der groesste berechnete Risikobeitrag kommt von {top.get('ticker', 'einer Position')} "
        f"mit etwa {_pct(contribution)} des Portfolio-Volatilitaetsbeitrags."
    )


def _map_summary(values: Any) -> str:
    if not isinstance(values, dict) or not values:
        return "nicht verfuegbar"
    return ", ".join(f"{key} {_pct(value)}" for key, value in values.items())


def _pct(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value * 100:.1f} Prozent"
    return "nicht verfuegbar"


def _num(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.2f}"
    return "nicht verfuegbar"
