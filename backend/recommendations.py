from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
import numpy as np

from .analysis import DISCLAIMER, optimize_portfolio
from .market_intelligence import fetch_news_signals, is_news_configured
from .models import GoalPreset, InvestorProfile, RecommendRequest, RecommendResponse


logger = logging.getLogger(__name__)


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "90"))
# CLOUD_* is provider-neutral. The OPENAI_* names remain supported for existing setups.
_legacy_cloud_key = os.getenv("OPENAI_API_KEY", "")
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY") or _legacy_cloud_key
CLOUD_BASE_URL = (
    os.getenv("CLOUD_BASE_URL")
    or (os.getenv("OPENAI_BASE_URL") if _legacy_cloud_key else None)
    or "https://integrate.api.nvidia.com"
).rstrip("/")
CLOUD_MODEL = (
    os.getenv("CLOUD_MODEL")
    or (os.getenv("OPENAI_MODEL") if _legacy_cloud_key else None)
    or "nvidia/nemotron-3-nano-30b-a3b"
)
CLOUD_TIMEOUT = float(os.getenv("CLOUD_TIMEOUT", "45"))


def lmstudio_candidate_urls() -> list[str]:
    """Mögliche LM-Studio-Adressen: .env zuerst, dann Standard-Ports."""
    candidates: list[str] = []
    for raw in (os.getenv("LMSTUDIO_URL", ""), os.getenv("LMSTUDIO_URLS", "")):
        for item in raw.split(","):
            item = item.strip().rstrip("/")
            if item and item not in candidates:
                candidates.append(item)
    for default in ("http://localhost:1234", "http://127.0.0.1:1234"):
        if default not in candidates:
            candidates.append(default)
    return candidates

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

GOAL_OPTIMIZATION: dict[GoalPreset, dict[str, object]] = {
    "diversify_broadly": {"objective": "max_diversification", "max_weight": 0.20},
    "keep_tech_focus": {"objective": "max_sharpe", "max_weight": 0.40},
    "defensive": {"objective": "min_volatility", "max_weight": 0.25},
    "balanced": {"objective": "max_sharpe", "max_weight": 0.30},
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
    """Provider-Auswahl durch den Nutzer:

    - "local":  LM Studio -> Ollama -> regelbasierter Fallback (privat, nichts verlässt den Rechner)
    - "cloud":  OpenAI-kompatible Cloud-API -> regelbasierter Fallback (z. B. für iPad/schwache Hardware)
    - "auto":   erst lokal, dann Cloud, dann Fallback
    """
    preference = request.llm_preference
    fallback_model = request.model or LMSTUDIO_MODEL or OLLAMA_MODEL
    fallback = await build_rule_recommendation_response(request, fallback_model)
    prompt = _build_prompt(request, fallback, detail="small")
    cloud_prompt = _build_prompt(request, fallback, detail="large")
    attempted_backends: list[str] = []
    fallback_reason = "no_backend_reachable"

    if preference in ("auto", "local"):
        attempted_backends.append("LM Studio")
        lmstudio_result, lmstudio_status = await _call_lmstudio_with_status(prompt, request.model)
        if lmstudio_result is not None:
            text, model_used = lmstudio_result
            validated = _validate_llm_response(text, "lmstudio", model_used, fallback)
            if validated is not None:
                return validated
            fallback_reason = "invalid_response" if _parse_recommendation_payload(text) is None else "validation_failed"
        elif lmstudio_status in {"timeout", "invalid_response"}:
            fallback_reason = lmstudio_status

        ollama_model = request.model or OLLAMA_MODEL
        attempted_backends.append("Ollama")
        ollama_text, ollama_status = await _call_ollama_with_status(prompt, ollama_model)
        if ollama_text is not None:
            validated = _validate_llm_response(ollama_text, "ollama", ollama_model, fallback)
            if validated is not None:
                return validated
            fallback_reason = "invalid_response" if _parse_recommendation_payload(ollama_text) is None else "validation_failed"
        elif ollama_status in {"timeout", "invalid_response"}:
            fallback_reason = ollama_status

    if preference in ("auto", "cloud"):
        attempted_backends.append("Cloud-API")
        cloud_result, cloud_status = await _call_cloud_with_status(cloud_prompt, request.model)
        if cloud_result is not None:
            text, model_used = cloud_result
            validated = _validate_llm_response(text, "cloud", model_used, fallback)
            if validated is not None:
                return validated
            fallback_reason = "invalid_response" if _parse_recommendation_payload(text) is None else "validation_failed"
        elif cloud_status in {"timeout", "invalid_response"}:
            fallback_reason = cloud_status

    return fallback.model_copy(
        update={
            "fallback_reason": fallback_reason,
            "attempted_backends": attempted_backends,
        }
    )


async def _call_cloud(prompt: str, requested_model: str | None) -> tuple[str, str] | None:
    result, _ = await _call_cloud_with_status(prompt, requested_model)
    return result


async def _call_cloud_with_status(prompt: str, requested_model: str | None) -> tuple[tuple[str, str] | None, str]:
    """OpenAI-kompatible Cloud-API mit maschinenlesbarem Fehlerstatus."""
    if not CLOUD_API_KEY:
        return None, "not_configured"
    model_name = requested_model or CLOUD_MODEL
    try:
        async with httpx.AsyncClient(timeout=CLOUD_TIMEOUT) as client:
            request_body = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Du bist die Interpretationsebene eines Portfolio-Analyse-Tools. "
                            "Antworte ausschließlich mit einem gültigen JSON-Objekt, ohne Markdown."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 700,
            }
            if model_name == "moonshotai/kimi-k3":
                # Kimi K3 defaults to max reasoning, which can exceed the cloud timeout
                # for this compact JSON interpretation task.
                request_body["reasoning_effort"] = "low"
                request_body["max_tokens"] = 420
            elif model_name == "nvidia/nemotron-3-nano-30b-a3b":
                # Nemotron defaults to an internal reasoning trace; the app needs the
                # final structured JSON directly for reliable validation.
                request_body["chat_template_kwargs"] = {"enable_thinking": False}
            response = await client.post(
                f"{CLOUD_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {CLOUD_API_KEY}"},
                json=request_body,
            )
            response.raise_for_status()
            choices = response.json().get("choices", [])
            if not choices:
                return None, "invalid_response"
            content = choices[0].get("message", {}).get("content", "")
            return ((content, model_name), "ok") if content else (None, "invalid_response")
    except httpx.TimeoutException:
        return None, "timeout"
    except httpx.HTTPStatusError as exc:
        logger.warning("Cloud API rejected recommendation request with HTTP %s", exc.response.status_code)
        return None, "unreachable"
    except httpx.RequestError as exc:
        logger.warning("Cloud API request failed: %s", type(exc).__name__)
        return None, "unreachable"
    except Exception as exc:
        logger.exception("Cloud recommendation call failed: %s", type(exc).__name__)
        return None, "unreachable"


