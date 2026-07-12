export type ApiInstrumentType = "EQUITY" | "ETF";
export type FocusArea = "summary" | "sector" | "concentration" | "diversification" | "risk_drivers";
export type TimeHorizon = "short_term" | "mid_term" | "long_term";
export type RiskStyle = "defensive" | "balanced" | "aggressive";
export type GoalPreset = "diversify_broadly" | "keep_tech_focus" | "defensive" | "balanced";

export type ApiAsset = {
  ticker: string;
  name: string;
  sector: string;
  instrumentType: ApiInstrumentType;
  weight: number;
  expectedReturn: number;
  volatility: number;
  lastPrice: number;
};

export type ApiRiskFinding = {
  type: "concentration" | "correlation" | "diversification" | "volatility" | "risk_return";
  severity: "low" | "medium" | "high";
  message: string;
};

export type ApiMetrics = {
  expectedReturn: number;
  volatility: number;
  sharpeRatio: number;
  valueAtRisk: number;
  diversificationScore: number;
};

export type ApiSectorAllocation = {
  sector: string;
  weight: number;
  tickers: string[];
};

export type ApiAnalysis = {
  mode: "live";
  dataSource: string;
  updatedAt: string;
  startDate: string;
  endDate: string;
  frequency: "1d" | "1wk" | "1mo";
  riskFreeRate: number;
  varConfidence: number;
  assets: ApiAsset[];
  sectorAllocation: ApiSectorAllocation[];
  metrics: ApiMetrics;
  optimizedMetrics: ApiMetrics;
  optimizedWeights: number[];
  riskFindings: ApiRiskFinding[];
  correlationMatrix: {
    tickers: string[];
    values: number[][];
  };
  covarianceMatrix: number[][];
  performance: Array<Record<string, number | string>>;
  frontier: Array<Record<string, number | string | number[]>>;
  recommendations: string[];
  recommendationSource: "rules";
  disclaimer: string;
};

export type AnalyzePayload = {
  tickers: string[];
  weights: number[];
  startDate: string;
  endDate: string;
  frequency: "1d" | "1wk" | "1mo";
  riskFreeRate: number;
  varConfidence: number;
};

export type InvestorProfile = {
  timeHorizon: TimeHorizon;
  riskStyle: RiskStyle;
};

export type RecommendationWeightAdjustment = {
  ticker: string;
  currentWeight: number;
  suggestedWeight: number;
  reason: string;
};

export type RecommendationIdea = {
  ticker: string;
  name: string;
  sector: string;
  reason: string;
};

export type RecommendationReviewCandidate = {
  ticker: string;
  reason: string;
};

export type RecommendationNewsSignal = {
  ticker: string;
  headline: string;
  sentimentLabel: "positive" | "neutral" | "negative" | "mixed";
  url: string;
};

export type RecommendationResult = {
  summary: string;
  profileFit: string;
  analysisHighlights: string[];
  sectorInsights: string[];
  actionItems: string[];
  weightAdjustments: RecommendationWeightAdjustment[];
  newIdeas: RecommendationIdea[];
  reviewCandidates: RecommendationReviewCandidate[];
  newsSignals: RecommendationNewsSignal[];
  source: "ollama" | "rules";
  model: string;
  disclaimer: string;
};

export type RecommendPayload = {
  analysis: ApiAnalysis;
  focusAreas: FocusArea[];
  investorProfile: InvestorProfile;
  goalPreset: GoalPreset;
  goalNote?: string;
  model?: string;
};

export type SecuritySearchResult = {
  symbol: string;
  name: string;
  type: "EQUITY" | "ETF";
  exchange: string;
};

export type SecuritySearchResponse = {
  results: SecuritySearchResult[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function analyzePortfolio(payload: AnalyzePayload) {
  return postJson<ApiAnalysis>("/api/analyze", payload);
}

export async function recommendPortfolio(payload: RecommendPayload) {
  return postJson<RecommendationResult>("/api/recommend", payload);
}

export async function searchSecurities(query: string, limit = 8) {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
  });
  return getJson<SecuritySearchResponse>(`/api/securities/search?${params.toString()}`);
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await request(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  return response.json() as Promise<T>;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await request(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  return response.json() as Promise<T>;
}

async function request(input: RequestInfo | URL, init?: RequestInit) {
  try {
    return await fetch(input, init);
  } catch (caughtError) {
    if (caughtError instanceof TypeError) {
      throw new Error(
        "Backend nicht erreichbar. Bitte starte das FastAPI-Backend auf Port 8000 neu oder nutze den Vite-Proxy.",
      );
    }
    throw caughtError;
  }
}

async function readApiError(response: Response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail)) {
      return body.detail.map((item: { msg?: string }) => item.msg ?? JSON.stringify(item)).join(" ");
    }
    return JSON.stringify(body);
  } catch {
    return `API request failed with status ${response.status}.`;
  }
}
