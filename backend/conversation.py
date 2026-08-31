from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from .analysis import DISCLAIMER
from .models import AskRequest, AskResponse, ChatMessage, GoalChatRequest, GoalChatResponse, WizardProposal
from .recommendations import OLLAMA_MODEL, _call_cloud_with_status, _call_ollama


MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARS = 8000
MAX_RESPONSE_CHARS = 1500
GENERIC_UPPERCASE_TERMS = {"ETF", "EUR", "USD", "VAR", "HHI", "CAGR", "API", "KI", "LLM"}
TRADE_LANGUAGE = (
    "kaufen sie",
    "kaufe",
    "verkaufe",
    "verkaufen sie",
    "jetzt einsteigen",
    "kursziel",
    "wird steigen",
    "wird fallen",
)


def build_digest(analysis: dict[str, Any]) -> dict[str, Any]:
    """Verdichtet eine Analyse für Erklärungen und lässt Roh-/Ballastdaten weg."""
    assets = []
    for asset in analysis.get("assets", []):
        if not isinstance(asset, dict):
            continue
        assets.append(
            {
                "ticker": asset.get("ticker"),
                "name": asset.get("name"),
                "sector": asset.get("sector"),
                "weight": asset.get("weight"),
                "expectedReturn": asset.get("expectedReturn"),
                "volatility": asset.get("volatility"),
                "annualizedReturnGeometric": asset.get("annualizedReturnGeometric"),
            }
        )
    metric_keys = (
        "expectedReturn",
        "annualizedReturnGeometric",
        "volatility",
        "sharpeRatio",
        "valueAtRisk",
        "valueAtRiskHorizonDays",
        "valueAtRiskMethod",
        "diversificationScore",
        "effectiveHoldings",
        "diversificationRatio",
    )

    def select_metrics(source: Any) -> dict[str, Any]:
        source = source if isinstance(source, dict) else {}
        return {key: source[key] for key in metric_keys if key in source}

    return {
        "mode": analysis.get("mode"),
        "dataSource": analysis.get("dataSource"),
        "startDate": analysis.get("startDate"),
        "endDate": analysis.get("endDate"),
        "riskFreeRate": analysis.get("riskFreeRate"),
        "varConfidence": analysis.get("varConfidence"),
        "assets": assets,
        "metrics": select_metrics(analysis.get("metrics")),
        "optimizedMetrics": select_metrics(analysis.get("optimizedMetrics")),
        "optimizedWeights": analysis.get("optimizedWeights", []),
        "sectorAllocation": analysis.get("sectorAllocation", []),
        "riskFindings": analysis.get("riskFindings", []),
        "recommendations": analysis.get("recommendations", []),
    }


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _trim_history(messages: list[ChatMessage]) -> list[ChatMessage]:
    selected = list(messages[-MAX_HISTORY_MESSAGES:])
    total = sum(len(message.content) for message in selected)
    while selected and total > MAX_HISTORY_CHARS:
        removed = selected.pop(0)
        total -= len(removed.content)
    return selected


