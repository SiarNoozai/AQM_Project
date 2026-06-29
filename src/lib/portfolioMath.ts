import { AssetInput, baseCorrelationMatrix } from "../data/assets";

export type PortfolioMetrics = {
  expectedReturn: number;
  volatility: number;
  sharpeRatio: number;
  valueAtRisk: number;
  diversificationScore: number;
};

export type FrontierPoint = {
  id: number;
  risk: number;
  return: number;
  sharpe: number;
  weights: number[];
  kind: "simulation" | "current" | "optimized";
};

export type PerformancePoint = {
  month: string;
  portfolio: number;
  optimized: number;
  [ticker: string]: string | number;
};

const riskFreeRate = 0.025;

const monthLabels = [
  "Jan",
  "Feb",
  "Mrz",
  "Apr",
  "Mai",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Okt",
  "Nov",
  "Dez",
];

export function normalizeWeights(assets: AssetInput[]) {
  const total = assets.reduce((sum, asset) => sum + Math.max(asset.weight, 0), 0);

  if (total === 0) {
    return assets.map(() => 1 / assets.length);
  }

  return assets.map((asset) => Math.max(asset.weight, 0) / total);
}

export function calculatePortfolioMetrics(
  assets: AssetInput[],
  weights = normalizeWeights(assets),
): PortfolioMetrics {
  const expectedReturn = weights.reduce(
    (sum, weight, index) => sum + weight * assets[index].expectedReturn,
    0,
  );
  const volatility = calculatePortfolioVolatility(assets, weights);
  const sharpeRatio = volatility > 0 ? (expectedReturn - riskFreeRate) / volatility : 0;
  const valueAtRisk = expectedReturn / 252 - 1.65 * (volatility / Math.sqrt(252));
  const diversificationScore = calculateDiversificationScore(weights);

  return {
    expectedReturn,
    volatility,
    sharpeRatio,
    valueAtRisk: Math.abs(valueAtRisk),
    diversificationScore,
  };
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

export function buildEfficientFrontier(assets: AssetInput[], currentWeights: number[]) {
  const points: FrontierPoint[] = [];

  for (let index = 0; index < 150; index += 1) {
    const rawWeights = assets.map((_, assetIndex) => {
      const base = Math.abs(Math.sin((index + 2) * (assetIndex + 1.7)));
      const tilt = assetIndex === 3 ? 0.6 : 1;
      return base * tilt + 0.08;
    });
    const total = rawWeights.reduce((sum, value) => sum + value, 0);
    const weights = rawWeights.map((value) => value / total);
    const metrics = calculatePortfolioMetrics(assets, weights);

    points.push({
      id: index,
      risk: metrics.volatility,
      return: metrics.expectedReturn,
      sharpe: metrics.sharpeRatio,
      weights,
      kind: "simulation",
    });
  }

  const currentMetrics = calculatePortfolioMetrics(assets, currentWeights);
  const optimized = points.reduce((best, point) => (point.sharpe > best.sharpe ? point : best), points[0]);

  return [
    ...points,
    {
      id: 900,
      risk: currentMetrics.volatility,
      return: currentMetrics.expectedReturn,
      sharpe: currentMetrics.sharpeRatio,
      weights: currentWeights,
      kind: "current" as const,
    },
    {
      ...optimized,
      id: 901,
      kind: "optimized" as const,
    },
  ];
}

export function getOptimizedPoint(frontier: FrontierPoint[]) {
  return frontier.find((point) => point.kind === "optimized") ?? frontier[0];
}

export function buildPerformanceSeries(
  assets: AssetInput[],
  currentWeights: number[],
  optimizedWeights: number[],
): PerformancePoint[] {
  const assetSeries = assets.map((asset, assetIndex) => {
    let value = 100;

    return Array.from({ length: 24 }, (_, monthIndex) => {
      const trend = asset.expectedReturn / 12;
      const seasonal =
        Math.sin((monthIndex + 1) * (assetIndex + 1) * 0.72) * asset.volatility * 0.08;
      const shock = Math.cos((monthIndex + 2) * (assetIndex + 2) * 0.33) * asset.volatility * 0.04;
      value *= 1 + trend + seasonal + shock;
      return value;
    });
  });

  return Array.from({ length: 24 }, (_, monthIndex) => {
    const row: PerformancePoint = {
      month: `${monthLabels[monthIndex % 12]} ${monthIndex < 12 ? "25" : "26"}`,
      portfolio: 0,
      optimized: 0,
    };

    assets.forEach((asset, assetIndex) => {
      const value = assetSeries[assetIndex][monthIndex];
      row[asset.ticker] = Number(value.toFixed(1));
      row.portfolio += currentWeights[assetIndex] * value;
      row.optimized += optimizedWeights[assetIndex] * value;
    });

    row.portfolio = Number(row.portfolio.toFixed(1));
    row.optimized = Number(row.optimized.toFixed(1));
    return row;
  });
}

export function buildRecommendations(
  assets: AssetInput[],
  currentWeights: number[],
  current: PortfolioMetrics,
  optimized: FrontierPoint,
) {
  const dominantAssetIndex = currentWeights.reduce(
    (maxIndex, weight, index) => (weight > currentWeights[maxIndex] ? index : maxIndex),
    0,
  );
  const riskAssetIndex = assets.reduce(
    (maxIndex, asset, index) => (asset.volatility > assets[maxIndex].volatility ? index : maxIndex),
    0,
  );
  const optimizedLargestIndex = optimized.weights.reduce(
    (maxIndex, weight, index) => (weight > optimized.weights[maxIndex] ? index : maxIndex),
    0,
  );

  return [
    `Die groesste Einzelposition ist ${assets[dominantAssetIndex].ticker} mit ${formatPercent(
      currentWeights[dominantAssetIndex],
    )}; dadurch ist das Portfolio spuerbar von dieser Position abhaengig.`,
    `${assets[riskAssetIndex].ticker} traegt wegen der hohen historischen Volatilitaet besonders stark zum Gesamtrisiko bei.`,
    `Die simulierte Max-Sharpe-Variante wuerde ${assets[optimizedLargestIndex].ticker} hoeher gewichten und die erwartete Sharpe Ratio auf ${optimized.sharpe.toFixed(
      2,
    )} verbessern.`,
    `Der historische 1-Tages-Value-at-Risk liegt bei etwa ${formatPercent(
      current.valueAtRisk,
    )}; dieser Wert ist ein Risikomass, keine Prognosegarantie.`,
  ];
}

export function formatPercent(value: number) {
  return new Intl.NumberFormat("de-DE", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

function calculateDiversificationScore(weights: number[]) {
  const herfindahl = weights.reduce((sum, weight) => sum + weight * weight, 0);
  return Math.max(0, Math.min(100, (1 - herfindahl) * 140));
}
