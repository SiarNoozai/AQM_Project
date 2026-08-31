import type { ApiAnalysis } from "./api";

export type ExportFormat = "csv" | "pdf";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const EXPORT_TIMEOUT_MS = 10000;

export async function exportPortfolioReport(
  format: ExportFormat,
  analysis: ApiAnalysis,
  recommendations?: string[],
  portfolioName?: string,
) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), EXPORT_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/api/export/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis, recommendations, portfolioName }),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(await readApiError(response));
    }
    return response.blob();
  } catch (caughtError) {
    if (caughtError instanceof DOMException && caughtError.name === "AbortError") {
      throw new Error("Der Export hat zu lange gedauert. Bitte versuche es erneut.");
    }
    if (caughtError instanceof TypeError) {
      throw new Error("Backend nicht erreichbar. Bitte starte das FastAPI-Backend neu.");
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
    return JSON.stringify(body);
  } catch {
    return `Export fehlgeschlagen (Status ${response.status}).`;
  }
}
