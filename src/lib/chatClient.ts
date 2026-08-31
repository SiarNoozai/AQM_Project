import type { ApiAnalysis, FocusArea, GoalPreset, InvestorProfile, LlmPreference, RecommendationResult, RiskStyle, TimeHorizon } from "./api";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type WizardProposal = {
  focusAreas: FocusArea[];
  timeHorizon: TimeHorizon;
  riskStyle: RiskStyle;
  goalPreset: GoalPreset;
  goalNote: string;
  reasoning: string;
};

export type GoalChatResponse = {
  reply: string;
  followUpQuestion: string | null;
  proposal: WizardProposal | null;
  confidence: "low" | "medium" | "high";
  source: "ollama" | "rules";
  fallbackReason: string | null;
  disclaimer: string;
};

export type AskResponse = {
  answer: string;
  usedMetrics: string[];
  source: "ollama" | "cloud" | "rules";
  fallbackReason: string | null;
  disclaimer: string;
};

export type GoalChatPayload = {
  messages: ChatMessage[];
  portfolioPreview?: { tickers: string[]; weights: number[] };
  currentSelection?: WizardProposal;
};

export type AskPayload = {
  question: string;
  history: ChatMessage[];
  analysis: ApiAnalysis;
  recommendation?: RecommendationResult;
  llmPreference?: LlmPreference;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const CHAT_TIMEOUT_MS = 90000;

export function sendGoalChatMessage(payload: GoalChatPayload) {
  return postJson<GoalChatResponse>("/api/goal-chat", payload);
}

export function askQuestion(payload: AskPayload) {
  return postJson<AskResponse>("/api/ask", payload);
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(await readApiError(response));
    }
    return (await response.json()) as T;
  } catch (caughtError) {
    if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
      throw new Error("Die Chat-Anfrage hat zu lange gedauert. Bitte versuche es erneut.");
    }
    if (caughtError instanceof TypeError) {
      throw new Error("Backend nicht erreichbar. Bitte starte das FastAPI-Backend auf Port 8000 neu.");
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
    return `API-Anfrage fehlgeschlagen (Status ${response.status}).`;
  }
}
