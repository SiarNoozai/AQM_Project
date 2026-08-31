from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from .market_intelligence import PROFILE_FALLBACKS
from .models import SecuritySearchResponse, SecuritySearchResult


ALLOWED_INSTRUMENT_TYPES = {"EQUITY", "ETF"}
LOCAL_EXCHANGE_FALLBACKS = {
    "AAPL": "NASDAQ",
    "MSFT": "NASDAQ",
    "GOOG": "NASDAQ",
    "GOOGL": "NASDAQ",
    "META": "NASDAQ",
    "AMZN": "NASDAQ",
    "NVDA": "NASDAQ",
    "TSLA": "NASDAQ",
    "P911.DE": "XETRA",
    "SPY": "NYSE Arca",
    "QQQ": "NASDAQ",
    "VTI": "NYSE Arca",
    "AGG": "NYSE Arca",
    "BND": "NASDAQ",
    "TLT": "NASDAQ",
    "VNQ": "NYSE Arca",
    "IEFA": "NASDAQ",
    "XLV": "NYSE Arca",
    "XLF": "NYSE Arca",
    "XLI": "NYSE Arca",
    "XLP": "NYSE Arca",
    "XLU": "NYSE Arca",
    "XLE": "NYSE Arca",
    "JNJ": "NYSE",
    "JPM": "NYSE",
    "CAT": "NYSE",
    "PG": "NYSE",
    "NEE": "NYSE",
    "XOM": "NYSE",
    "PLD": "NYSE",
    "VEA": "NYSE Arca",
    "LLY": "NYSE",
    "SMH": "NASDAQ",
}


def _get_yfinance():
    try:
        import yfinance as yf
    except Exception as exc:  # pragma: no cover - depends on local environment
        raise HTTPException(
            status_code=503,
            detail="Die Instrumentensuche ist aktuell nicht verfuegbar.",
        ) from exc

    return yf


def search_securities(query: str, limit: int = 8) -> SecuritySearchResponse:
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return SecuritySearchResponse(results=[])

    safe_limit = max(1, min(limit, 10))
    local_results = _search_local_catalog(normalized_query, safe_limit)
    if local_results:
        return SecuritySearchResponse(results=local_results)

    yf = _get_yfinance()

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
            timeout=2,
            raise_errors=True,
        )
    except Exception as exc:
        fallback_results = _search_local_catalog(normalized_query, safe_limit, allow_contains=True)
        if fallback_results:
            return SecuritySearchResponse(results=fallback_results)
        raise HTTPException(status_code=502, detail="Die Instrumentensuche ist aktuell nicht verfuegbar.") from exc

    try:
        quotes = getattr(search, "quotes", []) or []
    except Exception as exc:
        fallback_results = _search_local_catalog(normalized_query, safe_limit, allow_contains=True)
        if fallback_results:
            return SecuritySearchResponse(results=fallback_results)
        raise HTTPException(status_code=502, detail="Die Instrumentensuche ist aktuell nicht verfuegbar.") from exc

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


def _search_local_catalog(query: str, limit: int, allow_contains: bool = False) -> list[SecuritySearchResult]:
    normalized_query = query.strip().upper()
    matches: list[tuple[int, SecuritySearchResult]] = []

    for symbol, profile in PROFILE_FALLBACKS.items():
        haystack_name = profile.name.upper()
        haystack_symbol = symbol.upper()

        score = _local_match_score(normalized_query, haystack_symbol, haystack_name, allow_contains)
        if score is None:
            continue

        matches.append(
            (
                score,
                SecuritySearchResult(
                    symbol=symbol,
                    name=profile.name,
                    type="ETF" if profile.instrument_type == "ETF" else "EQUITY",
                    exchange=LOCAL_EXCHANGE_FALLBACKS.get(symbol, "Unbekannt"),
                ),
            )
        )

    matches.sort(key=lambda item: (item[0], item[1].symbol))
    return [result for _, result in matches[:limit]]


def _local_match_score(query: str, symbol: str, name: str, allow_contains: bool) -> int | None:
    if symbol == query:
        return 0
    if name == query:
        return 1
    if symbol.startswith(query):
        return 2
    if name.startswith(query):
        return 3
    if allow_contains and query in symbol:
        return 4
    if allow_contains and query in name:
        return 5
    return None


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