def _validate_llm_response(
    text: str,
    source: str,
    model_name: str,
    fallback: RecommendResponse,
) -> RecommendResponse | None:
    """Uebernimmt nur die Textfelder der KI; strukturierte Listen bleiben regelbasiert.

    Das macht die Ausgabe robust gegen Halluzination kleiner Modelle: Zahlen,
    Gewichtungsvorschläge und Ideen stammen immer aus der Berechnung.
    """
    parsed = _parse_recommendation_payload(text)
    if not parsed:
        return None

    updates: dict[str, Any] = {}
    for field in ("summary", "profileFit"):
        value = parsed.get(field)
        if isinstance(value, str) and 20 <= len(value.strip()) <= 900:
            updates[field] = value.strip()
    for field in ("analysisHighlights", "sectorInsights", "actionItems"):
        value = parsed.get(field)
        if isinstance(value, list):
            items = [item.strip() for item in value if isinstance(item, str) and 10 <= len(item.strip()) <= 400]
            if items:
                updates[field] = items[:4]

    if not updates:
        return None

    try:
        return RecommendResponse.model_validate(
            {
                **fallback.model_dump(by_alias=True),
                **updates,
                "source": source,
                "model": model_name,
                "disclaimer": DISCLAIMER,
            }
        )
    except Exception:
        return None


async def _call_lmstudio(prompt: str, requested_model: str | None) -> tuple[str, str] | None:
    result, _ = await _call_lmstudio_with_status(prompt, requested_model)
    return result


