from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from fastapi import HTTPException

try:
    from .market_intelligence import fetch_asset_profiles
    from .models import (
        AnalysisResponse,
        AnalyzeRequest,
        AssetResult,
        CorrelationMatrix,
        FrontierPoint,
        PortfolioMetrics,
        RiskFinding,
        SectorAllocationItem,
    )
except ImportError:
    from market_intelligence import fetch_asset_profiles
    from models import (
        AnalysisResponse,
        AnalyzeRequest,
        AssetResult,
        CorrelationMatrix,
        FrontierPoint,
        PortfolioMetrics,
        RiskFinding,
        SectorAllocationItem,
    )


DISCLAIMER = (
    "Dies ist keine Anlageberatung. Die Analyse basiert auf historischen Yahoo-Finance-Daten "
    "ueber yfinance und bietet keine Prognosegarantie."
)
DEMO_DATA_SOURCE = "Lokale Demo-Daten (Live-Marktdaten waren nicht rechtzeitig verfuegbar)"
DEMO_DISCLAIMER_SUFFIX = " Fuer diese Auswertung wurden lokale Demo-Annahmen statt Live-Daten verwendet."


@dataclass(frozen=True)
class DemoAssetAssumption:
    expected_return: float
    volatility: float
    last_price: float


DEFAULT_DEMO_ASSET = DemoAssetAssumption(expected_return=0.08, volatility=0.19, last_price=100.0)
DEMO_ASSET_ASSUMPTIONS: dict[str, DemoAssetAssumption] = {
    "AAPL": DemoAssetAssumption(0.148, 0.255, 212.0),
    "MSFT": DemoAssetAssumption(0.132, 0.218, 468.0),
    "SPY": DemoAssetAssumption(0.091, 0.152, 548.0),
    "AGG": DemoAssetAssumption(0.037, 0.062, 99.0),
    "QQQ": DemoAssetAssumption(0.118, 0.209, 486.0),
    "VTI": DemoAssetAssumption(0.086, 0.148, 285.0),
    "BND": DemoAssetAssumption(0.034, 0.058, 72.0),
    "VNQ": DemoAssetAssumption(0.071, 0.173, 84.0),
    "IEFA": DemoAssetAssumption(0.074, 0.141, 78.0),
    "TLT": DemoAssetAssumption(0.041, 0.108, 93.0),
    "GOOG": DemoAssetAssumption(0.121, 0.232, 182.0),
    "GOOGL": DemoAssetAssumption(0.121, 0.232, 182.0),
    "META": DemoAssetAssumption(0.139, 0.274, 516.0),
    "AMZN": DemoAssetAssumption(0.116, 0.247, 191.0),
    "NVDA": DemoAssetAssumption(0.178, 0.382, 128.0),
    "TSLA": DemoAssetAssumption(0.143, 0.401, 244.0),
    "P911.DE": DemoAssetAssumption(0.089, 0.241, 71.0),
    "XLV": DemoAssetAssumption(0.075, 0.146, 144.0),
    "XLF": DemoAssetAssumption(0.071, 0.171, 46.0),
    "XLI": DemoAssetAssumption(0.079, 0.168, 132.0),
    "XLP": DemoAssetAssumption(0.055, 0.112, 78.0),
    "XLU": DemoAssetAssumption(0.049, 0.129, 70.0),
    "XLE": DemoAssetAssumption(0.082, 0.221, 94.0),
    "JNJ": DemoAssetAssumption(0.068, 0.152, 162.0),
    "JPM": DemoAssetAssumption(0.087, 0.231, 211.0),
    "CAT": DemoAssetAssumption(0.084, 0.244, 338.0),
    "PG": DemoAssetAssumption(0.057, 0.118, 168.0),
    "NEE": DemoAssetAssumption(0.061, 0.164, 76.0),
    "XOM": DemoAssetAssumption(0.079, 0.233, 115.0),
    "PLD": DemoAssetAssumption(0.073, 0.192, 121.0),
    "VEA": DemoAssetAssumption(0.069, 0.137, 53.0),
    "LLY": DemoAssetAssumption(0.124, 0.226, 912.0),
    "SMH": DemoAssetAssumption(0.118, 0.258, 270.0),
}