def build_rule_goal_proposal(
    messages: list[ChatMessage],
    portfolio_preview: Any = None,
) -> tuple[WizardProposal | None, str, str | None, str]:
    history = _trim_history(messages)
    combined = " ".join(message.content for message in history if message.role == "user")
    normalized = _normalize_text(combined)
    latest = history[-1].content[:600] if history else ""

    defensive_terms = ("sicher", "sicherheit", "vorsichtig", "defensiv", "schwankung", "verlust", "ruhig", "absichern", "rente")
    aggressive_terms = ("wachstum", "chance", "rendite maximieren", "offensiv", "aggressiv", "tech", "dynamisch")
    short_terms = ("kurzfristig", "naechstes jahr", "bald", "kurz")
    long_terms = ("langfristig", "altersvorsorge", "rente", "jahrzehnt", "10 jahre", "20 jahre", "sparplan")
    defensive_goal_terms = ("absichern", "weniger risiko", "schwankung reduzieren", "stabil")
    tech_goal_terms = ("tech behalten", "technologie", "wachstumswerte behalten")
    diversify_goal_terms = ("streuen", "diversifizieren", "breiter", "verteilen", "klumpenrisiko")

    def count(terms: tuple[str, ...]) -> int:
        return sum(normalized.count(term) for term in terms)

    defensive_score = count(defensive_terms)
    aggressive_score = count(aggressive_terms)
    if defensive_score >= aggressive_score and defensive_score > 0:
        risk_style = "defensive"
    elif aggressive_score > 0:
        risk_style = "aggressive"
    else:
        risk_style = "balanced"

    long_score = count(long_terms)
    short_score = count(short_terms)
    if long_score >= short_score and long_score > 0:
        time_horizon = "long_term"
    elif short_score > 0:
        time_horizon = "short_term"
    else:
        time_horizon = "mid_term"

    goal_scores = {
        "defensive": count(defensive_goal_terms),
        "keep_tech_focus": count(tech_goal_terms),
        "diversify_broadly": count(diversify_goal_terms),
        "balanced": 0,
    }
    max_goal_score = max(goal_scores.values())
    goal_preset = max((goal for goal, score in goal_scores.items() if score == max_goal_score), key=lambda goal: {"defensive": 3, "diversify_broadly": 2, "keep_tech_focus": 1, "balanced": 0}[goal])
    if max_goal_score == 0:
        goal_preset = "defensive" if risk_style == "defensive" else "balanced"

    focus_areas = ["summary", "sector", "concentration", "diversification", "risk_drivers"]
    focus_hits: list[str] = []
    if re.search(r"branche|sektor", normalized):
        focus_hits.append("sector")
    if re.search(r"konzent|klump", normalized):
        focus_hits.append("concentration")
    if re.search(r"divers|streu|breit", normalized):
        focus_hits.append("diversification")
    if re.search(r"risiko|schwank|verlust", normalized):
        focus_hits.append("risk_drivers")
    focus_areas = focus_hits + [area for area in focus_areas if area not in focus_hits]

    signal_count = sum(
        [
            int(defensive_score > 0 or aggressive_score > 0),
            int(long_score > 0 or short_score > 0),
            int(max_goal_score > 0),
            int(bool(focus_hits)),
        ]
    )
    confidence = "high" if signal_count >= 3 else "medium" if signal_count >= 1 else "low"
    labels = {
        "short_term": "kurzfristig",
        "mid_term": "mittelfristig",
        "long_term": "langfristig",
        "defensive": "defensiv",
        "balanced": "ausgewogen",
        "aggressive": "aggressiv",
        "defensive_goal": "defensiver Absicherung",
        "keep_tech_focus": "beibehaltenem Tech-Fokus",
        "diversify_broadly": "breiter Streuung",
    }
    if confidence == "low":
        return None, "Ich habe noch nicht genug Angaben, um dein Ziel zuverlässig einzuordnen.", "Geht es dir eher um weniger Schwankung, höhere Renditechancen oder eine breitere Streuung?", confidence

    goal_label = {"defensive": labels["defensive_goal"], "keep_tech_focus": labels["keep_tech_focus"], "diversify_broadly": labels["diversify_broadly"], "balanced": "ausgewogenem Rendite-Risiko"}[goal_preset]
    reasoning = f"Die Angaben sprechen für ein {labels[time_horizon]}es, {labels[risk_style]}es Profil mit dem Ziel {goal_label}."
    proposal = WizardProposal(
        focusAreas=focus_areas,
        timeHorizon=time_horizon,
        riskStyle=risk_style,
        goalPreset=goal_preset,
        goalNote=latest,
        reasoning=reasoning,
    )
    reply = f"Ich habe daraus ein {labels[time_horizon]}es, {labels[risk_style]}es Profil mit dem Ziel {goal_label} abgeleitet. Passt das so, oder ist dir ein anderer Schwerpunkt wichtiger?"
    return proposal, reply, None, confidence


