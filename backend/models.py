from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Frequency = Literal["1d", "1wk", "1mo"]
InstrumentType = Literal["EQUITY", "ETF"]
FocusArea = Literal["summary", "sector", "concentration", "diversification", "risk_drivers"]
TimeHorizon = Literal["short_term", "mid_term", "long_term"]
RiskStyle = Literal["defensive", "balanced", "aggressive"]
GoalPreset = Literal["diversify_broadly", "keep_tech_focus", "defensive", "balanced"]
RecommendationSource = Literal["lmstudio", "ollama", "cloud", "rules"]
LlmPreference = Literal["auto", "local", "cloud"]
SentimentLabel = Literal["positive", "neutral", "negative", "mixed"]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tickers: list[str] = Field(min_length=2, max_length=10)
    weights: list[float] = Field(min_length=2, max_length=10)
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
    effective_holdings: float = Field(default=0.0, alias="effectiveHoldings")
    diversification_ratio: float = Field(default=0.0, alias="diversificationRatio")
    value_at_risk_horizon_days: int = Field(default=1, alias="valueAtRiskHorizonDays")
    value_at_risk_method: Literal["historisch"] = Field(default="historisch", alias="valueAtRiskMethod")
    annualized_return_geometric: float = Field(default=0.0, alias="annualizedReturnGeometric")

    model_config = ConfigDict(populate_by_name=True)


class RiskFinding(BaseModel):
    type: Literal["concentration", "correlation", "diversification", "volatility", "risk_return"]
    severity: Literal["low", "medium", "high"]
    message: str


class AssetResult(BaseModel):
    ticker: str
    name: str
    sector: str
    instrument_type: InstrumentType = Field(alias="instrumentType")
    weight: float
    expected_return: float = Field(alias="expectedReturn")
    volatility: float
    last_price: float = Field(alias="lastPrice")
    annualized_return_geometric: float = Field(default=0.0, alias="annualizedReturnGeometric")

    model_config = ConfigDict(populate_by_name=True)


class SectorAllocationItem(BaseModel):
    sector: str
    weight: float
    tickers: list[str]


class OptimizationSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    objective: str
    max_weight: float = Field(alias="maxWeight")
    shrinkage_intensity: float = Field(alias="shrinkageIntensity")
    converged: bool


class CorrelationMatrix(BaseModel):
    tickers: list[str]
    values: list[list[float]]


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["live", "demo"]
    data_source: str = Field(alias="dataSource")
    updated_at: datetime = Field(alias="updatedAt")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    frequency: Frequency
    risk_free_rate: float = Field(alias="riskFreeRate")
    var_confidence: float = Field(alias="varConfidence")
    assets: list[AssetResult]
    sector_allocation: list[SectorAllocationItem] = Field(alias="sectorAllocation")
    metrics: PortfolioMetrics
    optimized_metrics: PortfolioMetrics = Field(alias="optimizedMetrics")
    optimized_weights: list[float] = Field(alias="optimizedWeights")
    risk_findings: list[RiskFinding] = Field(alias="riskFindings")
    correlation_matrix: CorrelationMatrix = Field(alias="correlationMatrix")
    covariance_matrix: list[list[float]] = Field(alias="covarianceMatrix")
    performance: list[dict[str, float | str]]
    optimization_settings: OptimizationSettings = Field(alias="optimizationSettings")
    recommendations: list[str]
    recommendation_source: Literal["rules"] = Field(alias="recommendationSource")
    disclaimer: str


class InvestorProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    time_horizon: TimeHorizon = Field(alias="timeHorizon")
    risk_style: RiskStyle = Field(alias="riskStyle")


class RecommendRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    analysis: dict[str, Any]
    focus_areas: list[FocusArea] = Field(alias="focusAreas", min_length=1)
    investor_profile: InvestorProfile = Field(alias="investorProfile")
    goal_preset: GoalPreset = Field(alias="goalPreset")
    goal_note: str | None = Field(default=None, alias="goalNote", max_length=600)
    model: str | None = None
    llm_preference: LlmPreference = Field(default="auto", alias="llmPreference")


