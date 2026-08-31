import { describe, expect, it } from "vitest";
import { calculateDiversificationScore, calculateHistoricalValueAtRisk, normalizeWeights } from "./portfolioMath";
import { initialAssets } from "../data/assets";

describe("portfolioMath", () => {
  it("normalizes weights", () => {
    const assets = initialAssets.map((asset, index) => ({ ...asset, weight: index + 1 }));
    expect(normalizeWeights(assets).reduce((sum, weight) => sum + weight, 0)).toBeCloseTo(1);
    expect(normalizeWeights(assets)[0]).toBeCloseTo(0.1);
  });

  it("uses the effective-holdings diversification formula", () => {
    expect(calculateDiversificationScore([0.25, 0.25, 0.25, 0.25])).toBeCloseTo(100);
    expect(calculateDiversificationScore([0.35, 0.3, 0.25, 0.1])).toBeCloseTo(83.63, 1);
  });

  it("calculates a historical lower-tail quantile", () => {
    expect(calculateHistoricalValueAtRisk([-0.1, -0.05, 0.01, 0.02], 0.75)).toBeCloseTo(0.0625);
  });
});