def _build_goal_prompt(request: GoalChatRequest) -> str:
    history = _trim_history(request.messages)
    messages = [{"role": message.role, "content": message.content} for message in history]
    preview = None
    if request.portfolio_preview is not None:
        preview = request.portfolio_preview.model_dump(by_alias=True)
    return (
        "Du hilfst einem Privatanleger, sein Analyseziel zu präzisieren. Keine Anlageberatung, "
        "keine Kauf- oder Verkaufsempfehlungen, keine Prognosen. Stelle höchstens eine Rückfrage. "
        "Antworte auf Deutsch, höchstens 120 Wörter im Feld reply und ausschließlich als JSON. "
        "Wenn die Angaben ausreichen, fülle proposal vollständig aus, sonst null.\n"
        f"Nachrichten: {json.dumps(messages, ensure_ascii=False)}\n"
        f"Portfolio-Vorschau: {json.dumps(preview, ensure_ascii=False)}\n"
        'JSON-Felder: reply, followUpQuestion, proposal, confidence. In proposal: focusAreas, timeHorizon, riskStyle, goalPreset, goalNote, reasoning.'
    )


async def generate_goal_chat_reply(request: GoalChatRequest) -> GoalChatResponse:
    rule_proposal, rule_reply, rule_question, confidence = build_rule_goal_proposal(request.messages, request.portfolio_preview)
    fallback_reason = "no_backend_reachable"
    try:
        model_text = await _call_ollama(_build_goal_prompt(request), OLLAMA_MODEL)
    except Exception:
        model_text = None
    if model_text:
        parsed = _parse_json_object(model_text)
        if parsed and isinstance(parsed.get("reply"), str):
            try:
                model_reply = str(parsed["reply"])
                allowed_tickers = set(request.portfolio_preview.tickers) if request.portfolio_preview else set()
                if not _is_safe_model_answer(model_reply, allowed_tickers):
                    raise ValueError("Die Modellantwort enthält unzulässige Handels- oder Tickerangaben.")
                proposal = WizardProposal.model_validate(parsed["proposal"]) if parsed.get("proposal") else None
                return GoalChatResponse(
                    reply=_limit_and_disclaim(model_reply),
                    followUpQuestion=parsed.get("followUpQuestion"),
                    proposal=proposal,
                    confidence=parsed.get("confidence", confidence),
                    source="ollama",
                    fallbackReason=None,
                    disclaimer=DISCLAIMER,
                )
            except Exception:
                fallback_reason = "validation_failed"
        else:
            fallback_reason = "invalid_response"
    return GoalChatResponse(
        reply=_limit_and_disclaim(rule_reply),
        followUpQuestion=rule_question,
        proposal=rule_proposal,
        confidence=confidence,
        source="rules",
        fallbackReason=fallback_reason,
        disclaimer=DISCLAIMER,
    )