def _get_yfinance():
    try:
        import yfinance as yf
    except Exception as exc:  # pragma: no cover - depends on local environment
        raise HTTPException(
            status_code=503,
            detail="Das Marktdaten-Modul konnte nicht geladen werden. Bitte starte das Backend neu.",
        ) from exc

    return yf


def run_analysis(request: AnalyzeRequest) -> AnalysisResponse:
    weights = _normalize_weights(np.array(request.weights, dtype=float))
    mode = "live"
    data_source = "Yahoo Finance via yfinance"
    disclaimer = DISCLAIMER

    try:
        prices = _download_prices(request)
        returns = _calculate_returns(prices, request.frequency)
        if returns.empty or len(returns) < 10:
            raise HTTPException(
                status_code=422,
                detail="Nicht genug Kursdaten fuer eine belastbare Analyse gefunden.",
            )
    except HTTPException as exc:
        if not _should_use_demo_fallback(exc):
            raise
        prices = _build_demo_prices(request)
        returns = _calculate_returns(prices, request.frequency)
        mode = "demo"
        data_source = DEMO_DATA_SOURCE
        disclaimer = f"{DISCLAIMER}{DEMO_DISCLAIMER_SUFFIX}"

    profiles = fetch_asset_profiles(request.tickers)
    annual_factor = _annualization_factor(request.frequency)
    mean_returns = returns.mean() * annual_factor
    covariance = returns.cov() * annual_factor
    correlation = returns.corr()
    current_metrics = _metrics(mean_returns, covariance, returns, weights, request.risk_free_rate, request.var_confidence)
    optimized_weights = _optimize_max_sharpe(mean_returns, covariance, request.risk_free_rate)
    optimized_metrics = _metrics(
        mean_returns,
        covariance,
        returns,
        optimized_weights,
        request.risk_free_rate,
        request.var_confidence,
    )
    frontier = _build_frontier(mean_returns, covariance, request.risk_free_rate, weights, optimized_weights)
    performance = _build_performance(prices, weights, optimized_weights)
    asset_results = _build_asset_results(request.tickers, weights, mean_returns, covariance, prices, profiles)
    sector_allocation = _build_sector_allocation(asset_results)
    risk_findings = _build_risk_findings(request.tickers, weights, correlation, current_metrics, optimized_metrics)

    return AnalysisResponse(
        mode=mode,
        dataSource=data_source,
        updatedAt=datetime.now(timezone.utc),
        startDate=request.start_date,
        endDate=request.end_date,
        frequency=request.frequency,
        riskFreeRate=request.risk_free_rate,
        varConfidence=request.var_confidence,
        assets=asset_results,
        sectorAllocation=sector_allocation,
        metrics=current_metrics,
        optimizedMetrics=optimized_metrics,
        optimizedWeights=[float(value) for value in optimized_weights],
        riskFindings=risk_findings,
        correlationMatrix=CorrelationMatrix(
            tickers=request.tickers,
            values=_matrix_to_lists(correlation),
        ),
        covarianceMatrix=_matrix_to_lists(covariance),
        performance=performance,
        frontier=frontier,
        recommendations=build_rule_recommendations(
            request.tickers,
            weights,
            current_metrics.model_dump(by_alias=True),
            optimized_metrics.model_dump(by_alias=True),
            optimized_weights,
            risk_findings,
        ),
        recommendationSource="rules",
        disclaimer=disclaimer,
    )


