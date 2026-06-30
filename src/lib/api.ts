export type ApiAsset = {
  ticker: string;
  weight: number;
  expectedReturn: number;
  volatility: number;
  lastPrice: number;
};

export type ApiAssetAllocation = {
  bySecurity: Record<string, number>;
  byAssetClass: Record<string, number>;
  bySector: Record<string, number>;
  byRegion: Record<string, number>;
};

export type ApiRiskFinding = {
  type:
    | "concentration"
    | "correlation"
    | "diversification"
    | "volatility"
    | "risk_return"
    | "allocation"
    | "behavioral";
  severity: "low" | "medium" | "high";
  message: string;
  affectedAssets: string[];
};

export type ApiMetrics = {
  expectedReturn: number;
  volatility: number;
  sharpeRatio: number;
  valueAtRisk: number;
  diversificationScore: number;
};

export type ApiFrontierPoint = {
  id: number;
  risk: number;
  return: number;
  sharpe: number;
  weights: number[];
  kind: "simulation" | "current" | "optimized";
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
  metrics: ApiMetrics;
  optimizedMetrics: ApiMetrics;
  optimizedWeights: number[];
  assetAllocation: ApiAssetAllocation;
  riskFindings: ApiRiskFinding[];
  correlationMatrix: {
    tickers: string[];
    values: number[][];
  };
  covarianceMatrix: number[][];
  performance: Array<Record<string, number | string>>;
  frontier: ApiFrontierPoint[];
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

export type RecommendationResult = {
  recommendations: string[];
  source: "ollama" | "rules";
  model: string;
  disclaimer: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function analyzePortfolio(payload: AnalyzePayload) {
  return postJson<ApiAnalysis>("/api/analyze", payload);
}

export async function recommendPortfolio(analysis: ApiAnalysis) {
  return postJson<RecommendationResult>("/api/recommend", { analysis });
}

export async function downloadExport(kind: "csv" | "pdf", analysis: ApiAnalysis, recommendations: string[]) {
  const response = await fetch(`${API_BASE_URL}/api/export/${kind}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ analysis, recommendations }),
  });

  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  const blob = await response.blob();
  const extension = kind === "csv" ? "csv" : "pdf";
  const mimePrefix = kind === "csv" ? "text/csv" : "application/pdf";
  const url = URL.createObjectURL(new Blob([blob], { type: mimePrefix }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `portfolio-analyse.${extension}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