def build_rule_answer(question: str, digest: dict[str, Any], recommendation: Any = None) -> tuple[str, list[str]]:
    normalized = _normalize_text(question)
    metrics = digest.get("metrics", {})
    optimized = digest.get("optimizedMetrics", {})
    assets = digest.get("assets", [])
    top_asset = max(assets, key=lambda asset: float(asset.get("weight", 0))) if assets else {}
    top_sector = max(digest.get("sectorAllocation", []), key=lambda item: float(item.get("weight", 0)), default={})
    pct = lambda value: f"{float(value) * 100:.1f}".replace(".", ",")
    num = lambda value: f"{float(value):.2f}".replace(".", ",")

    if "sharpe" in normalized:
        answer = f"Deine Sharpe Ratio liegt bei {num(metrics.get('sharpeRatio', 0))}. Sie setzt die Rendite über dem risikofreien Zins ins Verhältnis zur Volatilität. Die Vergleichsvariante kommt auf {num(optimized.get('sharpeRatio', 0))}. Die Werte beruhen auf historischen Daten und sind keine Prognose."
        return answer, ["sharpeRatio", "expectedReturn", "riskFreeRate", "volatility"]
    if re.search(r"volatil|schwank", normalized):
        return f"Die historische Volatilität deines Portfolios liegt bei {pct(metrics.get('volatility', 0))} p.a. Sie beschreibt die typische Schwankungsbreite, nicht einen sicheren Verlust. Die Vergleichsvariante liegt bei {pct(optimized.get('volatility', 0))} p.a.", ["volatility", "optimizedMetrics.volatility"]
    if "rendite" in normalized or "ertrag" in normalized or "cagr" in normalized:
        return f"Die annualisierte Erwartungsrendite liegt bei {pct(metrics.get('expectedReturn', 0))}. Die geometrische Rendite der Kursreihe beträgt tatsächlich {pct(metrics.get('annualizedReturnGeometric', 0))} p.a. Der erste Wert ist ein arithmetischer Erwartungswert, der zweite die historische Wachstumsrate.", ["expectedReturn", "annualizedReturnGeometric"]
    if "value at risk" in normalized or re.search(r"\bvar\b|verlust", normalized):
        return f"Der historische Value at Risk beträgt {pct(metrics.get('valueAtRisk', 0))} für {metrics.get('valueAtRiskHorizonDays', 1)} Tag(e) bei {pct(digest.get('varConfidence', 0.95))} Konfidenz. Das ist ein historisches Quantil und keine Garantie für einen maximalen Verlust.", ["valueAtRisk", "valueAtRiskHorizonDays", "varConfidence", "valueAtRiskMethod"]
    if "korrel" in normalized:
        pairs = [item.get("message") for item in digest.get("riskFindings", []) if item.get("type") == "correlation"]
        return (pairs[0] if pairs else "Die Analyse enthält Korrelationsinformationen, aber keinen auffälligen Korrelationsbefund."), ["riskFindings", "correlationMatrix"]
    if re.search(r"divers|streu", normalized):
        return f"Der Diversifikationswert liegt bei {num(metrics.get('diversificationScore', 0))} von 100. Das entspricht etwa {num(metrics.get('effectiveHoldings', 0))} gleich gewichteten Positionen. Der Diversifikationsquotient liegt bei {num(metrics.get('diversificationRatio', 0))} und berücksichtigt zusätzlich den Streuungsnutzen durch Kovarianzen.", ["diversificationScore", "effectiveHoldings", "diversificationRatio"]
    if re.search(r"konzent|klump|dominant|einzel", normalized):
        return (str(next((item.get("message") for item in digest.get("riskFindings", []) if item.get("type") == "concentration"), f"Die größte Position ist {top_asset.get('ticker', 'unbekannt')} mit {pct(top_asset.get('weight', 0))}."))), ["riskFindings", "assets.weight"]
    if re.search(r"branche|sektor", normalized):
        return f"Der größte Sektor ist {top_sector.get('sector', 'unbekannt')} mit {pct(top_sector.get('weight', 0))}. Die Einordnung basiert auf den hinterlegten Asset-Metadaten.", ["sectorAllocation", "assets.sector"]
    if re.search(r"optim|vorschlag|gewicht", normalized):
        if recommendation is not None and getattr(recommendation, "weight_adjustments", None):
            adjustment = recommendation.weight_adjustments[0]
            return f"Die stärkste profilbezogene Anpassung betrifft {adjustment.ticker}: {pct(adjustment.current_weight)} auf {pct(adjustment.suggested_weight)}. {adjustment.reason}", ["weightAdjustments", "optimizationBasis"]
        return f"Die neutrale Vergleichsvariante begrenzt jede Position auf höchstens 35,0 Prozent. Die größte aktuelle Position ist {top_asset.get('ticker', 'unbekannt')}.", ["optimizedWeights", "optimizationSettings", "assets.weight"]
    if "zeitraum" in normalized or "jahre" in normalized:
        return f"Die Analyse umfasst den Zeitraum {digest.get('startDate', '')} bis {digest.get('endDate', '')}. Die Kennzahlen beschreiben diesen historischen Ausschnitt.", ["startDate", "endDate"]
    if re.search(r"datenquelle|yahoo|quelle", normalized):
        return f"Als Datenquelle ist {digest.get('dataSource', 'keine Quelle angegeben')} hinterlegt. Im Demo-Modus wurden lokale Annahmen verwendet.", ["dataSource", "mode"]
    if "demo" in normalized:
        return "Im Demo-Modus stammen die Werte aus lokalen, deterministischen Annahmen. Sie zeigen die Bedienung und Methodik, sind aber keine Live-Marktanalyse.", ["mode", "dataSource"]
    if re.search(r"haft|disclaimer|anlageberatung", normalized):
        return f"Die Anwendung ist keine Anlageberatung und gibt keine Prognosegarantie. {DISCLAIMER}", ["disclaimer"]
    if "method" in normalized or "formel" in normalized:
        return "Die Methodik kombiniert arithmetische Erwartungsrendite, geometrische historische Rendite, annualisierte Volatilität, Sharpe Ratio, historischen VaR sowie HHI-basierte Diversifikationskennzahlen.", ["metrics", "valueAtRiskMethod"]
    return "Mit den vorliegenden Daten kann ich Kennzahlen, historische Risiken, Diversifikation, Sektoren und die Vergleichsvariante erklären. Beispiele: Was bedeutet meine Sharpe Ratio? Wie diversifiziert ist mein Portfolio? Warum gibt es diese Gewichtungsanpassung?", []