async def _call_lmstudio_with_status(prompt: str, requested_model: str | None) -> tuple[tuple[str, str] | None, str]:
    """OpenAI-kompatible LM Studio API. Probiert alle Kandidaten-URLs durch."""
    statuses: list[str] = []
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT, trust_env=False) as client:
        for base_url in lmstudio_candidate_urls():
            try:
                models_response = await client.get(f"{base_url}/v1/models", timeout=2.5)
                models_response.raise_for_status()
                loaded = models_response.json().get("data", [])
            except httpx.TimeoutException:
                statuses.append("timeout")
                continue
            except Exception:
                statuses.append("unreachable")
                continue

            model_name = requested_model or LMSTUDIO_MODEL
            if not model_name:
                if not loaded:
                    continue
                model_name = str(loaded[0].get("id", ""))
                if not model_name:
                    continue

            try:
                response = await client.post(
                    f"{base_url}/v1/chat/completions",
                    json={
                        "model": model_name,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Du bist die Interpretationsebene eines Portfolio-Analyse-Tools. "
                                    "Antworte ausschließlich mit einem gültigen JSON-Objekt, ohne Markdown."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 700,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                choices = response.json().get("choices", [])
                if not choices:
                    statuses.append("invalid_response")
                    continue
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    return (content, model_name), "ok"
                statuses.append("invalid_response")
            except httpx.TimeoutException:
                statuses.append("timeout")
                continue
            except Exception:
                statuses.append("unreachable")
                continue
    return None, _combined_provider_status(statuses)


async def _call_ollama(prompt: str, model_name: str) -> str | None:
    result, _ = await _call_ollama_with_status(prompt, model_name)
    return result


async def _call_ollama_with_status(prompt: str, model_name: str) -> tuple[str | None, str]:
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT, trust_env=False) as client:
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
            return (text, "ok") if text else (None, "invalid_response")
    except httpx.TimeoutException:
        return None, "timeout"
    except Exception:
        return None, "unreachable"


def _combined_provider_status(statuses: list[str]) -> str:
    if statuses and all(status == "timeout" for status in statuses):
        return "timeout"
    if "invalid_response" in statuses and not any(status == "ok" for status in statuses):
        return "invalid_response"
    return "unreachable"


async def build_rule_recommendation_response(request: RecommendRequest, model_name: str) -> RecommendResponse:
    analysis = request.analysis
    assets = [asset for asset in analysis.get("assets", []) if asset.get("ticker")]
    sector_allocation = analysis.get("sectorAllocation", [])
    metrics = analysis.get("metrics", {})
    optimized_metrics = analysis.get("optimizedMetrics", metrics)
    optimized_weights = analysis.get("optimizedWeights", [asset.get("weight", 0) for asset in assets])
    findings = analysis.get("riskFindings", [])
    try:
        news_signals = await fetch_news_signals([str(asset.get("ticker", "")) for asset in assets])
    except Exception:
        news_signals = []
    profile_weights, optimization_basis = _profile_optimized_weights(request, assets, optimized_weights)

    profile_label = _profile_label(request.investor_profile)
    summary = _build_summary(assets, sector_allocation, findings, request.investor_profile, request.goal_preset)
    profile_fit = _build_profile_fit(metrics, sector_allocation, request.investor_profile)
    analysis_highlights = _build_analysis_highlights(metrics, findings, request.focus_areas)
    sector_insights = _build_sector_insights(sector_allocation, request.goal_preset)
    weight_adjustments = _build_weight_adjustments(
        assets,
        profile_weights,
        request.goal_preset,
        request.investor_profile,
        str(optimization_basis["objective"]),
    )
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
        optimizationBasis=optimization_basis,
        newsAvailable=is_news_configured(),
    )


def _optimization_inputs(analysis: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, list[str]] | None:
    """Liest Berechnungsdaten für die Optimierung, ohne sie in den LLM-Prompt zu geben."""
    assets = [asset for asset in analysis.get("assets", []) if isinstance(asset, dict)]
    tickers = [str(asset.get("ticker", "")).strip() for asset in assets]
    if len(tickers) < 2 or any(not ticker for ticker in tickers):
        return None

    try:
        mean_returns = np.asarray([float(asset["expectedReturn"]) for asset in assets], dtype=float)
        covariance = np.asarray(analysis["covarianceMatrix"], dtype=float)
    except (KeyError, TypeError, ValueError):
        return None

    if (
        mean_returns.shape != (len(tickers),)
        or covariance.shape != (len(tickers), len(tickers))
        or not np.isfinite(mean_returns).all()
        or not np.isfinite(covariance).all()
        or np.any(np.diag(covariance) <= 0)
    ):
        return None
    return mean_returns, (covariance + covariance.T) / 2, tickers


