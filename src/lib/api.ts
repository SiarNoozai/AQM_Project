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
  mode: "live" | "demo";
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

export type ExportFormat = "csv" | "pdf";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const REQUEST_TIMEOUT_MS = 10000;
const SEARCH_TIMEOUT_MS = 2500;

export async function analyzePortfolio(payload: AnalyzePayload) {
  return postJson<ApiAnalysis>("/api/analyze", payload, REQUEST_TIMEOUT_MS);
}

export async function recommendPortfolio(payload: RecommendPayload) {
  return postJson<RecommendationResult>("/api/recommend", payload, REQUEST_TIMEOUT_MS);
}

export async function searchSecurities(query: string, limit = 8) {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
  });
  return getJson<SecuritySearchResponse>(`/api/securities/search?${params.toString()}`, SEARCH_TIMEOUT_MS);
}

export async function exportPortfolioReport(
  format: ExportFormat,
  analysis: ApiAnalysis,
  recommendations?: string[],
) {
  const response = await request(
    `${API_BASE_URL}/api/export/${format}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ analysis, recommendations }),
    },
    REQUEST_TIMEOUT_MS,
  );

  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  return response.blob();
}

async function postJson<T>(path: string, payload: unknown, timeoutMs: number): Promise<T> {
  const response = await request(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  }, timeoutMs);

  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  return response.json() as Promise<T>;
}

async function getJson<T>(path: string, timeoutMs: number): Promise<T> {
  const response = await request(`${API_BASE_URL}${path}`, undefined, timeoutMs);

  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  return response.json() as Promise<T>;
}

async function request(input: RequestInfo | URL, init?: RequestInit, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } catch (caughtError) {
    if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
      throw new Error("Die Anfrage hat zu lange gedauert. Bitte versuche es erneut.");
    }
    if (caughtError instanceof TypeError) {
      throw new Error(
        "Backend nicht erreichbar. Bitte starte das FastAPI-Backend auf Port 8000 neu oder nutze den Vite-Proxy.",
      );
    }
    throw caughtError;
  } finally {
    window.clearTimeout(timeoutId);
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
