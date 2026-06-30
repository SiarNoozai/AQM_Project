import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Database,
  Download,
  FileText,
  LineChart as LineChartIcon,
  Menu,
  MoreVertical,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AssetInput, baseCorrelationMatrix, initialAssets } from "./data/assets";
import {
  ApiAnalysis,
  ApiFrontierPoint,
  ApiRiskFinding,
  RecommendationResult,
  analyzePortfolio,
  downloadExport,
  recommendPortfolio,
} from "./lib/api";
import {
  FrontierPoint,
  buildEfficientFrontier,
  buildPerformanceSeries,
  buildRecommendations,
  calculatePortfolioMetrics,
  formatPercent,
  getOptimizedPoint,
  normalizeWeights,
} from "./lib/portfolioMath";

type MetricCardProps = {
  label: string;
  value: string;
  helper: string;
  icon: ReactNode;
  tone?: "positive" | "warning" | "neutral";
};

type DisplayAsset = {
  ticker: string;
  name: string;
  weight: number;
  expectedReturn: number;
  volatility: number;
  color: string;
};

type Frequency = "1d" | "1wk" | "1mo";

const percentFormatter = new Intl.NumberFormat("de-DE", {
  style: "percent",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const defaultStartDate = toInputDate(addYears(new Date(), -5));
const defaultEndDate = toInputDate(new Date());

function App() {
  const [assets, setAssets] = useState<AssetInput[]>(initialAssets);
  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultEndDate);
  const [frequency, setFrequency] = useState<Frequency>("1d");
  const [riskFreeRate] = useState(2.5);
  const [varConfidence] = useState(95);
  const [analysis, setAnalysis] = useState<ApiAnalysis | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState<"csv" | "pdf" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const demoWeights = useMemo(() => normalizeWeights(assets), [assets]);
  const demoFrontier = useMemo(() => buildEfficientFrontier(assets, demoWeights), [assets, demoWeights]);
  const demoOptimizedPoint = useMemo(() => getOptimizedPoint(demoFrontier), [demoFrontier]);
  const demoMetrics = useMemo(() => calculatePortfolioMetrics(assets, demoWeights), [assets, demoWeights]);
  const demoOptimizedMetrics = useMemo(
    () => calculatePortfolioMetrics(assets, demoOptimizedPoint.weights),
    [assets, demoOptimizedPoint.weights],
  );
  const demoPerformance = useMemo(
    () => buildPerformanceSeries(assets, demoWeights, demoOptimizedPoint.weights),
    [assets, demoOptimizedPoint.weights, demoWeights],
  );
  const demoRecommendations = useMemo(
    () => buildRecommendations(assets, demoWeights, demoMetrics, demoOptimizedPoint),
    [assets, demoMetrics, demoOptimizedPoint, demoWeights],
  );
  const demoRiskFindings = useMemo(
    () => buildDemoRiskFindings(assets, demoWeights, demoMetrics),
    [assets, demoMetrics, demoWeights],
  );

  const displayAssets: DisplayAsset[] = useMemo(() => {
    if (!analysis) {
      return assets;
    }

    return analysis.assets.map((asset, index) => {
      const existing = assets.find((item) => item.ticker === asset.ticker);
      return {
        ticker: asset.ticker,
        name: existing?.name ?? asset.ticker,
        weight: asset.weight,
        expectedReturn: asset.expectedReturn,
        volatility: asset.volatility,
        color: existing?.color ?? initialAssets[index % initialAssets.length].color,
      };
    });
  }, [analysis, assets]);

  const activeWeights = analysis ? analysis.assets.map((asset) => asset.weight) : demoWeights;
  const activeMetrics = analysis?.metrics ?? demoMetrics;
  const activeOptimizedMetrics = analysis?.optimizedMetrics ?? demoOptimizedMetrics;
  const activeOptimizedWeights = analysis?.optimizedWeights ?? demoOptimizedPoint.weights;
  const activePerformance = analysis?.performance ?? demoPerformance;
  const activeFrontier = analysis?.frontier ?? demoFrontier;
  const activeRecommendations = recommendation?.recommendations ?? analysis?.recommendations ?? demoRecommendations;
  const activeRiskFindings = analysis?.riskFindings ?? demoRiskFindings;
  const visibleRiskFindings = getVisibleRiskFindings(activeRiskFindings);
  const recommendationSource = recommendation?.source ?? analysis?.recommendationSource ?? "rules";
  const isLive = Boolean(analysis);
  const weightSum = assets.reduce((sum, asset) => sum + Number(asset.weight || 0), 0);

  function updateAsset(index: number, key: keyof AssetInput, value: string | number) {
    setAnalysis(null);
    setRecommendation(null);
    setAssets((currentAssets) =>
      currentAssets.map((asset, assetIndex) =>
        assetIndex === index
          ? {
              ...asset,
              [key]: value,
            }
          : asset,
      ),
    );
  }

  function resetPortfolio() {
    setAssets(initialAssets);
    setAnalysis(null);
    setRecommendation(null);
    setError(null);
  }

  async function handleAnalyze() {
    setIsLoading(true);
    setError(null);
    setRecommendation(null);

    try {
      const nextAnalysis = await analyzePortfolio({
        tickers: assets.map((asset) => asset.ticker),
        weights: assets.map((asset) => asset.weight),
        startDate,
        endDate,
        frequency,
        riskFreeRate: riskFreeRate / 100,
        varConfidence: varConfidence / 100,
      });
      setAnalysis(nextAnalysis);
      setIsLoading(false);

      try {
        const nextRecommendation = await recommendPortfolio(nextAnalysis);
        setRecommendation(nextRecommendation);
      } catch {
        setRecommendation(null);
      }
    } catch (caughtError) {
      setAnalysis(null);
      setRecommendation(null);
      setError(caughtError instanceof Error ? caughtError.message : "Analyse konnte nicht geladen werden.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleExport(kind: "csv" | "pdf") {
    if (!analysis) {
      setError("Export ist erst nach einer Live-Analyse verfuegbar.");
      return;
    }

    setIsExporting(kind);
    setError(null);
    try {
      await downloadExport(kind, analysis, activeRecommendations);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Export konnte nicht erstellt werden.");
    } finally {
      setIsExporting(null);
    }
  }

  return (
    <div className="dashboard-screen">
      <header className="app-header">
        <div className="header-brand">
          <button className="icon-button" type="button" aria-label="Navigation oeffnen">
            <Menu size={20} />
          </button>
          <div>
            <h1>Portfolio- und Risikoanalyse</h1>
            <span>{isLive ? "Live-Daten aus Yahoo Finance" : "Demo-Fallback aktiv"}</span>
          </div>
        </div>

        <div className="header-controls" aria-label="Analyse Steuerung">
          <label className="toolbar-field date-toolbar">
            <span>Zeitraum</span>
            <div className="date-range">
              <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
              <span aria-hidden="true">-</span>
              <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            </div>
          </label>

          <label className="toolbar-field">
            <span>Frequenz</span>
            <select value={frequency} onChange={(event) => setFrequency(event.target.value as Frequency)}>
              <option value="1d">Taeglich</option>
              <option value="1wk">Woechentlich</option>
              <option value="1mo">Monatlich</option>
            </select>
          </label>

          <button className="toolbar-button primary" type="button" onClick={handleAnalyze} disabled={isLoading}>
            {isLoading ? <RefreshCw className="spinning" size={16} /> : <Database size={16} />}
            {isLoading ? "Aktualisiere" : "Daten aktualisieren"}
          </button>

          <button
            className="toolbar-button icon-text"
            type="button"
            onClick={() => handleExport("csv")}
            disabled={!analysis || isExporting !== null}
          >
            <Download size={15} />
            {isExporting === "csv" ? "CSV..." : "CSV"}
          </button>

          <button
            className="toolbar-button icon-text"
            type="button"
            onClick={() => handleExport("pdf")}
            disabled={!analysis || isExporting !== null}
          >
            <FileText size={15} />
            {isExporting === "pdf" ? "PDF..." : "PDF"}
          </button>

          <button className="icon-button" type="button" aria-label="Mehr Optionen">
            <MoreVertical size={19} />
          </button>
        </div>
      </header>

      <div className="dashboard-layout">
        <aside className="portfolio-sidebar" aria-label="Portfolio Eingaben">
          <div className="sidebar-title">
            <h2>Portfolio-Eingaben</h2>
            <button className="sidebar-reset" type="button" onClick={resetPortfolio}>
              Reset
            </button>
          </div>

          <label className="sidebar-field">
            <span>Anzahl Assets</span>
            <select value={assets.length} disabled>
              <option value={assets.length}>{assets.length}</option>
            </select>
          </label>

          <section className="sidebar-section">
            <h3>Assets</h3>
            <div className="asset-compact-list">
              {assets.map((asset, index) => (
                <article className="asset-row-card" key={`${asset.ticker}-${index}`}>
                  <span className="asset-dot" style={{ backgroundColor: asset.color }} />
                  <div className="asset-copy">
                    <input
                      aria-label={`Ticker ${index + 1}`}
                      value={asset.ticker}
                      onChange={(event) => updateAsset(index, "ticker", event.target.value.toUpperCase())}
                    />
                    <span>{asset.name}</span>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="sidebar-section weights-section">
            <h3>Gewichtung (%)</h3>
            <div className="weight-list">
              {assets.map((asset, index) => (
                <label className="weight-row" key={`${asset.ticker}-weight`}>
                  <span className="asset-dot" style={{ backgroundColor: asset.color }} />
                  <strong>{asset.ticker}</strong>
                  <input
                    aria-label={`Gewichtung ${asset.ticker}`}
                    min="0"
                    max="100"
                    step="1"
                    type="number"
                    value={asset.weight}
                    onChange={(event) => updateAsset(index, "weight", Number(event.target.value))}
                  />
                  <span>%</span>
                </label>
              ))}
            </div>
            <div className={`weight-sum ${Math.abs(weightSum - 100) <= 0.5 ? "valid" : "invalid"}`}>
              <span>Summe</span>
              <strong>{weightSum.toFixed(0)} %</strong>
            </div>
          </section>

          <button className="sidebar-primary" type="button" onClick={handleAnalyze} disabled={isLoading}>
            <RefreshCw size={15} />
            Portfolio aktualisieren
          </button>

          <div className="currency-row">
            <span>Waehrung</span>
            <select value="USD" disabled>
              <option>USD</option>
            </select>
          </div>
        </aside>

        <main className="analysis-board">
          {error ? <div className="notice error">{error}</div> : null}

          <section className="kpi-row" aria-label="Portfolio Kennzahlen">
            <MetricCard
              icon={<TrendingUp size={18} />}
              label="Rendite (p.a.)"
              value={formatPercent(activeMetrics.expectedReturn)}
              helper={`Optimiert: ${formatPercent(activeOptimizedMetrics.expectedReturn)}`}
              tone="positive"
            />
            <MetricCard
              icon={<Activity size={18} />}
              label="Volatilitaet (p.a.)"
              value={formatPercent(activeMetrics.volatility)}
              helper={`Optimiert: ${formatPercent(activeOptimizedMetrics.volatility)}`}
            />
            <MetricCard
              icon={<LineChartIcon size={18} />}
              label="Sharpe Ratio"
              value={activeMetrics.sharpeRatio.toFixed(2)}
              helper={`Max-Sharpe: ${activeOptimizedMetrics.sharpeRatio.toFixed(2)}`}
              tone="positive"
            />
            <MetricCard
              icon={<AlertTriangle size={18} />}
              label={`Value at Risk (${varConfidence}%)`}
              value={`-${formatPercent(activeMetrics.valueAtRisk)}`}
              helper="Historisch, 1 Tag"
              tone="warning"
            />
          </section>

          <article className="panel performance-panel">
            <PanelHeader
              title="Normalisierte Wertentwicklung"
              description={analysis ? formatShortDateRange(analysis.startDate, analysis.endDate) : "Demo-Zeitraum"}
            />
            <div className="legend-row">
              <span className="legend-chip portfolio-line">Portfolio</span>
              {displayAssets.map((asset) => (
                <span className="legend-chip" key={asset.ticker}>
                  <span className="legend-dot" style={{ backgroundColor: asset.color }} />
                  {asset.ticker}
                </span>
              ))}
            </div>
            <div className="chart-frame performance-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={activePerformance} margin={{ top: 10, right: 18, left: 2, bottom: 0 }}>
                  <CartesianGrid stroke="#e5eaf0" strokeDasharray="4 4" />
                  <XAxis dataKey="month" tickLine={false} axisLine={false} minTickGap={22} />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    domain={["dataMin - 3", "dataMax + 4"]}
                    tickFormatter={(value) => Number(value).toFixed(0)}
                    width={42}
                  />
                  <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#d8dee8" }} />
                  <Line
                    dataKey="portfolio"
                    name="Portfolio"
                    stroke="#08345f"
                    dot={false}
                    isAnimationActive={false}
                    strokeWidth={3}
                    type="monotone"
                  />
                  {displayAssets.map((asset) => (
                    <Line
                      dataKey={asset.ticker}
                      key={asset.ticker}
                      name={asset.ticker}
                      stroke={asset.color}
                      dot={false}
                      isAnimationActive={false}
                      strokeWidth={2}
                      type="monotone"
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>

          <section className="bottom-grid">
            <article className="panel heatmap-panel">
              <PanelHeader title="Korrelationsmatrix" description="Diversifikation der Anlagen" />
              <CorrelationHeatmap
                assets={displayAssets}
                values={analysis?.correlationMatrix.values ?? baseCorrelationMatrix}
              />
              <div className="correlation-scale" aria-hidden="true">
                <span>-1,0</span>
                <div />
                <span>1,0</span>
              </div>
            </article>

            <article className="panel frontier-panel">
              <PanelHeader title="Effiziente Grenze" description="Mittelwert-Varianz Simulation" />
              <div className="frontier-layout">
                <div className="chart-frame small">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 10, right: 12, left: 0, bottom: 4 }}>
                      <CartesianGrid stroke="#e5eaf0" strokeDasharray="4 4" />
                      <XAxis
                        dataKey="risk"
                        name="Volatilitaet"
                        type="number"
                        domain={["dataMin - 0.01", "dataMax + 0.01"]}
                        tickFormatter={(value) => `${Math.round(value * 100)}%`}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        dataKey="return"
                        name="Rendite"
                        type="number"
                        domain={["dataMin - 0.01", "dataMax + 0.01"]}
                        tickFormatter={(value) => `${Math.round(value * 100)}%`}
                        tickLine={false}
                        axisLine={false}
                        width={34}
                      />
                      <Tooltip
                        cursor={{ strokeDasharray: "3 3" }}
                        content={({ active, payload }) => {
                          if (!active || !payload?.length) return null;
                          const point = payload[0].payload as ApiFrontierPoint | FrontierPoint;
                          return (
                            <div className="tooltip-box">
                              <strong>
                                {point.kind === "current"
                                  ? "Aktuelles Portfolio"
                                  : point.kind === "optimized"
                                    ? "Optimiert"
                                    : "Simulation"}
                              </strong>
                              <span>Rendite: {formatPercent(point.return)}</span>
                              <span>Risiko: {formatPercent(point.risk)}</span>
                              <span>Sharpe: {point.sharpe.toFixed(2)}</span>
                            </div>
                          );
                        }}
                      />
                      <Scatter
                        data={activeFrontier.filter((point) => point.kind === "simulation")}
                        fill="#9aa8b6"
                        isAnimationActive={false}
                        opacity={0.58}
                      />
                      <ReferenceDot
                        x={activeMetrics.volatility}
                        y={activeMetrics.expectedReturn}
                        r={6}
                        fill="#08345f"
                        stroke="#ffffff"
                        strokeWidth={2}
                      />
                      <ReferenceDot
                        x={activeOptimizedMetrics.volatility}
                        y={activeOptimizedMetrics.expectedReturn}
                        r={6}
                        fill="#079475"
                        stroke="#ffffff"
                        strokeWidth={2}
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
                <div className="frontier-legend">
                  <span>
                    <i className="current-marker" />
                    Aktuell
                  </span>
                  <span>
                    <i className="optimized-marker" />
                    Optimiert
                  </span>
                </div>
              </div>
            </article>
          </section>
        </main>

        <aside className="ai-rail panel" aria-label="KI Empfehlung">
          <div className="ai-rail-header">
            <div className="ai-mark">
              <BrainCircuit size={22} />
            </div>
            <div>
              <h2>KI-Empfehlung</h2>
              <p>Aus Kennzahlen abgeleitet, keine freie Investment-Auswahl.</p>
            </div>
          </div>

          <section className="ai-summary">
            <h3>Kurzfazit</h3>
            <ul>
              <li>
                Rendite {formatPercent(activeMetrics.expectedReturn)} bei Volatilitaet{" "}
                {formatPercent(activeMetrics.volatility)}.
              </li>
              <li>Sharpe Ratio {activeMetrics.sharpeRatio.toFixed(2)} fuer risikobereinigte Performance.</li>
              <li>Historischer VaR liegt bei -{formatPercent(activeMetrics.valueAtRisk)}.</li>
            </ul>
          </section>

          <section className="ai-recommendations">
            <h3>Empfehlungen</h3>
            {activeRecommendations.slice(0, 3).map((item, index) => (
              <article className="recommendation-card" key={`${item}-${index}`}>
                <span className={`recommendation-icon tone-${index + 1}`}>
                  {index === 0 ? <TrendingUp size={18} /> : index === 1 ? <ShieldCheck size={18} /> : <Activity size={18} />}
                </span>
                <div>
                  <strong>{getRecommendationTitle(index)}</strong>
                  <p>{item}</p>
                </div>
              </article>
            ))}
          </section>

          <section className="risk-findings">
            <h3>Auffaelligkeiten</h3>
            {visibleRiskFindings.map((finding, index) => (
              <article className={`risk-finding severity-${finding.severity}`} key={`${finding.type}-${index}`}>
                <strong>{getRiskFindingTitle(finding)}</strong>
                <p>{finding.message}</p>
              </article>
            ))}
          </section>

          <footer className="ai-footer">
            <h3>Hinweis</h3>
            <p>
              Historische Daten sind kein verlaesslicher Indikator fuer zukuenftige Ergebnisse. Diese Analyse ist keine
              Anlageberatung.
            </p>
            <span>
              Quelle: {analysis?.dataSource ?? "Demo-Daten"} | Modell:{" "}
              {recommendationSource === "ollama" ? `Ollama ${recommendation?.model ?? ""}` : "Regel-Fallback"}
            </span>
            <span>Letzte Aktualisierung: {analysis ? formatDateTime(analysis.updatedAt) : "noch keine Live-Analyse"}</span>
          </footer>
        </aside>
      </div>
    </div>
  );
}

function MetricCard({ label, value, helper, icon, tone = "neutral" }: MetricCardProps) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-label-row">
        <span>{label}</span>
        <div className="metric-icon">{icon}</div>
      </div>
      <strong>{value}</strong>
      <p>{helper}</p>
    </article>
  );
}

function PanelHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="panel-header">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}

function CorrelationHeatmap({ assets, values }: { assets: DisplayAsset[]; values: number[][] }) {
  return (
    <div className="heatmap" role="table" aria-label="Korrelationsmatrix">
      <div className="heatmap-row header-row" style={{ gridTemplateColumns: `50px repeat(${assets.length}, minmax(44px, 1fr))` }}>
        <span />
        {assets.map((asset) => (
          <strong key={asset.ticker}>{asset.ticker}</strong>
        ))}
      </div>
      {assets.map((asset, rowIndex) => (
        <div
          className="heatmap-row"
          key={asset.ticker}
          style={{ gridTemplateColumns: `50px repeat(${assets.length}, minmax(44px, 1fr))` }}
        >
          <strong>{asset.ticker}</strong>
          {assets.map((columnAsset, columnIndex) => {
            const value = values[rowIndex]?.[columnIndex] ?? 0;
            return (
              <span
                className="heatmap-cell"
                key={`${asset.ticker}-${columnAsset.ticker}`}
                style={{ backgroundColor: getCorrelationColor(value) }}
              >
                {value.toFixed(2)}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function getCorrelationColor(value: number) {
  if (value < 0) {
    return `rgba(213, 55, 80, ${0.14 + Math.abs(value) * 0.5})`;
  }

  return `rgba(10, 95, 168, ${0.12 + value * 0.62})`;
}

function getRecommendationTitle(index: number) {
  if (index === 0) {
    return "Rendite-Risiko-Profil verbessern";
  }
  if (index === 1) {
    return "Diversifikation pruefen";
  }
  return "Risikomanagement beibehalten";
}

function buildDemoRiskFindings(
  assets: AssetInput[],
  weights: number[],
  metrics: { volatility: number; sharpeRatio: number; diversificationScore: number },
): ApiRiskFinding[] {
  const dominantIndex = weights.reduce((maxIndex, weight, index) => (weight > weights[maxIndex] ? index : maxIndex), 0);
  const findings: ApiRiskFinding[] = [];
  if ((weights[dominantIndex] ?? 0) >= 0.35) {
    findings.push({
      type: "concentration",
      severity: "medium",
      affectedAssets: [assets[dominantIndex].ticker],
      message: `${assets[dominantIndex].ticker} ist mit ${percentFormatter.format(
        weights[dominantIndex],
      )} die groesste Einzelposition. Das kann ein Klumpenrisiko erzeugen.`,
    });
  }
  if (metrics.diversificationScore < 65) {
    findings.push({
      type: "diversification",
      severity: "medium",
      affectedAssets: [],
      message: `Der Diversifikationswert liegt bei ${metrics.diversificationScore.toFixed(
        0,
      )} von 100. Eine breitere Streuung sollte geprueft werden.`,
    });
  }
  if (metrics.volatility >= 0.2) {
    findings.push({
      type: "volatility",
      severity: "medium",
      affectedAssets: [],
      message: `Die historische Volatilitaet von ${formatPercent(metrics.volatility)} weist auf spuerbare Schwankungen hin.`,
    });
  }
  findings.push({
    type: "behavioral",
    severity: "low",
    affectedAssets: [],
    message:
      "Behavioral-Finance-Hinweis: Historische Renditen und bekannte Namen sollten nicht als sichere Zukunftserwartung verstanden werden.",
  });
  return findings;
}

function getRiskFindingTitle(finding: ApiRiskFinding) {
  const titles: Record<ApiRiskFinding["type"], string> = {
    concentration: "Konzentration",
    correlation: "Hohe Korrelation",
    diversification: "Diversifikation",
    volatility: "Volatilitaet",
    risk_return: "Rendite-Risiko",
    allocation: "Asset Allocation",
    behavioral: "Behavioral Finance",
  };
  return titles[finding.type];
}

function getVisibleRiskFindings(findings: ApiRiskFinding[]) {
  const behavioral = findings.find((finding) => finding.type === "behavioral");
  const primary = findings.find((finding) => finding.type !== "behavioral");
  return [primary, behavioral].filter((finding): finding is ApiRiskFinding => Boolean(finding)).slice(0, 2);
}

function addYears(date: Date, years: number) {
  const next = new Date(date);
  next.setFullYear(next.getFullYear() + years);
  return next;
}

function toInputDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatShortDateRange(start: string, end: string) {
  return `${formatInputDate(start)} - ${formatInputDate(end)}`;
}

function formatInputDate(value: string) {
  return new Intl.DateTimeFormat("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

export default App;
