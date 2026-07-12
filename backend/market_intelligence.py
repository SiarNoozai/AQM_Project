from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
import yfinance as yf


ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


@dataclass(frozen=True)
class AssetProfile:
    name: str
    sector: str
    instrument_type: str


PROFILE_FALLBACKS: dict[str, AssetProfile] = {
    "AAPL": AssetProfile("Apple", "Information Technology", "EQUITY"),
    "MSFT": AssetProfile("Microsoft", "Information Technology", "EQUITY"),
    "GOOG": AssetProfile("Alphabet", "Communication Services", "EQUITY"),
    "GOOGL": AssetProfile("Alphabet", "Communication Services", "EQUITY"),
    "META": AssetProfile("Meta Platforms", "Communication Services", "EQUITY"),
    "AMZN": AssetProfile("Amazon", "Consumer Discretionary", "EQUITY"),
    "NVDA": AssetProfile("NVIDIA", "Information Technology", "EQUITY"),
    "TSLA": AssetProfile("Tesla", "Consumer Discretionary", "EQUITY"),
    "P911.DE": AssetProfile("Porsche AG", "Consumer Discretionary", "EQUITY"),
    "SPY": AssetProfile("S&P 500 ETF", "ETF / Multi-Sektor", "ETF"),
    "QQQ": AssetProfile("Nasdaq 100 ETF", "ETF / Multi-Sektor", "ETF"),
    "VTI": AssetProfile("Total Stock Market ETF", "ETF / Multi-Sektor", "ETF"),
    "AGG": AssetProfile("US Aggregate Bond ETF", "Fixed Income", "ETF"),
    "BND": AssetProfile("Total Bond Market ETF", "Fixed Income", "ETF"),
    "TLT": AssetProfile("Long-Term Treasury ETF", "Government Bonds", "ETF"),
    "VNQ": AssetProfile("Real Estate ETF", "Real Estate", "ETF"),
    "IEFA": AssetProfile("Developed Markets ETF", "International Equities", "ETF"),
    "XLV": AssetProfile("Health Care Select Sector SPDR Fund", "Health Care", "ETF"),
    "XLF": AssetProfile("Financial Select Sector SPDR Fund", "Financial Services", "ETF"),
    "XLI": AssetProfile("Industrial Select Sector SPDR Fund", "Industrials", "ETF"),
    "XLP": AssetProfile("Consumer Staples Select Sector SPDR Fund", "Consumer Staples", "ETF"),
    "XLU": AssetProfile("Utilities Select Sector SPDR Fund", "Utilities", "ETF"),
    "XLE": AssetProfile("Energy Select Sector SPDR Fund", "Energy", "ETF"),
}


def fetch_asset_profiles(tickers: list[str]) -> dict[str, AssetProfile]:
    return {ticker: _fetch_asset_profile(ticker) for ticker in tickers}


def _fetch_asset_profile(ticker: str) -> AssetProfile:
    fallback = PROFILE_FALLBACKS.get(ticker, AssetProfile(ticker, "Unbekannt", "EQUITY"))
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return fallback

    name = str(info.get("longName") or info.get("shortName") or fallback.name).strip() or fallback.name
    raw_type = str(info.get("quoteType") or info.get("instrumentType") or fallback.instrument_type).upper()
    instrument_type = "ETF" if "ETF" in raw_type or "FUND" in raw_type else "EQUITY"
    sector = str(info.get("sectorDisp") or info.get("sector") or "").strip()
    if not sector:
        sector = fallback.sector if fallback.sector != "Unbekannt" else ("ETF / Multi-Sektor" if instrument_type == "ETF" else "Unbekannt")

    return AssetProfile(name=name, sector=sector, instrument_type=instrument_type)


async def fetch_news_signals(tickers: list[str], max_results: int = 4) -> list[dict[str, str]]:
    if not ALPHA_VANTAGE_API_KEY:
        return []

    collected: list[dict[str, str]] = []
    async with httpx.AsyncClient(timeout=5) as client:
        for ticker in tickers[:max_results]:
            if len(collected) >= max_results:
                break
            try:
                response = await client.get(
                    ALPHA_VANTAGE_URL,
                    params={
                        "function": "NEWS_SENTIMENT",
                        "tickers": ticker,
                        "limit": 3,
                        "apikey": ALPHA_VANTAGE_API_KEY,
                    },
                )
                response.raise_for_status()
            except Exception:
                continue

            body = response.json()
            for item in body.get("feed", []):
                headline = str(item.get("title") or "").strip()
                url = str(item.get("url") or "").strip()
                if not headline or not url:
                    continue
                collected.append(
                    {
                        "ticker": ticker,
                        "headline": headline,
                        "sentimentLabel": _normalize_sentiment_label(
                            str(item.get("overall_sentiment_label") or item.get("sentiment") or "")
                        ),
                        "url": url,
                    }
                )
                break

    return collected[:max_results]


def _normalize_sentiment_label(value: str) -> str:
    normalized = value.lower()
    if "bear" in normalized or "negative" in normalized:
        return "negative"
    if "bull" in normalized or "positive" in normalized:
        return "positive"
    if "mixed" in normalized:
        return "mixed"
    return "neutral"
