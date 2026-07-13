from __future__ import annotations

import json
import os
from typing import Any

import httpx

try:
    from .analysis import DISCLAIMER
    from .market_intelligence import fetch_news_signals
    from .models import GoalPreset, InvestorProfile, RecommendRequest, RecommendResponse
except ImportError:
    from analysis import DISCLAIMER
    from market_intelligence import fetch_news_signals
    from models import GoalPreset, InvestorProfile, RecommendRequest, RecommendResponse


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

TIME_HORIZON_LABELS = {
    "short_term": "kurzfristig",
    "mid_term": "mittelfristig",
    "long_term": "langfristig",
}

RISK_STYLE_LABELS = {
    "defensive": "defensiv",
    "balanced": "ausgewogen",
    "aggressive": "aggressiv",
}

GOAL_LABELS: dict[GoalPreset, str] = {
    "diversify_broadly": "breit diversifizieren",
    "keep_tech_focus": "Tech-Fokus bewusst beibehalten",
    "defensive": "defensiver aufstellen",
    "balanced": "Rendite-Risiko ausbalancieren",
}

SECTOR_IDEA_CATALOG: dict[str, list[dict[str, str]]] = {
    "Health Care": [
        {"ticker": "XLV", "name": "Health Care Select Sector SPDR Fund", "sector": "Health Care", "style": "defensive"},
        {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Health Care", "style": "defensive"},
        {"ticker": "LLY", "name": "Eli Lilly", "sector": "Health Care", "style": "aggressive"},
    ],
    "Financial Services": [
        {"ticker": "XLF", "name": "Financial Select Sector SPDR Fund", "sector": "Financial Services", "style": "defensive"},
        {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Financial Services", "style": "balanced"},
    ],
    "Industrials": [
        {"ticker": "XLI", "name": "Industrial Select Sector SPDR Fund", "sector": "Industrials", "style": "defensive"},
        {"ticker": "CAT", "name": "Caterpillar", "sector": "Industrials", "style": "balanced"},
    ],
    "Consumer Staples": [
        {"ticker": "XLP", "name": "Consumer Staples Select Sector SPDR Fund", "sector": "Consumer Staples", "style": "defensive"},
        {"ticker": "PG", "name": "Procter & Gamble", "sector": "Consumer Staples", "style": "defensive"},
    ],
    "Utilities": [
        {"ticker": "XLU", "name": "Utilities Select Sector SPDR Fund", "sector": "Utilities", "style": "defensive"},
        {"ticker": "NEE", "name": "NextEra Energy", "sector": "Utilities", "style": "balanced"},
    ],
    "Energy": [
        {"ticker": "XLE", "name": "Energy Select Sector SPDR Fund", "sector": "Energy", "style": "balanced"},
        {"ticker": "XOM", "name": "Exxon Mobil", "sector": "Energy", "style": "aggressive"},
    ],
    "Communication Services": [
        {"ticker": "XLC", "name": "Communication Services Select Sector SPDR Fund", "sector": "Communication Services", "style": "balanced"},
        {"ticker": "GOOGL", "name": "Alphabet", "sector": "Communication Services", "style": "aggressive"},
    ],
    "Information Technology": [
        {"ticker": "SMH", "name": "VanEck Semiconductor ETF", "sector": "Information Technology", "style": "aggressive"},
        {"ticker": "MSFT", "name": "Microsoft", "sector": "Information Technology", "style": "balanced"},
    ],
    "Real Estate": [
        {"ticker": "VNQ", "name": "Vanguard Real Estate ETF", "sector": "Real Estate", "style": "defensive"},
        {"ticker": "PLD", "name": "Prologis", "sector": "Real Estate", "style": "balanced"},
    ],
    "International Equities": [
        {"ticker": "IEFA", "name": "iShares Core MSCI EAFE ETF", "sector": "International Equities", "style": "defensive"},
        {"ticker": "VEA", "name": "Vanguard FTSE Developed Markets ETF", "sector": "International Equities", "style": "balanced"},
    ],
}


async def generate_recommendations(request: RecommendRequest) -> RecommendResponse:
    model_name = request.model or OLLAMA_MODEL
    fallback = await build_rule_recommendation_response(request, model_name)
    prompt = _build_prompt(request, fallback)

    try:
        async with httpx.AsyncClient(timeout=4) as client:
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

    parsed = _parse_recommendation_payload(text)
    if not parsed:
        return fallback

    try:
        return RecommendResponse.model_validate(
            {
                **parsed,
                "source": "ollama",
                "model": model_name,
                "disclaimer": DISCLAIMER,
            }
        )
    except Exception:
        return fallback


async def build_rule_recommendation_response(request: RecommendRequest, model_name: str) -> RecommendResponse:
    analysis = request.analysis
    assets = [asset for asset in analysis.get("assets", []) if asset.get("ticker")]
    sector_allocation = analysis.get("sectorAllocation", [])
    metrics = analysis.get("metrics", {})
    optimized_metrics = analysis.get("optimizedMetrics", metrics)
    optimized_weights = analysis.get("optimizedWeights", [asset.get("weight", 0) for asset in assets])
    findings = analysis.get("riskFindings", [])
    news_signals = await fetch_news_signals([str(asset.get("ticker", "")) for asset in assets])

    profile_label = _profile_label(request.investor_profile)
    summary = _build_summary(assets, sector_allocation, findings, request.investor_profile, request.goal_preset)
    profile_fit = _build_profile_fit(metrics, sector_allocation, request.investor_profile)
    analysis_highlights = _build_analysis_highlights(metrics, findings, request.focus_areas)
    sector_insights = _build_sector_insights(sector_allocation, request.goal_preset)
    weight_adjustments = _build_weight_adjustments(assets, optimized_weights, request.goal_preset, request.investor_profile)
    new_ideas = _build_new_ideas(assets, sector_allocation, request.goal_preset, request.investor_profile)
    review_candidates = _build_review_candidates(assets, optimized_weights, findings)
    action_items = _build_action_items(
        request.goal_preset,
        request.goal_note,
        weight_adjustments,
        new_ideas,
        news_signals,
        profile_label,
    )

    return RecommendResponse(
        summary=summary,
        profileFit=profile_fit,
        analysisHighlights=analysis_highlights,
        sectorInsights=sector_insights,
        actionItems=action_items,
        weightAdjustments=weight_adjustments,
        newIdeas=new_ideas,
        reviewCandidates=review_candidates,
        newsSignals=news_signals,
        source="rules",
        model=model_name,
        disclaimer=DISCLAIMER,
    )


def _build_summary(
    assets: list[dict[str, Any]],
    sector_allocation: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    investor_profile: InvestorProfile,
    goal_preset: GoalPreset,
) -> str:
    top_sector = sector_allocation[0] if sector_allocation else None
    top_weight = max((float(asset.get("weight", 0)) for asset in assets), default=0.0)
    top_ticker = next((str(asset.get("ticker")) for asset in assets if float(asset.get("weight", 0)) == top_weight), "das Portfolio")
    opening = (
        f"Dein Portfolio wird aktuell vor allem von {top_ticker} und der Zielsetzung "
        f"'{GOAL_LABELS[goal_preset]}' gepraegt."
    )

    if top_sector and float(top_sector.get("weight", 0)) >= 0.55:
        return (
            f"{opening} Gleichzeitig liegt mit {top_sector.get('sector')} ein klarer Schwerpunkt bei "
            f"{float(top_sector.get('weight', 0)) * 100:.1f} Prozent vor, was fuer ein { _profile_label(investor_profile) }es Profil genauer geprueft werden sollte."
        )

    dominant_finding = next((str(item.get("message")) for item in findings if item.get("type") == "concentration"), None)
    if dominant_finding:
        return f"{opening} {dominant_finding}"

    return (
        f"{opening} Auf Basis der historischen Analyse wirkt das Portfolio solide, aber noch nicht voll auf ein "
        f"{_profile_label(investor_profile)}es Verhalten abgestimmt."
    )


def _build_profile_fit(metrics: dict[str, Any], sector_allocation: list[dict[str, Any]], investor_profile: InvestorProfile) -> str:
    volatility = float(metrics.get("volatility", 0))
    top_sector_weight = float(sector_allocation[0].get("weight", 0)) if sector_allocation else 0.0
    profile_label = _profile_label(investor_profile)

    if investor_profile.risk_style == "defensive":
        if volatility >= 0.20 or top_sector_weight >= 0.45:
            return (
                f"Du hast {profile_label} gewaehlt. Die aktuelle Mischung wirkt dafuer noch etwas konzentriert oder schwankungsstark "
                "und sollte eher breiter verteilt werden."
            )
        return f"Du hast {profile_label} gewaehlt. Die Struktur wirkt bereits vergleichsweise robust, kann aber noch breiter abgestimmt werden."

    if investor_profile.risk_style == "aggressive":
        if top_sector_weight >= 0.45:
            return (
                f"Du hast {profile_label} gewaehlt. Ein Wachstumsschwerpunkt passt grundsaetzlich dazu, "
                "trotzdem bleibt die Konzentration auf wenige Titel ein zentrales Risiko."
            )
        return f"Du hast {profile_label} gewaehlt. Das Portfolio kann fuer diese Zielsetzung noch klarer auf Wachstumsschwerpunkte ausgerichtet werden."

    return (
        f"Du hast {profile_label} gewaehlt. Die KI gewichtet deshalb sowohl Diversifikation als auch Rendite-Risiko-Balance gleichermassen."
    )


def _build_analysis_highlights(
    metrics: dict[str, Any],
    findings: list[dict[str, Any]],
    focus_areas: list[str],
) -> list[str]:
    highlights: list[str] = []
    if "summary" in focus_areas:
        highlights.append(
            f"Die Kennzahlen zeigen aktuell {float(metrics.get('volatility', 0)) * 100:.1f} Prozent Volatilitaet bei einer Sharpe Ratio von {float(metrics.get('sharpeRatio', 0)):.2f}."
        )
    if "diversification" in focus_areas:
        highlights.append(
            f"Der Diversifikationswert liegt bei {float(metrics.get('diversificationScore', 0)):.1f} von 100."
        )
    for finding in findings:
        finding_type = str(finding.get("type"))
        if finding_type == "concentration" and "concentration" in focus_areas:
            highlights.append(str(finding.get("message")))
        elif finding_type in {"correlation", "diversification"} and "diversification" in focus_areas:
            highlights.append(str(finding.get("message")))
        elif finding_type in {"volatility", "risk_return"} and "risk_drivers" in focus_areas:
            highlights.append(str(finding.get("message")))
    return highlights[:4]


def _build_sector_insights(sector_allocation: list[dict[str, Any]], goal_preset: GoalPreset) -> list[str]:
    if not sector_allocation:
        return ["Fuer die aktuelle Auswahl liegen noch keine belastbaren Brancheninformationen vor."]

    insights = [
        f"Die groesste Branchengewichtung liegt bei {sector_allocation[0].get('sector')} mit {float(sector_allocation[0].get('weight', 0)) * 100:.1f} Prozent."
    ]
    represented = [str(item.get("sector")) for item in sector_allocation]
    if len(represented) <= 3:
        insights.append("Es sind bisher nur wenige unterschiedliche Branchen sichtbar, was die Breite des Portfolios begrenzt.")

    if goal_preset == "keep_tech_focus":
        insights.append("Fuer einen bewussten Tech-Fokus sollte die restliche Branchenverteilung trotzdem als Puffer gegen Einzelrisiken dienen.")
    else:
        missing = _pick_target_sectors(sector_allocation, goal_preset, "defensive")[:2]
        if missing:
            insights.append(f"Unterstuetzend waeren ergaenzende Gewichte in {', '.join(missing)}.")
    return insights[:3]


def _build_weight_adjustments(
    assets: list[dict[str, Any]],
    optimized_weights: list[float],
    goal_preset: GoalPreset,
    investor_profile: InvestorProfile,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, asset in enumerate(assets):
        current = float(asset.get("weight", 0))
        suggested = float(optimized_weights[index]) if index < len(optimized_weights) else current
        delta = suggested - current
        if abs(delta) < 0.02:
            continue

        sector = str(asset.get("sector", "Unbekannt"))
        reason = "Die Anpassung naehert sich der berechneten Vergleichsvariante an."
        if delta < 0 and goal_preset != "keep_tech_focus":
            reason = f"Eine geringere Gewichtung von {asset.get('ticker')} reduziert Konzentration in {sector}."
        elif delta > 0 and investor_profile.risk_style == "aggressive":
            reason = f"Das hoehere Gewicht stuetzt einen chancenorientierteren Schwerpunkt in {sector}."
        elif delta > 0:
            reason = f"Das hoehere Gewicht stabilisiert die Verteilung innerhalb von {sector} gegenueber dem bisherigen Portfolio."

        rows.append(
            {
                "ticker": str(asset.get("ticker")),
                "currentWeight": current,
                "suggestedWeight": suggested,
                "reason": reason,
            }
        )

    rows.sort(key=lambda item: abs(float(item["suggestedWeight"]) - float(item["currentWeight"])), reverse=True)
    return rows[:4]


def _build_new_ideas(
    assets: list[dict[str, Any]],
    sector_allocation: list[dict[str, Any]],
    goal_preset: GoalPreset,
    investor_profile: InvestorProfile,
) -> list[dict[str, str]]:
    held_tickers = {str(asset.get("ticker")) for asset in assets}
    risk_style = investor_profile.risk_style
    target_sectors = _pick_target_sectors(sector_allocation, goal_preset, risk_style)

    ideas: list[dict[str, str]] = []
    for sector in target_sectors:
        for candidate in SECTOR_IDEA_CATALOG.get(sector, []):
            if candidate["ticker"] in held_tickers:
                continue
            if risk_style == "defensive" and candidate["style"] == "aggressive":
                continue
            ideas.append(
                {
                    "ticker": candidate["ticker"],
                    "name": candidate["name"],
                    "sector": candidate["sector"],
                    "reason": _build_new_idea_reason(candidate["sector"], goal_preset, investor_profile),
                }
            )
            break
        if len(ideas) >= 3:
            break
    return ideas


def _build_review_candidates(
    assets: list[dict[str, Any]],
    optimized_weights: list[float],
    findings: list[dict[str, Any]],
) -> list[dict[str, str]]:
    reviews: list[dict[str, str]] = []
    for index, asset in enumerate(assets):
        current = float(asset.get("weight", 0))
        suggested = float(optimized_weights[index]) if index < len(optimized_weights) else current
        if current >= 0.25 or current - suggested >= 0.05:
            reviews.append(
                {
                    "ticker": str(asset.get("ticker")),
                    "reason": f"{asset.get('ticker')} praegt das Portfolio mit {current * 100:.1f} Prozent besonders stark und sollte im Kontext der neuen Zielsetzung geprueft werden.",
                }
            )

    if not reviews and findings:
        reviews.append(
            {
                "ticker": str(assets[0].get("ticker")) if assets else "Portfolio",
                "reason": str(findings[0].get("message")),
            }
        )

    return reviews[:3]


def _build_action_items(
    goal_preset: GoalPreset,
    goal_note: str | None,
    weight_adjustments: list[dict[str, Any]],
    new_ideas: list[dict[str, Any]],
    news_signals: list[dict[str, Any]],
    profile_label: str,
) -> list[str]:
    items = [
        f"Vergleiche die aktuelle Struktur mit deinem Profil '{profile_label}' und dem Ziel '{GOAL_LABELS[goal_preset]}'.",
    ]
    if weight_adjustments:
        top = weight_adjustments[0]
        items.append(
            f"Pruefe zuerst die Umgewichtung von {top['ticker']} von {float(top['currentWeight']) * 100:.1f} auf {float(top['suggestedWeight']) * 100:.1f} Prozent."
        )
    if new_ideas:
        ideas = ", ".join(idea["ticker"] for idea in new_ideas[:2])
        items.append(f"Nutze {ideas} als Beispiel, um Branchenluecken gezielt in einer Folgeanalyse zu testen.")
    if goal_note:
        items.append(f"Beruecksichtige deinen Zusatzhinweis: {goal_note.strip()}")
    elif news_signals:
        items.append(f"Pruefe die aktuelle Nachrichtenlage rund um {news_signals[0]['ticker']} vor einer Aenderung besonders aufmerksam.")
    return items[:4]


def _pick_target_sectors(
    sector_allocation: list[dict[str, Any]],
    goal_preset: GoalPreset,
    risk_style: str,
) -> list[str]:
    represented = {str(item.get("sector")): float(item.get("weight", 0)) for item in sector_allocation}

    if goal_preset == "keep_tech_focus":
        priority = ["Information Technology", "Communication Services", "Health Care"]
    elif goal_preset == "defensive" or risk_style == "defensive":
        priority = ["Health Care", "Consumer Staples", "Utilities", "Financial Services", "Industrials"]
    elif goal_preset == "balanced":
        priority = ["Health Care", "Financial Services", "Industrials", "International Equities", "Consumer Staples"]
    else:
        priority = ["Health Care", "Financial Services", "Industrials", "Communication Services", "Real Estate"]

    ranked = sorted(priority, key=lambda sector: represented.get(sector, 0))
    return [sector for sector in ranked if represented.get(sector, 0) < 0.18][:3]


def _build_new_idea_reason(sector: str, goal_preset: GoalPreset, investor_profile: InvestorProfile) -> str:
    if goal_preset == "keep_tech_focus":
        return f"Diese Idee kann den gewuenschten Fokus erhalten und gleichzeitig die Tech-Story breiter innerhalb von {sector} abstuetzen."
    if investor_profile.risk_style == "defensive":
        return f"Diese Idee kann die Branchenbreite in {sector} erhoehen und passt eher zu einem defensiveren Profil."
    if investor_profile.risk_style == "aggressive":
        return f"Diese Idee ergaenzt {sector} als chancenorientierte Beispielposition fuer eine naechste Vergleichsanalyse."
    return f"Diese Idee kann die Branchenabdeckung in {sector} fuer eine ausgewogenere Folgeanalyse erweitern."


def _profile_label(investor_profile: InvestorProfile) -> str:
    return f"{TIME_HORIZON_LABELS[investor_profile.time_horizon]}-{RISK_STYLE_LABELS[investor_profile.risk_style]}"


def _build_prompt(request: RecommendRequest, fallback: RecommendResponse) -> str:
    return f"""
Du bist die KI-Interpretationsebene eines Ausbildungsprojekts fuer Privatanleger.
Du gibst keine Anlageberatung und keine aggressiven Kauf- oder Verkaufssignale.
Du interpretierst ausschliesslich die vorliegenden historischen Kennzahlen, Brancheninformationen und optionalen News-Hinweise.

Nutzerprofil:
- Zeithorizont: {TIME_HORIZON_LABELS[request.investor_profile.time_horizon]}
- Risikotyp: {RISK_STYLE_LABELS[request.investor_profile.risk_style]}
- Ziel: {GOAL_LABELS[request.goal_preset]}
- Zusatzhinweis: {request.goal_note or "kein Zusatzhinweis"}

Analysebasis:
{json.dumps(request.analysis, ensure_ascii=False)}

Regelbasierter Ausgangsentwurf:
{fallback.model_dump_json(by_alias=True, ensure_ascii=False)}

Antworte ausschliesslich als gueltiges JSON-Objekt mit exakt diesen Feldern:
summary, profileFit, analysisHighlights, sectorInsights, actionItems, weightAdjustments, newIdeas, reviewCandidates, newsSignals

Regeln:
- keine Markdown-Formatierung
- keine weiteren Felder
- keine Prognosen
- Gewichtungen als Dezimalwerte zwischen 0 und 1
- News nur aus newsSignals, nichts erfinden
- newIdeas maximal 3, reviewCandidates maximal 3
""".strip()


def _parse_recommendation_payload(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if not cleaned:
        return None

    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None
