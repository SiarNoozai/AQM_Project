import { AssetInput, baseCorrelationMatrix } from "../data/assets";

export function normalizeWeights(assets: AssetInput[]) {
  const total = assets.reduce((sum, asset) => sum + Math.max(asset.weight, 0), 0);

  if (total === 0) {
    return assets.map(() => 1 / assets.length);
  }

  return assets.map((asset) => Math.max(asset.weight, 0) / total);
}

export function calculateHistoricalValueAtRisk(returns: number[], confidence = 0.95) {
  if (returns.length === 0) {
    return 0;
  }
  const sorted = [...returns].sort((left, right) => left - right);
  const position = (1 - confidence) * (sorted.length - 1);
  const lowerIndex = Math.floor(position);
  const upperIndex = Math.ceil(position);
  const fraction = position - lowerIndex;
  const quantile = sorted[lowerIndex] + (sorted[upperIndex] - sorted[lowerIndex]) * fraction;
  return Math.abs(quantile);
}

export function calculatePortfolioVolatility(assets: AssetInput[], weights: number[]) {
  let variance = 0;

  for (let row = 0; row < assets.length; row += 1) {
    for (let column = 0; column < assets.length; column += 1) {
      const correlation = baseCorrelationMatrix[row]?.[column] ?? (row === column ? 1 : 0.4);
      variance +=
        weights[row] *
        weights[column] *
        assets[row].volatility *
        assets[column].volatility *
        correlation;
    }
  }

  return Math.sqrt(Math.max(variance, 0));
}

export function formatPercent(value: number) {
  return new Intl.NumberFormat("de-DE", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

export function calculateEffectiveHoldings(weights: number[]) {
  const herfindahl = weights.reduce((sum, weight) => sum + weight * weight, 0);
  return herfindahl > 0 ? Number((1 / herfindahl).toFixed(1)) : 0;
}

export function calculateDiversificationScore(weights: number[]) {
  if (weights.length <= 1) {
    return 0;
  }
  const herfindahl = weights.reduce((sum, weight) => sum + weight * weight, 0);
  const effectiveHoldings = herfindahl > 0 ? 1 / herfindahl : 0;
  return Math.max(0, Math.min(100, ((effectiveHoldings - 1) / (weights.length - 1)) * 100));
}

export function calculateDiversificationRatio(assets: AssetInput[], weights: number[]) {
  const numerator = assets.reduce((sum, asset, index) => sum + (weights[index] ?? 0) * asset.volatility, 0);
  const volatility = calculatePortfolioVolatility(assets, weights);
  return volatility > 0 ? numerator / volatility : 0;
}