def build_rule_recommendations(
    tickers: list[str],
    weights: np.ndarray | list[float],
    metrics: dict[str, float],
    optimized_metrics: dict[str, float],
    optimized_weights: np.ndarray | list[float],
    risk_findings: list[RiskFinding] | None = None,
) -> list[str]:
    weight_array = np.array(weights, dtype=float)
    optimized_array = np.array(optimized_weights, dtype=float)
    dominant_index = int(np.argmax(weight_array))
    largest_shift_index = int(np.argmax(np.abs(optimized_array - weight_array)))
    sharpe_delta = optimized_metrics["sharpeRatio"] - metrics["sharpeRatio"]
    risk_change = optimized_metrics["volatility"] - metrics["volatility"]
    main_finding = next(
        (finding.message for finding in risk_findings or [] if finding.type in {"concentration", "correlation"}),
        None,
    )

    return [
        main_finding
        or (
            f"Die groesste Einzelposition ist {tickers[dominant_index]} mit "
            f"{weight_array[dominant_index] * 100:.1f} Prozent. Pruefe, ob diese Konzentration "
            "zu deinem Risikoprofil passt."
        ),
        (
            f"Eine datenbasierte Portfolioverbesserung waere, {tickers[largest_shift_index]} von "
            f"{weight_array[largest_shift_index] * 100:.1f} Prozent auf "
            f"{optimized_array[largest_shift_index] * 100:.1f} Prozent umzugewichten, "
            "um die Gewichte breiter und nachvollziehbarer zu verteilen."
        ),
        (
            f"Diese Anpassung stuetzt sich auf die berechneten Kennzahlen: Die Sharpe Ratio veraendert sich um "
            f"{sharpe_delta:.2f} Punkte und das Risiko um {risk_change * 100:+.1f} Prozentpunkte. "
            "Die Empfehlung basiert nur auf historischen Analysedaten."
        ),
    ]


def _build_risk_findings(
    tickers: list[str],
    weights: np.ndarray,
    correlation: pd.DataFrame,
    metrics: PortfolioMetrics,
    optimized_metrics: PortfolioMetrics,
) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    dominant_index = int(np.argmax(weights))
    dominant_weight = float(weights[dominant_index])
    if dominant_weight >= 0.30:
        findings.append(
            RiskFinding(
                type="concentration",
                severity="high" if dominant_weight >= 0.45 else "medium",
                message=(
                    f"{tickers[dominant_index]} ist mit {dominant_weight * 100:.1f} Prozent stark gewichtet. "
                    "Das kann dein Portfolio anfaelliger fuer Einzelrisiken machen."
                ),
            )
        )

    correlation_pairs = _high_correlation_pairs(correlation)
    if correlation_pairs:
        left, right = correlation_pairs[0]
        findings.append(
            RiskFinding(
                type="correlation",
                severity="medium",
                message=(
                    f"{left} und {right} bewegen sich historisch stark gemeinsam. "
                    "Dadurch kann die Diversifikation geringer sein als sie auf den ersten Blick wirkt."
                ),
            )
        )

    if metrics.diversification_score < 60:
        findings.append(
            RiskFinding(
                type="diversification",
                severity="medium",
                message=(
                    f"Der Diversifikationswert liegt bei {metrics.diversification_score:.1f} von 100. "
                    "Eine breitere Gewichtung koennte das Portfolio robuster machen."
                ),
            )
        )

    if metrics.volatility >= 0.24:
        findings.append(
            RiskFinding(
                type="volatility",
                severity="high" if metrics.volatility >= 0.32 else "medium",
                message=(
                    f"Die historische Volatilitaet liegt bei {metrics.volatility * 100:.1f} Prozent pro Jahr. "
                    "Das spricht fuer spuerbare Schwankungen im Portfolio."
                ),
            )
        )

    if optimized_metrics.sharpe_ratio - metrics.sharpe_ratio >= 0.15:
        findings.append(
            RiskFinding(
                type="risk_return",
                severity="low",
                message=(
                    "Die berechnete Vergleichsvariante erreicht ein besseres Rendite-Risiko-Verhaeltnis. "
                    "Es lohnt sich daher, die aktuelle Gewichtung kritisch mit der optimierten Alternative zu vergleichen."
                ),
            )
        )

    return findings[:4]


