import type { ApiAnalysis } from "./api";
import type { AssetInput } from "../data/assets";

const STORAGE_KEY = "portfolio-risk-tool.saved-portfolios.v1";

export type SavedPortfolio = {
  id: string;
  name: string;
  assets: AssetInput[];
  createdAt: string;
  updatedAt: string;
  lastAnalysis?: ApiAnalysis;
};

export function loadSavedPortfolios(): SavedPortfolio[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isSavedPortfolio);
  } catch {
    return [];
  }
}

export function savePortfolioRecord(
  existing: SavedPortfolio[],
  name: string,
  assets: AssetInput[],
  lastAnalysis?: ApiAnalysis | null,
): SavedPortfolio[] {
  const trimmedName = name.trim() || "Unbenanntes Portfolio";
  const now = new Date().toISOString();
  const current = existing.find((item) => item.name.toLowerCase() === trimmedName.toLowerCase());
  const next: SavedPortfolio = {
    id: current?.id ?? crypto.randomUUID(),
    name: trimmedName,
    assets: assets.map((asset) => ({ ...asset })),
    createdAt: current?.createdAt ?? now,
    updatedAt: now,
    lastAnalysis: lastAnalysis ?? current?.lastAnalysis,
  };
  const records = [next, ...existing.filter((item) => item.id !== next.id)];
  persistSavedPortfolios(records);
  return records;
}

export function deletePortfolioRecord(existing: SavedPortfolio[], id: string): SavedPortfolio[] {
  const records = existing.filter((item) => item.id !== id);
  persistSavedPortfolios(records);
  return records;
}

function persistSavedPortfolios(records: SavedPortfolio[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

function isSavedPortfolio(value: unknown): value is SavedPortfolio {
  if (!value || typeof value !== "object") return false;
  const record = value as SavedPortfolio;
  return typeof record.id === "string" && typeof record.name === "string" && Array.isArray(record.assets);
}
