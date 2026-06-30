from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Frequency = Literal["1d", "1wk", "1mo"]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tickers: list[str] = Field(min_length=2, max_length=8)
    weights: list[float] = Field(min_length=2, max_length=8)
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    frequency: Frequency = "1d"
    risk_free_rate: float = Field(0.025, alias="riskFreeRate", ge=0, le=0.2)
    var_confidence: float = Field(0.95, alias="varConfidence", gt=0.5, lt=1)

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, value: list[str]) -> list[str]:
        normalized = [ticker.strip().upper() for ticker in value if ticker.strip()]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Tickers must be unique.")
        return normalized

    @model_validator(mode="after")
    def validate_shape(self) -> "AnalyzeRequest":
        if len(self.tickers) != len(self.weights):
            raise ValueError("Tickers and weights must have the same length.")
        if self.end_date <= self.start_date:
            raise ValueError("endDate must be after startDate.")
        if any(weight < 0 for weight in self.weights):
            raise ValueError("Weights must be non-negative.")
        if sum(self.weights) <= 0:
            raise ValueError("Weight sum must be greater than zero.")
        return self


class PortfolioMetrics(BaseModel):
    expected_return: float = Field(alias="expectedReturn")
    volatility: float
    sharpe_ratio: float = Field(alias="sharpeRatio")
    value_at_risk: float = Field(alias="valueAtRisk")
    diversification_score: float = Field(alias="diversificationScore")

    model_config = ConfigDict(populate_by_name=True)


class RiskContribution(BaseModel):
    volatility_contribution: float = Field(alias="volatilityContribution")
    percent_contribution: float = Field(alias="percentContribution")
    method: str

    model_config = ConfigDict(populate_by_name=True)


class AssetResult(BaseModel):
    ticker: str
    weight: float
    expected_return: float = Field(alias="expectedReturn")
    volatility: float
    last_price: float = Field(alias="lastPrice")
    asset_class: str = Field(alias="assetClass")
    sector: str
    region: str
    metadata_status: Literal["known", "inferred", "unknown"] = Field(alias="metadataStatus")
    risk_contribution: RiskContribution = Field(alias="riskContribution")

    model_config = ConfigDict(populate_by_name=True)


class AssetAllocation(BaseModel):
    by_security: dict[str, float] = Field(alias="bySecurity")
    by_asset_class: dict[str, float] = Field(alias="byAssetClass")
    by_sector: dict[str, float] = Field(alias="bySector")
    by_region: dict[str, float] = Field(alias="byRegion")

    model_config = ConfigDict(populate_by_name=True)


class RiskFinding(BaseModel):
    type: Literal["concentration", "correlation", "diversification", "volatility", "risk_return", "allocation", "behavioral"]
    severity: Literal["low", "medium", "high"]
    message: str
    affected_assets: list[str] = Field(default_factory=list, alias="affectedAssets")

    model_config = ConfigDict(populate_by_name=True)


class FrontierPoint(BaseModel):
    id: int
    risk: float
    return_: float = Field(alias="return")
    sharpe: float
    weights: list[float]
    kind: Literal["simulation", "current", "optimized"]

    model_config = ConfigDict(populate_by_name=True)


class StrategyResult(BaseModel):
    id: Literal["low_volatility", "diversified", "return_oriented", "max_sharpe"]
    name: str
    description: str
    weights: list[float]
    metrics: PortfolioMetrics
    weight_delta: list[float] = Field(alias="weightDelta")
    diversification_note: str = Field(alias="diversificationNote")

    model_config = ConfigDict(populate_by_name=True)


class ReportSection(BaseModel):
    title: str
    content: str


class CorrelationMatrix(BaseModel):
    tickers: list[str]
    values: list[list[float]]


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["live"]
    data_source: str = Field(alias="dataSource")
    updated_at: datetime = Field(alias="updatedAt")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    frequency: Frequency
    risk_free_rate: float = Field(alias="riskFreeRate")
    var_confidence: float = Field(alias="varConfidence")
    assets: list[AssetResult]
    metrics: PortfolioMetrics
    optimized_metrics: PortfolioMetrics = Field(alias="optimizedMetrics")
    optimized_weights: list[float] = Field(alias="optimizedWeights")
    asset_allocation: AssetAllocation = Field(alias="assetAllocation")
    risk_findings: list[RiskFinding] = Field(alias="riskFindings")
    strategies: list[StrategyResult]
    correlation_matrix: CorrelationMatrix = Field(alias="correlationMatrix")
    covariance_matrix: list[list[float]] = Field(alias="covarianceMatrix")
    performance: list[dict[str, float | str]]
    frontier: list[FrontierPoint]
    recommendations: list[str]
    recommendation_source: Literal["rules"] = Field(alias="recommendationSource")
    disclaimer: str


class RecommendRequest(BaseModel):
    analysis: dict[str, Any]
    model: str | None = None


class RecommendResponse(BaseModel):
    recommendations: list[str]
    report: list[ReportSection] = Field(default_factory=list)
    source: Literal["ollama", "rules"]
    model: str
    disclaimer: str


class AskRequest(BaseModel):
    analysis: dict[str, Any]
    question: str = Field(min_length=3, max_length=500)
    model: str | None = None


class AskResponse(BaseModel):
    answer: str
    source: Literal["ollama", "rules"]
    model: str
    disclaimer: str


class ExportRequest(BaseModel):
    analysis: dict[str, Any]
    recommendations: list[str] | None = None