class WeightAdjustment(BaseModel):
    ticker: str
    current_weight: float = Field(alias="currentWeight")
    suggested_weight: float = Field(alias="suggestedWeight")
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class NewIdea(BaseModel):
    ticker: str
    name: str
    sector: str
    reason: str


class ReviewCandidate(BaseModel):
    ticker: str
    reason: str


class NewsSignal(BaseModel):
    ticker: str
    headline: str
    sentiment_label: SentimentLabel = Field(alias="sentimentLabel")
    url: str

    model_config = ConfigDict(populate_by_name=True)


class OptimizationBasis(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    objective: str = "max_sharpe"
    max_weight: float = Field(default=0.35, alias="maxWeight")
    description: str = "Neutrale historische Max-Sharpe-Vergleichsvariante."


class RecommendResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    summary: str
    profile_fit: str = Field(alias="profileFit")
    analysis_highlights: list[str] = Field(alias="analysisHighlights")
    sector_insights: list[str] = Field(alias="sectorInsights")
    action_items: list[str] = Field(alias="actionItems")
    weight_adjustments: list[WeightAdjustment] = Field(alias="weightAdjustments")
    new_ideas: list[NewIdea] = Field(alias="newIdeas")
    review_candidates: list[ReviewCandidate] = Field(alias="reviewCandidates")
    news_signals: list[NewsSignal] = Field(alias="newsSignals")
    source: RecommendationSource
    model: str
    disclaimer: str
    optimization_basis: OptimizationBasis = Field(default_factory=OptimizationBasis, alias="optimizationBasis")
    fallback_reason: str | None = Field(default=None, alias="fallbackReason")
    attempted_backends: list[str] = Field(default_factory=list, alias="attemptedBackends")
    news_available: bool = Field(default=True, alias="newsAvailable")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class PortfolioPreview(BaseModel):
    tickers: list[str] = Field(default_factory=list, max_length=10)
    weights: list[float] = Field(default_factory=list, max_length=10)


class WizardProposal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    focus_areas: list[FocusArea] = Field(alias="focusAreas", min_length=1, max_length=5)
    time_horizon: TimeHorizon = Field(alias="timeHorizon")
    risk_style: RiskStyle = Field(alias="riskStyle")
    goal_preset: GoalPreset = Field(alias="goalPreset")
    goal_note: str = Field(alias="goalNote", max_length=600)
    reasoning: str = Field(max_length=600)


class GoalChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    messages: list[ChatMessage] = Field(default_factory=list, max_length=20)
    portfolio_preview: PortfolioPreview | None = Field(default=None, alias="portfolioPreview")
    current_selection: WizardProposal | None = Field(default=None, alias="currentSelection")


class GoalChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reply: str = Field(max_length=1500)
    follow_up_question: str | None = Field(default=None, alias="followUpQuestion", max_length=600)
    proposal: WizardProposal | None = None
    confidence: Literal["low", "medium", "high"]
    source: Literal["ollama", "rules"]
    fallback_reason: str | None = Field(default=None, alias="fallbackReason")
    disclaimer: str


class AskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(max_length=600)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    analysis: dict[str, Any]
    recommendation: RecommendResponse | None = None
    llm_preference: LlmPreference = Field(default="auto", alias="llmPreference")


class AskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    answer: str = Field(max_length=1500)
    used_metrics: list[str] = Field(default_factory=list, alias="usedMetrics")
    source: Literal["ollama", "cloud", "rules"]
    fallback_reason: str | None = Field(default=None, alias="fallbackReason")
    disclaimer: str


class SecuritySearchResult(BaseModel):
    symbol: str
    name: str
    type: Literal["EQUITY", "ETF"]
    exchange: str


class SecuritySearchResponse(BaseModel):
    results: list[SecuritySearchResult]


class ExportRequest(BaseModel):
    analysis: AnalysisResponse
    recommendations: list[str] | None = None
    portfolio_name: str = Field(default="Portfolioanalyse", alias="portfolioName", max_length=120)

    model_config = ConfigDict(populate_by_name=True)
