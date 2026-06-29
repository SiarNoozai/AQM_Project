export type AssetInput = {
  ticker: string;
  name: string;
  weight: number;
  expectedReturn: number;
  volatility: number;
  color: string;
};

export const initialAssets: AssetInput[] = [
  {
    ticker: "AAPL",
    name: "Apple",
    weight: 35,
    expectedReturn: 0.148,
    volatility: 0.255,
    color: "#0f766e",
  },
  {
    ticker: "MSFT",
    name: "Microsoft",
    weight: 30,
    expectedReturn: 0.132,
    volatility: 0.218,
    color: "#2563eb",
  },
  {
    ticker: "SPY",
    name: "S&P 500 ETF",
    weight: 25,
    expectedReturn: 0.091,
    volatility: 0.152,
    color: "#d97706",
  },
  {
    ticker: "AGG",
    name: "US Aggregate Bond ETF",
    weight: 10,
    expectedReturn: 0.037,
    volatility: 0.062,
    color: "#7c3aed",
  },
];

export const baseCorrelationMatrix = [
  [1, 0.72, 0.81, -0.18],
  [0.72, 1, 0.78, -0.12],
  [0.81, 0.78, 1, -0.09],
  [-0.18, -0.12, -0.09, 1],
];