def _profile_optimized_weights(
    request: RecommendRequest,
    assets: list[dict[str, Any]],
    fallback_weights: list[float],
) -> tuple[list[float], dict[str, Any]]:
    config = GOAL_OPTIMIZATION[request.goal_preset]
    objective = str(config["objective"])
    if request.investor_profile.time_horizon == "short_term" and objective == "max_sharpe":
        objective = "min_volatility"

    base_max_weight = float(config["max_weight"])
    risk_multiplier = {"defensive": 0.8, "balanced": 1.0, "aggressive": 1.3}[request.investor_profile.risk_style]
    max_weight = min(0.5, base_max_weight * risk_multiplier)
    asset_count = len(assets)
    if asset_count:
        max_weight = max(max_weight, 1 / asset_count)

    inputs = _optimization_inputs(request.analysis)
    fallback = [float(value) for value in fallback_weights]
    if inputs is None:
        return fallback, {
            "objective": "fallback",
            "maxWeight": round(max_weight, 4),
            "description": "Die Analyse enthielt keine plausible Kovarianzmatrix; die vorhandene Vergleichsvariante bleibt aktiv.",
        }

    mean_returns, covariance, _ = inputs
    try:
        weights = optimize_portfolio(
            mean_returns,
            covariance,
            float(request.analysis.get("riskFreeRate", 0.025)),
            objective,
            max_weight,
        )
    except (ValueError, TypeError, FloatingPointError):
        return fallback, {
            "objective": "fallback",
            "maxWeight": round(max_weight, 4),
            "description": "Die profilbezogene Optimierung konnte nicht berechnet werden; die vorhandene Vergleichsvariante bleibt aktiv.",
        }

    objective_labels = {
        "max_sharpe": "historisches Max-Sharpe-Ziel",
        "min_volatility": "historische Minimierung der Volatilität",
        "max_diversification": "historische Maximierung des Diversifikationsquotienten",
    }
    return [float(value) for value in weights], {
        "objective": objective,
        "maxWeight": round(max_weight, 4),
        "description": f"Profilbezogene Optimierung: {objective_labels[objective]}, maximal {max_weight * 100:.1f} Prozent je Position.",
    }


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
        f"'{GOAL_LABELS[goal_preset]}' geprägt."
    )

    if top_sector and float(top_sector.get("weight", 0)) >= 0.55:
        return (
            f"{opening} Gleichzeitig liegt mit {top_sector.get('sector')} ein klarer Schwerpunkt bei "
            f"{float(top_sector.get('weight', 0)) * 100:.1f} Prozent vor, was für ein { _profile_label(investor_profile) }es Profil genauer geprüft werden sollte."
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
                f"Du hast {profile_label} gewählt. Die aktuelle Mischung wirkt dafür noch etwas konzentriert oder schwankungsstark "
                "und sollte eher breiter verteilt werden."
            )
        return f"Du hast {profile_label} gewählt. Die Struktur wirkt bereits vergleichsweise robust, kann aber noch breiter abgestimmt werden."

    if investor_profile.risk_style == "aggressive":
        if top_sector_weight >= 0.45:
            return (
                f"Du hast {profile_label} gewählt. Ein Wachstumsschwerpunkt passt grundsätzlich dazu, "
                "trotzdem bleibt die Konzentration auf wenige Titel ein zentrales Risiko."
            )
        return f"Du hast {profile_label} gewählt. Das Portfolio kann für diese Zielsetzung noch klarer auf Wachstumsschwerpunkte ausgerichtet werden."

    return (
        f"Du hast {profile_label} gewählt. Die KI gewichtet deshalb sowohl Diversifikation als auch Rendite-Risiko-Balance gleichermaßen."
    )