async def answer_question(request: AskRequest) -> AskResponse:
    digest = build_digest(request.analysis)
    rule_answer, rule_metrics = build_rule_answer(request.question, digest, request.recommendation)
    prompt = (
        "Beantworte ausschließlich auf Basis des folgenden Analyse-Digests. Keine erfundenen Zahlen, "
        "Ticker oder Nachrichten, keine Kauf-/Verkaufsempfehlungen und keine Prognose. Deutsch, höchstens 150 Wörter. "
        "Antworte als JSON mit answer und usedMetrics.\n"
        f"Frage: {request.question}\nDigest: {json.dumps(digest, ensure_ascii=False)}"
    )
    allowed_tickers = {str(asset.get("ticker")) for asset in digest.get("assets", [])}
    if request.recommendation is not None:
        allowed_tickers.update(idea.ticker for idea in request.recommendation.new_ideas)

    fallback_reason = "no_backend_reachable"

    async def validate_model_answer(model_text: str | None, source: str) -> AskResponse | None:
        nonlocal fallback_reason
        if not model_text:
            return None
        parsed = _parse_json_object(model_text)
        if not parsed or not isinstance(parsed.get("answer"), str) or not isinstance(parsed.get("usedMetrics"), list):
            fallback_reason = "invalid_response"
            return None
        model_answer = str(parsed["answer"])
        if not _is_safe_model_answer(model_answer, allowed_tickers):
            fallback_reason = "validation_failed"
            return None
        used = [str(item) for item in parsed["usedMetrics"] if isinstance(item, str)][:8]
        return AskResponse(
            answer=_limit_and_disclaim(model_answer),
            usedMetrics=used,
            source=source,
            fallbackReason=None,
            disclaimer=DISCLAIMER,
        )

    if request.llm_preference in ("auto", "local"):
        try:
            model_text = await _call_ollama(prompt, OLLAMA_MODEL)
        except Exception:
            model_text = None
        model_response = await validate_model_answer(model_text, "ollama")
        if model_response is not None:
            return model_response
        if request.llm_preference == "local":
            fallback_reason = fallback_reason if model_text else "no_backend_reachable"

    if request.llm_preference in ("auto", "cloud"):
        cloud_result, cloud_status = await _call_cloud_with_status(prompt, None)
        cloud_text = cloud_result[0] if cloud_result is not None else None
        model_response = await validate_model_answer(cloud_text, "cloud")
        if model_response is not None:
            return model_response
        if cloud_text is None and cloud_status in {"timeout", "invalid_response"}:
            fallback_reason = cloud_status

    return AskResponse(
        answer=_limit_and_disclaim(rule_answer),
        usedMetrics=rule_metrics,
        source="rules",
        fallbackReason=fallback_reason,
        disclaimer=DISCLAIMER,
    )


def _is_safe_model_answer(answer: str, allowed_tickers: set[str]) -> bool:
    normalized = _normalize_text(answer)
    if any(phrase in normalized for phrase in TRADE_LANGUAGE):
        return False
    tickers = set(re.findall(r"\b[A-Z]{2,6}(?:\.[A-Z]{1,3})?\b", answer))
    return all(ticker in allowed_tickers or ticker in GENERIC_UPPERCASE_TERMS for ticker in tickers)


def _parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _limit_and_disclaim(text: str) -> str:
    disclaimer = f"\n\n{DISCLAIMER}"
    available = max(0, MAX_RESPONSE_CHARS - len(disclaimer))
    clean = text.strip()
    if len(clean) > available:
        clean = clean[: max(0, available - 3)].rstrip() + "..."
    return f"{clean}{disclaimer}"