def _download_prices(request: AnalyzeRequest) -> pd.DataFrame:
    yf = _get_yfinance()
    try:
        data = yf.download(
            tickers=request.tickers,
            start=request.start_date.isoformat(),
            end=request.end_date.isoformat(),
            interval=request.frequency,
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=False,
            timeout=6,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Kursdaten konnten nicht geladen werden: {exc}") from exc

    if data.empty:
        raise HTTPException(status_code=422, detail="Keine Kursdaten fuer die angegebenen Ticker gefunden.")

    prices = _extract_close_prices(data, request.tickers)
    prices = prices.dropna(axis=1, how="all").ffill().dropna()
    missing = [ticker for ticker in request.tickers if ticker not in prices.columns]
    if missing:
        raise HTTPException(status_code=422, detail=f"Keine verwertbaren Kursdaten fuer: {', '.join(missing)}")
    if prices.shape[1] != len(request.tickers):
        raise HTTPException(status_code=422, detail="Nicht fuer alle Ticker liegen verwertbare Kursdaten vor.")
    return prices[request.tickers]


def _should_use_demo_fallback(error: HTTPException) -> bool:
    if error.status_code >= 500:
        return True

    detail = str(error.detail).lower()
    return "keine kursdaten" in detail or "nicht genug kursdaten" in detail


def _build_demo_prices(request: AnalyzeRequest) -> pd.DataFrame:
    end_timestamp = pd.Timestamp(request.end_date)
    index = pd.bdate_range(start=request.start_date, end=request.end_date)
    if len(index) < 60:
        index = pd.bdate_range(end=end_timestamp, periods=60)

    market_cycle = np.linspace(0, 4 * np.pi, len(index))
    market_wave = np.sin(market_cycle) * 0.0028
    macro_wave = np.cos(market_cycle * 0.45) * 0.0012
    data: dict[str, np.ndarray] = {}

    for ticker in request.tickers:
        assumption = DEMO_ASSET_ASSUMPTIONS.get(ticker, DEFAULT_DEMO_ASSET)
        seed = (sum(ord(char) for char in ticker) % 13) + 1
        annual_return = assumption.expected_return
        annual_volatility = assumption.volatility
        daily_return = annual_return / 252
        daily_volatility = annual_volatility / np.sqrt(252)

        asset_cycle = np.linspace(0, (seed + 3) * np.pi, len(index))
        asset_wave = np.sin(asset_cycle) * daily_volatility * 0.55
        secondary_wave = np.cos(asset_cycle * 0.63) * daily_volatility * 0.28
        drift = np.linspace(-0.0003, 0.0007, len(index))
        returns = daily_return + market_wave + macro_wave + asset_wave + secondary_wave + drift
        clipped_returns = np.clip(returns, -0.085, 0.085)

        price_path = 100 * np.cumprod(1 + clipped_returns)
        scaled_path = price_path * (assumption.last_price / price_path[-1])
        data[ticker] = scaled_path

    return pd.DataFrame(data, index=index)


def _extract_close_prices(data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            prices = data["Close"].copy()
        elif "Adj Close" in data.columns.get_level_values(0):
            prices = data["Adj Close"].copy()
        else:
            raise HTTPException(status_code=422, detail="Yahoo-Finance-Antwort enthaelt keine Schlusskurse.")
    else:
        close_column = "Close" if "Close" in data.columns else "Adj Close"
        if close_column not in data.columns:
            raise HTTPException(status_code=422, detail="Yahoo-Finance-Antwort enthaelt keine Schlusskurse.")
        prices = data[[close_column]].copy()
        prices.columns = [tickers[0]]

    prices.columns = [str(column).upper() for column in prices.columns]
    return prices


def _calculate_returns(prices: pd.DataFrame, frequency: str) -> pd.DataFrame:
    if frequency == "1d":
        sampled = prices
    elif frequency == "1wk":
        sampled = prices.resample("W-FRI").last()
    else:
        sampled = prices.resample("ME").last()
    return sampled.pct_change(fill_method=None).dropna()


def _annualization_factor(frequency: str) -> int:
    if frequency == "1d":
        return 252
    if frequency == "1wk":
        return 52
    return 12


def _normalize_weights(weights: np.ndarray) -> np.ndarray:
    total = float(weights.sum())
    if total <= 0:
        raise HTTPException(status_code=422, detail="Gewichtssumme muss groesser als null sein.")
    return weights / total


def _metrics(
    mean_returns: pd.Series,
    covariance: pd.DataFrame,
    returns: pd.DataFrame,
    weights: np.ndarray,
    risk_free_rate: float,
    var_confidence: float,
) -> PortfolioMetrics:
    expected_return = float(np.dot(weights, mean_returns.to_numpy()))
    volatility = float(np.sqrt(weights.T @ covariance.to_numpy() @ weights))
    sharpe = float((expected_return - risk_free_rate) / volatility) if volatility > 0 else 0.0
    portfolio_returns = returns.to_numpy() @ weights
    tail_probability = 1 - var_confidence
    historical_var = float(abs(np.quantile(portfolio_returns, tail_probability)))
    diversification_score = _diversification_score(weights)

    return PortfolioMetrics(
        expectedReturn=expected_return,
        volatility=volatility,
        sharpeRatio=sharpe,
        valueAtRisk=historical_var,
        diversificationScore=diversification_score,
    )


def _optimize_max_sharpe(mean_returns: pd.Series, covariance: pd.DataFrame, risk_free_rate: float) -> np.ndarray:
    # SciPy is only needed for optimization requests; importing it lazily keeps API startup responsive.
    from scipy.optimize import minimize

    asset_count = len(mean_returns)
    initial = np.repeat(1 / asset_count, asset_count)
    bounds = tuple((0.0, 1.0) for _ in range(asset_count))
    constraints = ({"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},)

    def objective(weights: np.ndarray) -> float:
        expected_return = float(np.dot(weights, mean_returns.to_numpy()))
        volatility = float(np.sqrt(weights.T @ covariance.to_numpy() @ weights))
        if volatility <= 0:
            return 1e6
        return -((expected_return - risk_free_rate) / volatility)

    result = minimize(objective, initial, method="SLSQP", bounds=bounds, constraints=constraints)
    if not result.success:
        return initial
    return _normalize_weights(np.clip(result.x, 0, 1))


def _build_frontier(
    mean_returns: pd.Series,
    covariance: pd.DataFrame,
    risk_free_rate: float,
    current_weights: np.ndarray,
    optimized_weights: np.ndarray,
) -> list[FrontierPoint]:
    points: list[FrontierPoint] = []
    asset_count = len(mean_returns)
    rng = np.random.default_rng(42)
    for index in range(140):
        weights = rng.dirichlet(np.ones(asset_count))
        risk, expected_return, sharpe = _risk_return_sharpe(mean_returns, covariance, weights, risk_free_rate)
        points.append(
            FrontierPoint(
                id=index,
                risk=risk,
                return_=expected_return,
                sharpe=sharpe,
                weights=[float(value) for value in weights],
                kind="simulation",
            )
        )

    current = _risk_return_sharpe(mean_returns, covariance, current_weights, risk_free_rate)
    optimized = _risk_return_sharpe(mean_returns, covariance, optimized_weights, risk_free_rate)
    points.extend(
        [
            FrontierPoint(
                id=900,
                risk=current[0],
                return_=current[1],
                sharpe=current[2],
                weights=[float(value) for value in current_weights],
                kind="current",
            ),
            FrontierPoint(
                id=901,
                risk=optimized[0],
                return_=optimized[1],
                sharpe=optimized[2],
                weights=[float(value) for value in optimized_weights],
                kind="optimized",
            ),
        ]
    )
    return points


def _risk_return_sharpe(
    mean_returns: pd.Series,
    covariance: pd.DataFrame,
    weights: np.ndarray,
    risk_free_rate: float,
) -> tuple[float, float, float]:
    expected_return = float(np.dot(weights, mean_returns.to_numpy()))
    risk = float(np.sqrt(weights.T @ covariance.to_numpy() @ weights))
    sharpe = float((expected_return - risk_free_rate) / risk) if risk > 0 else 0.0
    return risk, expected_return, sharpe


def _build_performance(prices: pd.DataFrame, weights: np.ndarray, optimized_weights: np.ndarray) -> list[dict[str, float | str]]:
    normalized = prices / prices.iloc[0] * 100
    rows: list[dict[str, float | str]] = []
    max_points = 90
    if len(normalized) > max_points:
        normalized = normalized.iloc[np.linspace(0, len(normalized) - 1, max_points).astype(int)]

    for date_value, row in normalized.iterrows():
        values = row.to_numpy(dtype=float)
        item: dict[str, float | str] = {
            "date": date_value.strftime("%Y-%m-%d"),
            "month": date_value.strftime("%b %y"),
            "portfolio": round(float(np.dot(weights, values)), 2),
            "optimized": round(float(np.dot(optimized_weights, values)), 2),
        }
        for ticker, value in row.items():
            item[str(ticker)] = round(float(value), 2)
        rows.append(item)
    return rows


def _build_asset_results(
    tickers: list[str],
    weights: np.ndarray,
    mean_returns: pd.Series,
    covariance: pd.DataFrame,
    prices: pd.DataFrame,
    profiles: dict[str, object],
) -> list[AssetResult]:
    results: list[AssetResult] = []
    for index, ticker in enumerate(tickers):
        profile = profiles[ticker]
        results.append(
            AssetResult(
                ticker=ticker,
                name=getattr(profile, "name"),
                sector=getattr(profile, "sector"),
                instrument_type=getattr(profile, "instrument_type"),
                weight=float(weights[index]),
                expectedReturn=float(mean_returns[ticker]),
                volatility=float(np.sqrt(covariance.loc[ticker, ticker])),
                lastPrice=float(prices[ticker].iloc[-1]),
            )
        )
    return results


def _build_sector_allocation(asset_results: list[AssetResult]) -> list[SectorAllocationItem]:
    grouped: dict[str, dict[str, object]] = {}
    for asset in asset_results:
        bucket = grouped.setdefault(asset.sector, {"weight": 0.0, "tickers": []})
        bucket["weight"] = float(bucket["weight"]) + asset.weight
        bucket["tickers"] = [*bucket["tickers"], asset.ticker]

    ordered = sorted(grouped.items(), key=lambda item: float(item[1]["weight"]), reverse=True)
    return [
        SectorAllocationItem(
            sector=sector,
            weight=round(float(values["weight"]), 6),
            tickers=list(values["tickers"]),
        )
        for sector, values in ordered
    ]


def _matrix_to_lists(matrix: pd.DataFrame) -> list[list[float]]:
    return [[round(float(value), 6) for value in row] for row in matrix.to_numpy()]


def _diversification_score(weights: np.ndarray) -> float:
    herfindahl = float(np.sum(weights * weights))
    return max(0.0, min(100.0, (1 - herfindahl) * 140))


def _high_correlation_pairs(correlation: pd.DataFrame, threshold: float = 0.75) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    tickers = [str(ticker) for ticker in correlation.columns]
    for row_index, left in enumerate(tickers):
        for column_index, right in enumerate(tickers):
            if column_index <= row_index:
                continue
            value = float(correlation.iloc[row_index, column_index])
            if value >= threshold:
                pairs.append((left, right))
    return pairs
