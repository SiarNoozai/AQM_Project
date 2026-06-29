from __future__ import annotations

from datetime import datetime, timezone
from statistics import NormalDist

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import HTTPException
from scipy.optimize import minimize

from .models import (
    AnalysisResponse,
    AnalyzeRequest,
    AssetResult,
    CorrelationMatrix,
    FrontierPoint,
    PortfolioMetrics,
)


DISCLAIMER = (
    "Dies ist keine Anlageberatung. Die Analyse basiert auf historischen Yahoo-Finance-Daten "
    "ueber yfinance und bietet keine Prognosegarantie."
)


def run_analysis(request: AnalyzeRequest) -> AnalysisResponse:
    prices = _download_prices(request)
    returns = _calculate_returns(prices, request.frequency)
    if returns.empty or len(returns) < 10:
        raise HTTPException(
            status_code=422,
            detail="Nicht genug Kursdaten fuer eine belastbare Analyse gefunden.",
        )

    weights = _normalize_weights(np.array(request.weights, dtype=float))
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
    asset_results = _build_asset_results(request.tickers, weights, mean_returns, covariance, prices)

    return AnalysisResponse(
        mode="live",
        dataSource="Yahoo Finance via yfinance",
        updatedAt=datetime.now(timezone.utc),
        startDate=request.start_date,
        endDate=request.end_date,
        frequency=request.frequency,
        riskFreeRate=request.risk_free_rate,
        varConfidence=request.var_confidence,
        assets=asset_results,
        metrics=current_metrics,
        optimizedMetrics=optimized_metrics,
        optimizedWeights=[float(value) for value in optimized_weights],
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
        ),
        recommendationSource="rules",
        disclaimer=DISCLAIMER,
    )


def build_rule_recommendations(
    tickers: list[str],
    weights: np.ndarray | list[float],
    metrics: dict[str, float],
    optimized_metrics: dict[str, float],
    optimized_weights: np.ndarray | list[float],
) -> list[str]:
    weight_array = np.array(weights, dtype=float)
    optimized_array = np.array(optimized_weights, dtype=float)
    dominant_index = int(np.argmax(weight_array))
    largest_shift_index = int(np.argmax(np.abs(optimized_array - weight_array)))
    sharpe_delta = optimized_metrics["sharpeRatio"] - metrics["sharpeRatio"]
    risk_change = optimized_metrics["volatility"] - metrics["volatility"]

    return [
        (
            f"Die groesste Einzelposition ist {tickers[dominant_index]} mit "
            f"{weight_array[dominant_index] * 100:.1f} Prozent. Pruefe, ob diese Konzentration "
            "zu deinem Risikoprofil passt."
        ),
        (
            f"Die Max-Sharpe-Optimierung verschiebt {tickers[largest_shift_index]} am staerksten "
            f"auf {optimized_array[largest_shift_index] * 100:.1f} Prozent."
        ),
        (
            f"Das optimierte Portfolio veraendert die Sharpe Ratio um {sharpe_delta:.2f} Punkte "
            f"und die Volatilitaet um {risk_change * 100:+.1f} Prozentpunkte."
        ),
        (
            f"Der historische Value at Risk liegt bei etwa {metrics['valueAtRisk'] * 100:.1f} Prozent "
            "fuer den betrachteten Zeitraum. Dieser Wert ist ein historisches Risikomass, keine Verlustgrenze."
        ),
    ]


def _download_prices(request: AnalyzeRequest) -> pd.DataFrame:
    try:
        data = yf.download(
            tickers=request.tickers,
            start=request.start_date.isoformat(),
            end=request.end_date.isoformat(),
            interval=request.frequency,
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
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
) -> list[AssetResult]:
    results: list[AssetResult] = []
    for index, ticker in enumerate(tickers):
        results.append(
            AssetResult(
                ticker=ticker,
                weight=float(weights[index]),
                expectedReturn=float(mean_returns[ticker]),
                volatility=float(np.sqrt(covariance.loc[ticker, ticker])),
                lastPrice=float(prices[ticker].iloc[-1]),
            )
        )
    return results


def _matrix_to_lists(matrix: pd.DataFrame) -> list[list[float]]:
    return [[round(float(value), 6) for value in row] for row in matrix.to_numpy()]


def _diversification_score(weights: np.ndarray) -> float:
    herfindahl = float(np.sum(weights * weights))
    return max(0.0, min(100.0, (1 - herfindahl) * 140))
