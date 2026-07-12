export type AssetInput = {
  id: string;
  ticker: string;
  name: string;
  weight: number;
  expectedReturn: number;
  volatility: number;
  color: string;
};

type AssetSeed = Omit<AssetInput, "id" | "weight"> & {
  defaultWeight: number;
};

const assetPalette = [
  "#0f766e",
  "#2563eb",
  "#d97706",
  "#0f4c81",
  "#7c3aed",
  "#15803d",
  "#dc2626",
  "#0891b2",
  "#92400e",
  "#475569",
];

export const DEFAULT_EXPECTED_RETURN = 0.082;
export const DEFAULT_VOLATILITY = 0.18;

const suggestedAssetCatalog: AssetSeed[] = [
  {
    ticker: "AAPL",
    name: "Apple",
    defaultWeight: 35,
    expectedReturn: 0.148,
    volatility: 0.255,
    color: assetPalette[0],
  },
  {
    ticker: "MSFT",
    name: "Microsoft",
    defaultWeight: 30,
    expectedReturn: 0.132,
    volatility: 0.218,
    color: assetPalette[1],
  },
  {
    ticker: "SPY",
    name: "S&P 500 ETF",
    defaultWeight: 25,
    expectedReturn: 0.091,
    volatility: 0.152,
    color: assetPalette[2],
  },
  {
    ticker: "AGG",
    name: "US Aggregate Bond ETF",
    defaultWeight: 10,
    expectedReturn: 0.037,
    volatility: 0.062,
    color: assetPalette[3],
  },
  {
    ticker: "QQQ",
    name: "Nasdaq 100 ETF",
    defaultWeight: 0,
    expectedReturn: 0.118,
    volatility: 0.209,
    color: assetPalette[4],
  },
  {
    ticker: "VTI",
    name: "Total Stock Market ETF",
    defaultWeight: 0,
    expectedReturn: 0.086,
    volatility: 0.148,
    color: assetPalette[5],
  },
  {
    ticker: "BND",
    name: "Total Bond Market ETF",
    defaultWeight: 0,
    expectedReturn: 0.034,
    volatility: 0.058,
    color: assetPalette[6],
  },
  {
    ticker: "VNQ",
    name: "Real Estate ETF",
    defaultWeight: 0,
    expectedReturn: 0.071,
    volatility: 0.173,
    color: assetPalette[7],
  },
  {
    ticker: "IEFA",
    name: "Developed Markets ETF",
    defaultWeight: 0,
    expectedReturn: 0.074,
    volatility: 0.141,
    color: assetPalette[8],
  },
  {
    ticker: "TLT",
    name: "Long-Term Treasury ETF",
    defaultWeight: 0,
    expectedReturn: 0.041,
    volatility: 0.108,
    color: assetPalette[9],
  },
];

export const baseCorrelationMatrix = [
  [1, 0.72, 0.81, -0.18],
  [0.72, 1, 0.78, -0.12],
  [0.81, 0.78, 1, -0.09],
  [-0.18, -0.12, -0.09, 1],
];

export const initialAssets: AssetInput[] = suggestedAssetCatalog
  .slice(0, 4)
  .map((seed, index) => createAssetInput({ ...seed, weight: seed.defaultWeight }, index));

export function createAssetInput(seed: Partial<Omit<AssetInput, "id">> = {}, index = 0): AssetInput {
  const color = seed.color ?? assetPalette[index % assetPalette.length];
  return {
    id: crypto.randomUUID(),
    ticker: seed.ticker?.toUpperCase() ?? "",
    name: seed.name ?? "Neue Position",
    weight: seed.weight ?? 0,
    expectedReturn: seed.expectedReturn ?? DEFAULT_EXPECTED_RETURN,
    volatility: seed.volatility ?? DEFAULT_VOLATILITY,
    color,
  };
}

export function syncAssetMetadata(asset: AssetInput, index: number, options: { preserveName?: boolean } = {}): AssetInput {
  const normalizedTicker = asset.ticker.trim().toUpperCase();
  const seed = suggestedAssetCatalog.find((item) => item.ticker === normalizedTicker);
  const preservedName = asset.name.trim();
  return {
    ...asset,
    ticker: normalizedTicker,
    name: seed?.name ?? (options.preserveName && preservedName ? preservedName : normalizedTicker || "Neue Position"),
    expectedReturn: seed?.expectedReturn ?? asset.expectedReturn,
    volatility: seed?.volatility ?? asset.volatility,
    color: asset.color || assetPalette[index % assetPalette.length],
  };
}

export function getNextSuggestedAsset(existing: AssetInput[]): AssetInput {
  return createAssetInput(
    {
      ticker: "",
      name: "Neue Position",
      weight: 0,
    },
    existing.length,
  );
}

export function buildFallbackCorrelationMatrix(assets: AssetInput[]): number[][] {
  return assets.map((_, rowIndex) =>
    assets.map((__, columnIndex) => {
      if (rowIndex === columnIndex) {
        return 1;
      }
      const presetValue = baseCorrelationMatrix[rowIndex]?.[columnIndex];
      if (presetValue !== undefined) {
        return presetValue;
      }
      const generated = 0.18 + Math.abs(Math.sin((rowIndex + 1) * (columnIndex + 2) * 0.73)) * 0.58;
      return Number(generated.toFixed(2));
    }),
  );
}