def _build_analysis_highlights(
    metrics: dict[str, Any],
    findings: list[dict[str, Any]],
    focus_areas: list[str],
) -> list[str]:
    highlights: list[str] = []
    if "summary" in focus_areas:
        highlights.append(
            f"Die Kennzahlen zeigen aktuell {float(metrics.get('volatility', 0)) * 100:.1f} Prozent Volatilität bei einer Sharpe Ratio von {float(metrics.get('sharpeRatio', 0)):.2f}."
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
        return ["Für die aktuelle Auswahl liegen noch keine belastbaren Brancheninformationen vor."]

    insights = [
        f"Die größte Branchengewichtung liegt bei {sector_allocation[0].get('sector')} mit {float(sector_allocation[0].get('weight', 0)) * 100:.1f} Prozent."
    ]
    represented = [str(item.get("sector")) for item in sector_allocation]
    if len(represented) <= 3:
        insights.append("Es sind bisher nur wenige unterschiedliche Branchen sichtbar, was die Breite des Portfolios begrenzt.")

    if goal_preset == "keep_tech_focus":
        insights.append("Für einen bewussten Tech-Fokus sollte die restliche Branchenverteilung trotzdem als Puffer gegen Einzelrisiken dienen.")
    else:
        missing = _pick_target_sectors(sector_allocation, goal_preset, "defensive")[:2]
        if missing:
            insights.append(f"Unterstützend wären ergänzende Gewichte in {', '.join(missing)}.")
    return insights[:3]


def _build_weight_adjustments(
    assets: list[dict[str, Any]],
    optimized_weights: list[float],
    goal_preset: GoalPreset,
    investor_profile: InvestorProfile,
    objective: str = "max_sharpe",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, asset in enumerate(assets):
        current = float(asset.get("weight", 0))
        suggested = float(optimized_weights[index]) if index < len(optimized_weights) else current
        delta = suggested - current
        if abs(delta) < 0.02:
            continue

        sector = str(asset.get("sector", "Unbekannt"))
        reason = "Die Anpassung nähert sich der berechneten Vergleichsvariante an."
        if objective == "min_volatility":
            reason = "Diese Anpassung senkt die erwartete Schwankung des Gesamtportfolios."
        elif objective == "max_diversification":
            reason = "Diese Anpassung verbessert den berechneten Diversifikationsquotienten und die Streuung."
        elif delta < 0 and goal_preset != "keep_tech_focus":
            reason = f"Eine geringere Gewichtung von {asset.get('ticker')} reduziert Konzentration in {sector}."
        elif delta > 0 and investor_profile.risk_style == "aggressive":
            reason = f"Das höhere Gewicht stützt einen chancenorientierteren Schwerpunkt in {sector}."
        elif delta > 0:
            reason = f"Das höhere Gewicht stabilisiert die Verteilung innerhalb von {sector} gegenüber dem bisherigen Portfolio."

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
                    "reason": f"{asset.get('ticker')} prägt das Portfolio mit {current * 100:.1f} Prozent besonders stark und sollte im Kontext der neuen Zielsetzung geprüft werden.",
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
            f"Prüfe zuerst die Umgewichtung von {top['ticker']} von {float(top['currentWeight']) * 100:.1f} auf {float(top['suggestedWeight']) * 100:.1f} Prozent."
        )
    if new_ideas:
        ideas = ", ".join(idea["ticker"] for idea in new_ideas[:2])
        items.append(f"Nutze {ideas} als Beispiel, um Branchenlücken gezielt in einer Folgeanalyse zu testen.")
    if goal_note:
        items.append(f"Berücksichtige deinen Zusatzhinweis: {goal_note.strip()}")
    elif news_signals:
        items.append(f"Prüfe die aktuelle Nachrichtenlage rund um {news_signals[0]['ticker']} vor einer Aenderung besonders aufmerksam.")
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
        return f"Diese Idee kann den gewünschten Fokus erhalten und gleichzeitig die Tech-Story breiter innerhalb von {sector} abstützen."
    if investor_profile.risk_style == "defensive":
        return f"Diese Idee kann die Branchenbreite in {sector} erhöhen und passt eher zu einem defensiveren Profil."
    if investor_profile.risk_style == "aggressive":
        return f"Diese Idee ergänzt {sector} als chancenorientierte Beispielposition für eine nächste Vergleichsanalyse."
    return f"Diese Idee kann die Branchenabdeckung in {sector} für eine ausgewogenere Folgeanalyse erweitern."


def _profile_label(investor_profile: InvestorProfile) -> str:
    return f"{TIME_HORIZON_LABELS[investor_profile.time_horizon]}-{RISK_STYLE_LABELS[investor_profile.risk_style]}"


def _compact_analysis(analysis: dict[str, Any], detail: str = "small") -> dict[str, Any]:
    """Reduziert die Analyse auf das, was die KI zum Formulieren braucht.

    detail="small": für lokale Modelle mit 4k-8k Kontext (~1k Tokens).
    detail="large": für Cloud-Modelle mit großem Kontext - zusätzlich volle
    Korrelationsmatrix, monatlich verdichtete Performance und Frontier-Eckpunkte.
    Rohe Tageskurse bekommt kein Modell: sie verbessern die Erklärung nicht,
    kosten aber Tokens und erhöhen das Halluzinationsrisiko.
    """
    assets = [
        {
            "ticker": a.get("ticker"),
            "name": a.get("name"),
            "sector": a.get("sector"),
            "weight": round(float(a.get("weight", 0)), 4),
            "expectedReturn": round(float(a.get("expectedReturn", 0)), 4),
            "volatility": round(float(a.get("volatility", 0)), 4),
        }
        for a in analysis.get("assets", [])
    ]

    metrics_keys = (
        "expectedReturn",
        "volatility",
        "sharpeRatio",
        "valueAtRisk",
        "diversificationScore",
        "effectiveHoldings",
        "diversificationRatio",
        "valueAtRiskHorizonDays",
        "annualizedReturnGeometric",
    )

    def slim_metrics(source: dict[str, Any]) -> dict[str, Any]:
        return {k: round(float(source.get(k, 0)), 4) for k in metrics_keys}

    # Nur die stärksten Korrelationen statt der ganzen Matrix
    high_correlations: list[dict[str, Any]] = []
    matrix = analysis.get("correlationMatrix", {})
    tickers = matrix.get("tickers", [])
    values = matrix.get("values", [])
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            try:
                value = float(values[i][j])
            except (IndexError, TypeError, ValueError):
                continue
            if abs(value) >= 0.75:
                high_correlations.append({"pair": f"{tickers[i]}/{tickers[j]}", "correlation": round(value, 2)})
    high_correlations.sort(key=lambda item: -abs(item["correlation"]))

    compact: dict[str, Any] = {
        "mode": analysis.get("mode"),
        "zeitraum": f"{analysis.get('startDate')} bis {analysis.get('endDate')}",
        "assets": assets,
        "metrics": slim_metrics(analysis.get("metrics", {})),
        "optimizedMetrics": slim_metrics(analysis.get("optimizedMetrics", {})),
        "optimizedWeights": [round(float(w), 4) for w in analysis.get("optimizedWeights", [])],
        "sectorAllocation": [
            {"sector": s.get("sector"), "weight": round(float(s.get("weight", 0)), 4)}
            for s in analysis.get("sectorAllocation", [])
        ],
        "riskFindings": [
            {"type": f.get("type"), "severity": f.get("severity"), "message": f.get("message")}
            for f in analysis.get("riskFindings", [])
        ],
        "hoheKorrelationen": high_correlations[:4],
    }

    return compact


# Textfelder, die die KI formulieren soll - strukturierte Listen bleiben regelbasiert.
LLM_TEXT_FIELDS = ("summary", "profileFit", "analysisHighlights", "sectorInsights", "actionItems")


def _build_prompt(request: RecommendRequest, fallback: RecommendResponse, detail: str = "small") -> str:
    compact = _compact_analysis(request.analysis, detail)
    draft = {
        "summary": fallback.summary,
        "profileFit": fallback.profile_fit,
        "analysisHighlights": fallback.analysis_highlights,
        "sectorInsights": fallback.sector_insights,
        "actionItems": fallback.action_items,
    }
    return f"""Du erklärst Privatanlegern die Ergebnisse einer regelbasierten Portfolioanalyse.
Du gibst keine Anlageberatung, keine Kauf-/Verkaufssignale, keine Prognosen.
Nutze ausschließlich die folgenden berechneten Werte. Erfinde keine Zahlen.

Nutzerprofil: {TIME_HORIZON_LABELS[request.investor_profile.time_horizon]}, {RISK_STYLE_LABELS[request.investor_profile.risk_style]}, Ziel: {GOAL_LABELS[request.goal_preset]}.
Zusatzhinweis: {request.goal_note or "keiner"}

Berechnete Analyse (Gewichte/Renditen/Volatilität als Dezimalzahlen):
{json.dumps(compact, ensure_ascii=False)}

Vorformulierter Entwurf (verbessere Klarheit und Verständlichkeit, bleibe inhaltlich treu):
{json.dumps(draft, ensure_ascii=False)}

Antworte NUR mit einem JSON-Objekt mit exakt diesen Feldern:
{{"summary": string, "profileFit": string, "analysisHighlights": string[], "sectorInsights": string[], "actionItems": string[]}}
Regeln: kein Markdown, keine weiteren Felder, Deutsch, jede Aussage muss sich auf eine der obigen Zahlen stützen, maximal 4 Einträge pro Liste.""".strip()


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
