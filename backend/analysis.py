from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from fastapi import HTTPException

from .market_intelligence import fetch_asset_profiles
from .models import (
    AnalysisResponse,
    AnalyzeRequest,
    AssetResult,
    CorrelationMatrix,
    OptimizationSettings,
    PortfolioMetrics,
    RiskFinding,
    SectorAllocationItem,
)


class MarketDataUnavailable(RuntimeError):
    """A provider or transport failure that can safely use demo data."""


DISCLAIMER = (
    "Dies ist keine Anlageberatung. Die Analyse basiert auf historischen Yahoo-Finance-Daten "
    "über yfinance und bietet keine Prognosegarantie."
)
DEMO_DATA_SOURCE = "Lokale Demo-Daten (Live-Marktdaten waren nicht rechtzeitig verfügbar)"
DEMO_DISCLAIMER_SUFFIX = " Für diese Auswertung wurden lokale Demo-Annahmen statt Live-Daten verwendet."
OPTIMIZATION_MAX_WEIGHT = 0.35
OPTIMIZATION_SHRINKAGE_INTENSITY = 0.2


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
        raise MarketDataUnavailable("Das Marktdaten-Modul konnte nicht geladen werden.") from exc

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
                detail="Nicht genug Kursdaten für eine belastbare Analyse gefunden.",
            )
    except MarketDataUnavailable:
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
    current_metrics = _metrics(
        mean_returns,
        covariance,
        returns,
        weights,
        request.risk_free_rate,
        request.var_confidence,
        prices=prices,
        frequency=request.frequency,
    )
    optimized_weights, optimization_converged = _optimize_max_sharpe_with_status(
        mean_returns,
        covariance,
        request.risk_free_rate,
        max_weight=OPTIMIZATION_MAX_WEIGHT,
    )
    optimized_metrics = _metrics(
        mean_returns,
        covariance,
        returns,
        optimized_weights,
        request.risk_free_rate,
        request.var_confidence,
        prices=prices,
        frequency=request.frequency,
    )
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
        optimizationSettings=OptimizationSettings(
            objective="max_sharpe",
            maxWeight=OPTIMIZATION_MAX_WEIGHT,
            shrinkageIntensity=OPTIMIZATION_SHRINKAGE_INTENSITY,
            converged=optimization_converged,
        ),
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
            f"Die größte Einzelposition ist {tickers[dominant_index]} mit "
            f"{weight_array[dominant_index] * 100:.1f} Prozent. Prüfe, ob diese Konzentration "
            "zu deinem Risikoprofil passt."
        ),
        (
            f"Eine datenbasierte Portfolioverbesserung wäre, {tickers[largest_shift_index]} von "
            f"{weight_array[largest_shift_index] * 100:.1f} Prozent auf "
            f"{optimized_array[largest_shift_index] * 100:.1f} Prozent umzugewichten, "
            "um die Gewichte breiter und nachvollziehbarer zu verteilen."
        ),
        (
            f"Diese Anpassung stützt sich auf die berechneten Kennzahlen: Die Sharpe Ratio verändert sich um "
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
                    "Das kann dein Portfolio anfälliger für Einzelrisiken machen."
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
                    f"Das entspricht rechnerisch etwa {metrics.effective_holdings:.1f} gleich gewichteten Positionen. "
                    "Eine breitere Gewichtung könnte das Portfolio robuster machen."
                ),
            )
        )

    if metrics.volatility >= 0.24:
        findings.append(
            RiskFinding(
                type="volatility",
                severity="high" if metrics.volatility >= 0.32 else "medium",
                message=(
                    f"Die historische Volatilität liegt bei {metrics.volatility * 100:.1f} Prozent pro Jahr. "
                    "Das spricht für spürbare Schwankungen im Portfolio."
                ),
            )
        )

    if optimized_metrics.sharpe_ratio - metrics.sharpe_ratio >= 0.15:
        findings.append(
            RiskFinding(
                type="risk_return",
                severity="low",
                message=(
                    "Die berechnete Vergleichsvariante erreicht ein besseres Rendite-Risiko-Verhältnis. "
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
            timeout=15,
        )
    except Exception as exc:
        raise MarketDataUnavailable(f"Kursdaten konnten nicht geladen werden: {exc}") from exc

    if data.empty:
        raise HTTPException(status_code=422, detail="Keine Kursdaten für die angegebenen Ticker gefunden.")

    prices = _extract_close_prices(data, request.tickers)
    prices = prices.dropna(axis=1, how="all").ffill().dropna()
    missing = [ticker for ticker in request.tickers if ticker not in prices.columns]
    if missing:
        raise HTTPException(status_code=422, detail=f"Keine verwertbaren Kursdaten für: {', '.join(missing)}")
    if prices.shape[1] != len(request.tickers):
        raise HTTPException(status_code=422, detail="Nicht für alle Ticker liegen verwertbare Kursdaten vor.")
    return prices[request.tickers]


def _should_use_demo_fallback(error: BaseException) -> bool:
    return isinstance(error, MarketDataUnavailable)


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
            raise MarketDataUnavailable("Yahoo-Finance-Antwort enthält keine Schlusskurse.")
    else:
        close_column = "Close" if "Close" in data.columns else "Adj Close"
        if close_column not in data.columns:
            raise MarketDataUnavailable("Yahoo-Finance-Antwort enthält keine Schlusskurse.")
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
        raise HTTPException(status_code=422, detail="Gewichtssumme muss größer als null sein.")
    return weights / total


def _metrics(
    mean_returns: pd.Series,
    covariance: pd.DataFrame,
    returns: pd.DataFrame,
    weights: np.ndarray,
    risk_free_rate: float,
    var_confidence: float,
    prices: pd.DataFrame | None = None,
    frequency: str = "1d",
) -> PortfolioMetrics:
    expected_return = float(np.dot(weights, mean_returns.to_numpy()))
    volatility = float(np.sqrt(weights.T @ covariance.to_numpy() @ weights))
    sharpe = float((expected_return - risk_free_rate) / volatility) if volatility > 0 else 0.0
    portfolio_returns = returns.to_numpy() @ weights
    tail_probability = 1 - var_confidence
    historical_var = float(abs(np.quantile(portfolio_returns, tail_probability)))
    diversification_score = _diversification_score(weights)
    individual_volatilities = np.sqrt(np.maximum(np.diag(covariance.to_numpy()), 0.0))
    diversification_ratio = (
        float(np.dot(weights, individual_volatilities) / volatility) if volatility > 0 else 0.0
    )
    effective_holdings = _effective_holdings(weights)
    geometric_return = _portfolio_geometric_return(prices, weights) if prices is not None else expected_return

    return PortfolioMetrics(
        expectedReturn=expected_return,
        volatility=volatility,
        sharpeRatio=sharpe,
        valueAtRisk=historical_var,
        diversificationScore=diversification_score,
        effectiveHoldings=round(effective_holdings, 1),
        diversificationRatio=round(diversification_ratio, 4),
        valueAtRiskHorizonDays=_var_horizon_days(frequency),
        valueAtRiskMethod="historisch",
        annualizedReturnGeometric=geometric_return,
    )


def _optimize_max_sharpe(
    mean_returns: pd.Series,
    covariance: pd.DataFrame,
    risk_free_rate: float,
    max_weight: float = OPTIMIZATION_MAX_WEIGHT,
    min_weight: float = 0.0,
) -> np.ndarray:
    weights, _ = _optimize_max_sharpe_with_status(mean_returns, covariance, risk_free_rate, max_weight, min_weight)
    return weights


def _optimize_max_sharpe_with_status(
    mean_returns: pd.Series,
    covariance: pd.DataFrame,
    risk_free_rate: float,
    max_weight: float = OPTIMIZATION_MAX_WEIGHT,
    min_weight: float = 0.0,
) -> tuple[np.ndarray, bool]:
    return _optimize_portfolio_with_status(
        mean_returns,
        covariance,
        risk_free_rate,
        objective="max_sharpe",
        max_weight=max_weight,
        min_weight=min_weight,
    )


def optimize_portfolio(
    mean_returns: pd.Series | np.ndarray,
    covariance: pd.DataFrame | np.ndarray,
    risk_free_rate: float,
    objective: str,
    max_weight: float,
    min_weight: float = 0.0,
) -> np.ndarray:
    """Optimiert ein Portfolio mit einem expliziten Ziel und Gewichtsgrenzen."""
    weights, _ = _optimize_portfolio_with_status(
        mean_returns,
        covariance,
        risk_free_rate,
        objective,
        max_weight,
        min_weight,
    )
    return weights


def _optimize_portfolio_with_status(
    mean_returns: pd.Series | np.ndarray,
    covariance: pd.DataFrame | np.ndarray,
    risk_free_rate: float,
    objective: str,
    max_weight: float,
    min_weight: float = 0.0,
) -> tuple[np.ndarray, bool]:
    # SciPy is only needed for optimization requests; importing it lazily keeps API startup responsive.
    from scipy.optimize import minimize

    returns_array = np.asarray(mean_returns, dtype=float)
    covariance_array = np.asarray(covariance, dtype=float)
    if returns_array.ndim != 1 or returns_array.size == 0:
        raise ValueError("mean_returns muss ein nichtleeres eindimensionales Array sein.")
    asset_count = returns_array.size
    if covariance_array.shape != (asset_count, asset_count) or not np.isfinite(covariance_array).all():
        raise ValueError("covariance muss eine endliche quadratische Matrix sein.")
    objective_name = objective
    if objective_name not in {"max_sharpe", "min_volatility", "max_diversification"}:
        raise ValueError(f"Unbekanntes Optimierungsziel: {objective}")

    covariance_array = (covariance_array + covariance_array.T) / 2
    covariance_array = np.asarray(_shrink_covariance(covariance_array), dtype=float)
    lower, upper = _optimization_bounds(asset_count, max_weight, min_weight)
    initial = np.repeat(1 / asset_count, asset_count)
    bounds = tuple((lower, upper) for _ in range(asset_count))
    constraints = ({"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},)
    individual_volatilities = np.sqrt(np.maximum(np.diag(covariance_array), 0.0))

    def objective_function(weights: np.ndarray) -> float:
        portfolio_volatility = float(np.sqrt(max(weights.T @ covariance_array @ weights, 0.0)))
        if objective_name == "min_volatility":
            return portfolio_volatility
        if objective_name == "max_diversification":
            if portfolio_volatility <= 0:
                return 1e6
            return -float(np.dot(weights, individual_volatilities) / portfolio_volatility)
        expected_return = float(np.dot(weights, returns_array))
        if portfolio_volatility <= 0:
            return 1e6
        return -((expected_return - risk_free_rate) / portfolio_volatility)

    result = minimize(objective_function, initial, method="SLSQP", bounds=bounds, constraints=constraints)
    if not result.success or not np.isfinite(result.x).all():
        return initial, False

    weights = _fit_weights_to_bounds(np.asarray(result.x, dtype=float), lower, upper)
    if weights is None:
        return initial, False
    return weights, True


def _optimization_bounds(asset_count: int, max_weight: float, min_weight: float) -> tuple[float, float]:
    lower = max(0.0, float(min_weight))
    upper = min(1.0, float(max_weight))
    upper = max(upper, 1 / asset_count)
    if lower > upper or lower * asset_count > 1 + 1e-9:
        raise ValueError("Die Gewichtsgrenzen lassen kein vollständig investiertes Portfolio zu.")
    return lower, upper


def _fit_weights_to_bounds(weights: np.ndarray, lower: float, upper: float) -> np.ndarray | None:
    fitted = np.clip(weights, lower, upper)
    for _ in range(len(fitted) + 2):
        difference = 1.0 - float(fitted.sum())
        if abs(difference) <= 1e-10:
            return fitted / fitted.sum()
        if difference > 0:
            capacity = np.maximum(upper - fitted, 0.0)
            capacity_sum = float(capacity.sum())
            if capacity_sum <= 1e-12:
                break
            fitted += capacity / capacity_sum * difference
        else:
            capacity = np.maximum(fitted - lower, 0.0)
            capacity_sum = float(capacity.sum())
            if capacity_sum <= 1e-12:
                break
            fitted -= capacity / capacity_sum * (-difference)
        fitted = np.clip(fitted, lower, upper)
    return fitted if abs(float(fitted.sum()) - 1.0) <= 1e-8 else None


def _shrink_covariance(covariance: pd.DataFrame | np.ndarray, intensity: float = OPTIMIZATION_SHRINKAGE_INTENSITY) -> pd.DataFrame | np.ndarray:
    """Zieht die Kovarianz in Richtung einer Matrix mit Durchschnittskorrelation."""
    value = np.asarray(covariance, dtype=float)
    if value.ndim != 2 or value.shape[0] != value.shape[1] or not np.isfinite(value).all():
        raise ValueError("Kovarianzmatrix muss endlich und quadratisch sein.")
    intensity = min(max(float(intensity), 0.0), 1.0)
    value = (value + value.T) / 2
    deviations = np.sqrt(np.maximum(np.diag(value), 1e-12))
    correlation = value / np.outer(deviations, deviations)
    off_diagonal = correlation[~np.eye(value.shape[0], dtype=bool)]
    average_correlation = float(np.mean(off_diagonal)) if off_diagonal.size else 0.0
    target = np.outer(deviations, deviations) * np.clip(average_correlation, -0.95, 0.95)
    np.fill_diagonal(target, np.diag(value))
    shrunk = (1 - intensity) * value + intensity * target
    if isinstance(covariance, pd.DataFrame):
        return pd.DataFrame(shrunk, index=covariance.index, columns=covariance.columns)
    return shrunk


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
                annualizedReturnGeometric=_annualized_geometric_return(prices[ticker]),
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
    if len(weights) <= 1:
        return 0.0
    effective_holdings = _effective_holdings(weights)
    return max(0.0, min(100.0, (effective_holdings - 1) / (len(weights) - 1) * 100))


def _effective_holdings(weights: np.ndarray) -> float:
    herfindahl = float(np.sum(np.square(weights)))
    return 1 / herfindahl if herfindahl > 0 else 0.0


def _var_horizon_days(frequency: str) -> int:
    return {"1d": 1, "1wk": 7, "1mo": 30}.get(frequency, 1)


def _annualized_geometric_return(series: pd.Series) -> float:
    clean = series.dropna()
    if len(clean) < 2 or float(clean.iloc[0]) <= 0 or float(clean.iloc[-1]) <= 0:
        return 0.0
    elapsed_years = max((clean.index[-1] - clean.index[0]).days / 365.25, 1 / 365.25)
    return float((float(clean.iloc[-1]) / float(clean.iloc[0])) ** (1 / elapsed_years) - 1)


def _portfolio_geometric_return(prices: pd.DataFrame, weights: np.ndarray) -> float:
    normalized = prices.div(prices.iloc[0])
    portfolio_values = normalized.mul(weights, axis=1).sum(axis=1)
    return _annualized_geometric_return(portfolio_values)


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
