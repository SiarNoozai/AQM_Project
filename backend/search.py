from __future__ import annotations

from typing import Any

import yfinance as yf
from fastapi import HTTPException

try:
    from .models import SecuritySearchResponse, SecuritySearchResult
except ImportError:
    from models import SecuritySearchResponse, SecuritySearchResult


ALLOWED_INSTRUMENT_TYPES = {"EQUITY", "ETF"}


def search_securities(query: str, limit: int = 8) -> SecuritySearchResponse:
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return SecuritySearchResponse(results=[])

    safe_limit = max(1, min(limit, 10))

    try:
        search = yf.Search(
            normalized_query,
            max_results=safe_limit,
            news_count=0,
            lists_count=0,
            include_nav_links=False,
            include_research=False,
            include_cultural_assets=False,
            enable_fuzzy_query=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Die Instrumentensuche ist aktuell nicht verfuegbar.",
        ) from exc

    try:
        quotes = getattr(search, "quotes", []) or []
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Die Instrumentensuche ist aktuell nicht verfuegbar.",
        ) from exc

    results: list[SecuritySearchResult] = []
    seen_symbols: set[str] = set()

    for raw_quote in quotes:
        normalized = _normalize_quote(raw_quote)
        if not normalized:
            continue
        if normalized.symbol in seen_symbols:
            continue
        seen_symbols.add(normalized.symbol)
        results.append(normalized)
        if len(results) >= safe_limit:
            break

    return SecuritySearchResponse(results=results)


def _normalize_quote(raw_quote: dict[str, Any]) -> SecuritySearchResult | None:
    symbol = str(raw_quote.get("symbol") or "").strip().upper()
    if not symbol:
        return None

    quote_type = _normalize_type(raw_quote)
    if quote_type not in ALLOWED_INSTRUMENT_TYPES:
        return None

    name = (
        str(
            raw_quote.get("shortname")
            or raw_quote.get("longname")
            or raw_quote.get("name")
            or raw_quote.get("symbol")
            or ""
        ).strip()
        or symbol
    )
    exchange = (
        str(
            raw_quote.get("exchangeDisp")
            or raw_quote.get("exchDisp")
            or raw_quote.get("exchange")
            or raw_quote.get("fullExchangeName")
            or "Unbekannt"
        ).strip()
        or "Unbekannt"
    )

    return SecuritySearchResult(
        symbol=symbol,
        name=name,
        type=quote_type,
        exchange=exchange,
    )


def _normalize_type(raw_quote: dict[str, Any]) -> str:
    raw_type = raw_quote.get("quoteType") or raw_quote.get("typeDisp") or raw_quote.get("type") or ""
    normalized = str(raw_type).strip().upper()
    if normalized in {"MUTUALFUND", "MUTUAL FUND"}:
        return "MUTUALFUND"
    return normalized
