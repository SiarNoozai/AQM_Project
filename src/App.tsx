import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Check,
  ChevronDown,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  MessageCircleQuestion,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  TrendingUp,
  Trash2,
  X,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  DEFAULT_EXPECTED_RETURN,
  DEFAULT_VOLATILITY,
  type AssetInput,
  buildFallbackCorrelationMatrix,
  createAssetInput,
  initialAssets,
  syncAssetMetadata,
} from "./data/assets";
import {
  type ApiAnalysis,
  type ApiRiskFinding,
  type ApiSectorAllocation,
  type FocusArea,
  type GoalPreset,
  type InvestorProfile,
  type RecommendationResult,
  type RiskStyle,
  type SecuritySearchResult,
  type TimeHorizon,
  analyzePortfolio,
  exportPortfolioReport,
  recommendPortfolio,
  searchSecurities,
} from "./lib/api";
import {
  type SavedPortfolio,
  deletePortfolioRecord,
  loadSavedPortfolios,
  savePortfolioRecord,
} from "./lib/portfolioStorage";
import {
  buildEfficientFrontier,
  buildPerformanceSeries,
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
  id: string;
  ticker: string;
  name: string;
  color: string;
  expectedReturn: number;
  volatility: number;
  sector: string;
  instrumentType: "EQUITY" | "ETF";
};

type RankedChartAsset = DisplayAsset & {
  sortWeight: number;
};

type PeriodPreset = 1 | 3 | 5;
type WorkspaceView = "analysis" | "ai";
type AiStep = 1 | 2 | 3 | 4;

const periodOptions: Array<{ label: string; value: PeriodPreset }> = [
  { label: "1 Jahr", value: 1 },
  { label: "3 Jahre", value: 3 },
  { label: "5 Jahre", value: 5 },
];

const focusAreaOptions: Array<{ id: FocusArea; label: string; description: string }> = [
  {
    id: "summary",
    label: "Gesamtueberblick",
    description: "Fasst die wichtigsten Kennzahlen und das Gesamtbild kompakt zusammen.",
  },
  {
    id: "sector",
    label: "Branchengewichtung",
    description: "Zeigt, ob dein Portfolio stark in einzelnen Branchen gebuendelt ist.",
  },
  {
    id: "concentration",
    label: "Konzentrationsrisiken",
    description: "Prueft, ob einzelne Positionen oder Schwerpunkte zu dominant sind.",
  },
  {
    id: "diversification",
    label: "Diversifikation & Korrelation",
    description: "Betrachtet Branchenbreite und historisch aehnliche Bewegungen im Portfolio.",
  },
  {
    id: "risk_drivers",
    label: "Risikotreiber",
    description: "Hebt Schwankungs- und Rendite-Risiko-Aspekte besonders hervor.",
  },
];

const timeHorizonOptions: Array<{ id: TimeHorizon; label: string; description: string }> = [
  {
    id: "short_term",
    label: "Kurzfristig",
    description: "Die KI priorisiert naheliegende Schwankungs- und Nachrichtenrisiken, ohne Trading-Signale zu geben.",
  },
  {
    id: "mid_term",
    label: "Mittelfristig",
    description: "Die KI sucht eine tragfaehige Balance zwischen Stabilitaet und Chancen.",
  },
  {
    id: "long_term",
    label: "Langfristig",
    description: "Die KI achtet staerker auf robuste Branchenbreite und nachhaltige Portfolio-Struktur.",
  },
];

const riskStyleOptions: Array<{ id: RiskStyle; label: string; description: string }> = [
  {
    id: "defensive",
    label: "Defensiv",
    description: "Mehr Fokus auf Schwankungsreduktion, Streuung und geringere Einzelrisiken.",
  },
  {
    id: "balanced",
    label: "Ausgewogen",
    description: "Balance aus Renditechancen, Diversifikation und nachvollziehbarer Gewichtung.",
  },
  {
    id: "aggressive",
    label: "Aggressiv",
    description: "Mehr Toleranz fuer Wachstumsschwerpunkte, aber weiter mit Blick auf Konzentrationsrisiken.",
  },
];

const goalPresetOptions: Array<{ id: GoalPreset; label: string; description: string }> = [
  {
    id: "diversify_broadly",
    label: "Breit diversifizieren",
    description: "Die KI soll vor allem Branchenbreite, robustere Verteilung und geringere Klumpenrisiken suchen.",
  },
  {
    id: "keep_tech_focus",
    label: "Tech-Fokus beibehalten",
    description: "Die KI darf Wachstumsschwerpunkte in Tech akzeptieren, soll aber die Struktur gezielter absichern.",
  },
  {
    id: "defensive",
    label: "Defensiver aufstellen",
    description: "Die KI priorisiert niedrigere Schwankung, stabilere Sektoren und geringere Einzelrisiken.",
  },
  {
    id: "balanced",
    label: "Rendite-Risiko ausbalancieren",
    description: "Die KI sucht eine nachvollziehbare Mittelposition zwischen Chancen und Risiko.",
  },
];

const defaultFocusAreas = focusAreaOptions.map((option) => option.id);

const percentFormatter = new Intl.NumberFormat("de-DE", {
  style: "percent",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const MIN_SEARCH_QUERY_LENGTH = 2;

const quickFollowUpQuestions = [
  "Welche Position traegt aktuell das groesste Risiko?",
  "Was wuerde die Diversifikation am staerksten verbessern?",
  "Welche vorgeschlagene Anpassung sollte ich zuerst pruefen?",
];

type AddPositionOption = {
  id: string;
  label: string;
  description: string;
  ticker: string;
  accent: string;
};

const addPositionOptions: AddPositionOption[] = [
  {
    id: "equity",
    label: "Aktie",
    description: "Einzelposition mit klarer Referenz, zum Beispiel Apple.",
    ticker: "AAPL",
    accent: "#0f766e",
  },
  {
    id: "etf",
    label: "ETF",
    description: "Breite Marktposition, passend als Kernbaustein.",
    ticker: "SPY",
    accent: "#2563eb",
  },
  {
    id: "bond",
    label: "Anleihe",
    description: "Stabilere Beimischung fuer mehr Ruhe im Portfolio.",
    ticker: "AGG",
    accent: "#0f4c81",
  },
  {
    id: "custom",
    label: "Leere Position",
    description: "Freien Ticker selbst waehlen oder anschliessend suchen.",
    ticker: "",
    accent: "#64748b",
  },
];

function App() {
  const [assets, setAssets] = useState<AssetInput[]>(initialAssets);
  const [periodYears, setPeriodYears] = useState<PeriodPreset>(5);
  const [analysis, setAnalysis] = useState<ApiAnalysis | null>(null);
  const [recommendation, setRecommendation] = useState<RecommendationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingRecommendation, setIsGeneratingRecommendation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>("analysis");
  const [activeAiStep, setActiveAiStep] = useState<AiStep>(1);
  const [selectedFocusAreas, setSelectedFocusAreas] = useState<FocusArea[]>(defaultFocusAreas);
  const [selectedTimeHorizon, setSelectedTimeHorizon] = useState<TimeHorizon | null>(null);
  const [selectedRiskStyle, setSelectedRiskStyle] = useState<RiskStyle | null>(null);
  const [selectedGoalPreset, setSelectedGoalPreset] = useState<GoalPreset>("diversify_broadly");
  const [goalNote, setGoalNote] = useState("");
  const [searchRowIndex, setSearchRowIndex] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SecuritySearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [savedPortfolios, setSavedPortfolios] = useState<SavedPortfolio[]>(() => loadSavedPortfolios());
  const [portfolioName, setPortfolioName] = useState("");
  const [activeSavedPortfolioId, setActiveSavedPortfolioId] = useState("");
  const [saveFeedback, setSaveFeedback] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState<"csv" | "pdf" | null>(null);
  const [exportFeedback, setExportFeedback] = useState<string | null>(null);
  const [lastFollowUp, setLastFollowUp] = useState<string | null>(null);
  const [isAddMenuOpen, setIsAddMenuOpen] = useState(false);
  const addMenuRef = useRef<HTMLDivElement | null>(null);

  const { startDate, endDate } = useMemo(() => buildPeriodRange(periodYears), [periodYears]);
  const debouncedSearchQuery = useDebouncedValue(searchQuery, 300);
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
  const demoRiskFindings = useMemo(
    () => buildDemoRiskFindings(assets, demoWeights, demoMetrics, buildFallbackCorrelationMatrix(assets)),
    [assets, demoMetrics, demoWeights],
  );

  const displayAssets: DisplayAsset[] = useMemo(() => {
    if (!analysis) {
      return assets.map((asset, index) => ({
        id: asset.id,
        ticker: asset.ticker,
        name: asset.name,
        color: asset.color,
        expectedReturn: asset.expectedReturn,
        volatility: asset.volatility,
        sector: inferFallbackSector(asset.ticker, asset.name),
        instrumentType: inferFallbackInstrumentType(asset.ticker, asset.name, index),
      }));
    }

    return analysis.assets.map((asset, index) => {
      const existing = assets[index];
      return {
        id: existing?.id ?? `${asset.ticker}-${index}`,
        ticker: asset.ticker,
        name: asset.name || existing?.name || asset.ticker,
        color: existing?.color ?? "#0f766e",
        expectedReturn: asset.expectedReturn,
        volatility: asset.volatility,
        sector: asset.sector,
        instrumentType: asset.instrumentType,
      };
    });
  }, [analysis, assets]);

  const activeWeights = analysis ? analysis.assets.map((asset) => asset.weight) : demoWeights;
  const activeMetrics = analysis?.metrics ?? demoMetrics;
  const activeOptimizedMetrics = analysis?.optimizedMetrics ?? demoOptimizedMetrics;
  const activeOptimizedWeights = analysis?.optimizedWeights ?? demoOptimizedPoint.weights;
  const activePerformance = analysis?.performance ?? demoPerformance;
  const activeRiskFindings = analysis?.riskFindings ?? demoRiskFindings;
  const activeCorrelationMatrix = analysis?.correlationMatrix.values ?? buildFallbackCorrelationMatrix(assets);
  const activeSectorAllocation = analysis?.sectorAllocation ?? buildFallbackSectorAllocation(displayAssets, activeWeights);
  const isLive = analysis?.mode === "live";
  const canOpenAiWorkspace = Boolean(analysis);
  const isSearchOpen = searchRowIndex !== null;
  const weightSum = assets.reduce((sum, asset) => sum + Number(asset.weight || 0), 0);
  const isWeightSumValid = Math.abs(weightSum - 100) <= 0.5;
  const selectedProfile: InvestorProfile | null =
    selectedTimeHorizon && selectedRiskStyle
      ? {
          timeHorizon: selectedTimeHorizon,
          riskStyle: selectedRiskStyle,
        }
      : null;

  const sortedChartAssets = useMemo<RankedChartAsset[]>(
    () =>
      displayAssets
        .map((asset, index) => ({ ...asset, sortWeight: activeWeights[index] ?? 0 }))
        .filter((asset) => Boolean(asset.ticker))
        .sort((left, right) => right.sortWeight - left.sortWeight),
    [activeWeights, displayAssets],
  );

  const chartAssets = useMemo(() => sortedChartAssets.slice(0, 4), [sortedChartAssets]);
  const hiddenChartAssets = useMemo(() => sortedChartAssets.slice(4), [sortedChartAssets]);

  const optimizationRows = useMemo(
    () =>
      displayAssets
        .map((asset, index) => ({
          id: asset.id,
          ticker: asset.ticker,
          current: activeWeights[index] ?? 0,
          optimized: activeOptimizedWeights[index] ?? 0,
          delta: (activeOptimizedWeights[index] ?? 0) - (activeWeights[index] ?? 0),
        }))
        .sort((left, right) => Math.abs(right.delta) - Math.abs(left.delta)),
    [activeOptimizedWeights, activeWeights, displayAssets],
  );

  useEffect(() => {
    if (!isSearchOpen) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeSearchModal();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isSearchOpen]);

  useEffect(() => {
    if (!isAddMenuOpen) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (addMenuRef.current?.contains(event.target as Node)) {
        return;
      }
      setIsAddMenuOpen(false);
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsAddMenuOpen(false);
      }
    };

    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isAddMenuOpen]);

  useEffect(() => {
    if (!isSearchOpen) {
      return;
    }

    const normalizedQuery = debouncedSearchQuery.trim();
    if (normalizedQuery.length < MIN_SEARCH_QUERY_LENGTH) {
      setSearchResults([]);
      setSearchError(null);
      setIsSearching(false);
      return;
    }

    let isCurrent = true;
    setIsSearching(true);
    setSearchError(null);

    searchSecurities(normalizedQuery, 8)
      .then((response) => {
        if (!isCurrent) {
          return;
        }
        setSearchResults(response.results);
      })
      .catch((caughtError) => {
        if (!isCurrent) {
          return;
        }
        setSearchResults([]);
        setSearchError(caughtError instanceof Error ? caughtError.message : "Suche konnte nicht geladen werden.");
      })
      .finally(() => {
        if (isCurrent) {
          setIsSearching(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [debouncedSearchQuery, isSearchOpen]);

  useEffect(() => {
    if (analysis) {
      return;
    }
    setWorkspaceView("analysis");
  }, [analysis]);

  useEffect(() => {
    if (!saveFeedback && !exportFeedback) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setSaveFeedback(null);
      setExportFeedback(null);
    }, 3500);
    return () => window.clearTimeout(timeoutId);
  }, [exportFeedback, saveFeedback]);

  function resetAiState() {
    setWorkspaceView("analysis");
    setActiveAiStep(1);
    setSelectedFocusAreas(defaultFocusAreas);
    setSelectedTimeHorizon(null);
    setSelectedRiskStyle(null);
    setSelectedGoalPreset("diversify_broadly");
    setGoalNote("");
    setRecommendation(null);
    setAiError(null);
    setIsGeneratingRecommendation(false);
    setLastFollowUp(null);
  }

  function resetDerivedState() {
    setAnalysis(null);
    setError(null);
    resetAiState();
  }

  function invalidateRecommendationResult() {
    setRecommendation(null);
    setAiError(null);
  }

  function closeSearchModal() {
    setSearchRowIndex(null);
    setSearchQuery("");
    setSearchResults([]);
    setSearchError(null);
    setIsSearching(false);
  }

  function openSearchModal(index: number) {
    const asset = assets[index];
    setSearchRowIndex(index);
    setSearchQuery(asset.name !== "Neue Position" ? asset.name : asset.ticker);
    setSearchResults([]);
    setSearchError(null);
  }

  function updateAsset(index: number, changes: Partial<AssetInput>) {
    resetDerivedState();
    setAssets((currentAssets) =>
      currentAssets.map((asset, assetIndex) =>
        assetIndex === index ? syncAssetMetadata({ ...asset, ...changes }, assetIndex) : syncAssetMetadata(asset, assetIndex),
      ),
    );
  }

  function appendAsset(seed: Partial<Omit<AssetInput, "id">>, options: { preserveName?: boolean } = {}) {
    resetDerivedState();
    setAssets((currentAssets) => {
      if (currentAssets.length >= 10) {
        return currentAssets;
      }

      const nextIndex = currentAssets.length;
      const nextAsset = syncAssetMetadata(createAssetInput(seed, nextIndex), nextIndex, options);
      return [...currentAssets, nextAsset];
    });
  }

  function handleAddPosition(option: AddPositionOption) {
    appendAsset(
      {
        ticker: option.ticker,
        name: option.label,
        weight: 0,
        color: option.accent,
      },
      { preserveName: option.ticker === "" },
    );
    setIsAddMenuOpen(false);
  }

  function removeAssetRow(index: number) {
    if (assets.length <= 2) {
      return;
    }
    resetDerivedState();
    setAssets((currentAssets) =>
      currentAssets
        .filter((_, assetIndex) => assetIndex !== index)
        .map((asset, assetIndex) => syncAssetMetadata(asset, assetIndex)),
    );
  }

  function resetPortfolio() {
    setAssets(initialAssets);
    setPeriodYears(5);
    resetDerivedState();
    closeSearchModal();
    setIsAddMenuOpen(false);
    setActiveSavedPortfolioId("");
    setPortfolioName("");
    setSaveFeedback(null);
  }

  function handleSavePortfolio() {
    const nextSavedPortfolios = savePortfolioRecord(savedPortfolios, portfolioName, assets, analysis);
    const savedName = portfolioName.trim() || "Unbenanntes Portfolio";
    const wasExisting = savedPortfolios.some((item) => item.name.toLowerCase() === savedName.toLowerCase());
    const savedRecord = nextSavedPortfolios.find((item) => item.name.toLowerCase() === savedName.toLowerCase());

    setSavedPortfolios(nextSavedPortfolios);
    setPortfolioName(savedRecord?.name ?? savedName);
    setActiveSavedPortfolioId(savedRecord?.id ?? "");
    setSaveFeedback(wasExisting ? "Portfolio aktualisiert" : "Portfolio gespeichert");
  }

  function handleLoadPortfolio(id: string) {
    const record = savedPortfolios.find((item) => item.id === id);
    if (!record) {
      return;
    }

    setAssets(record.assets.map((asset, index) => syncAssetMetadata({ ...asset }, index, { preserveName: true })));
    setAnalysis(record.lastAnalysis ?? null);
    resetAiState();
    setError(null);
    setPortfolioName(record.name);
    setActiveSavedPortfolioId(record.id);
    setSaveFeedback(record.lastAnalysis ? "Portfolio inklusive letzter Analyse geladen" : "Portfolio geladen");
  }

  function handleDeletePortfolio() {
    if (!activeSavedPortfolioId) {
      return;
    }
    const record = savedPortfolios.find((item) => item.id === activeSavedPortfolioId);
    setSavedPortfolios(deletePortfolioRecord(savedPortfolios, activeSavedPortfolioId));
    setActiveSavedPortfolioId("");
    setSaveFeedback(record ? `„${record.name}“ geloescht` : "Portfolio geloescht");
  }

  function handlePeriodChange(nextValue: PeriodPreset) {
    setPeriodYears(nextValue);
    resetDerivedState();
  }

  function applySearchSelection(result: SecuritySearchResult) {
    if (searchRowIndex === null) {
      return;
    }

    resetDerivedState();
    setAssets((currentAssets) =>
      currentAssets.map((asset, assetIndex) =>
        assetIndex === searchRowIndex
          ? syncAssetMetadata(
              {
                ...asset,
                ticker: result.symbol,
                name: result.name,
                expectedReturn: DEFAULT_EXPECTED_RETURN,
                volatility: DEFAULT_VOLATILITY,
              },
              assetIndex,
              { preserveName: true },
            )
          : syncAssetMetadata(asset, assetIndex),
      ),
    );
    closeSearchModal();
  }

  async function handleAnalyze() {
    const normalizedAssets = assets.map((asset, index) =>
      syncAssetMetadata({ ...asset, ticker: asset.ticker.trim().toUpperCase() }, index),
    );
    const tickers = normalizedAssets.map((asset) => asset.ticker);
    const duplicates = new Set<string>();
    const unique = new Set<string>();
    for (const ticker of tickers) {
      if (unique.has(ticker)) {
        duplicates.add(ticker);
      }
      unique.add(ticker);
    }

    if (normalizedAssets.some((asset) => !asset.ticker)) {
      setError("Bitte fuelle fuer alle Positionen einen Ticker aus.");
      setAssets(normalizedAssets);
      return;
    }

    if (duplicates.size > 0) {
      setError(`Bitte entferne doppelte Ticker: ${Array.from(duplicates).join(", ")}`);
      setAssets(normalizedAssets);
      return;
    }

    if (!isWeightSumValid) {
      setError("Die Gewichtung sollte in Summe 100 Prozent ergeben.");
      setAssets(normalizedAssets);
      return;
    }

    setAssets(normalizedAssets);
    setIsLoading(true);
    setError(null);
    resetAiState();

    try {
      const nextAnalysis = await analyzePortfolio({
        tickers,
        weights: normalizedAssets.map((asset) => asset.weight),
        startDate,
        endDate,
        frequency: "1d",
        riskFreeRate: 0.025,
        varConfidence: 0.95,
      });
      setAnalysis(nextAnalysis);
    } catch (caughtError) {
      setAnalysis(null);
      setError(caughtError instanceof Error ? caughtError.message : "Analyse konnte nicht geladen werden.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleWorkspaceChange(nextView: WorkspaceView) {
    if (nextView === "ai" && !canOpenAiWorkspace) {
      return;
    }
    setWorkspaceView(nextView);
  }

  function toggleFocusArea(area: FocusArea) {
    invalidateRecommendationResult();
    setSelectedFocusAreas((current) => {
      if (current.includes(area)) {
        if (current.length === 1) {
          return current;
        }
        return current.filter((item) => item !== area);
      }
      return [...current, area];
    });
  }

  function selectTimeHorizon(nextValue: TimeHorizon) {
    invalidateRecommendationResult();
    setSelectedTimeHorizon(nextValue);
  }

  function selectRiskStyle(nextValue: RiskStyle) {
    invalidateRecommendationResult();
    setSelectedRiskStyle(nextValue);
  }

  function selectGoalPreset(nextValue: GoalPreset) {
    invalidateRecommendationResult();
    setSelectedGoalPreset(nextValue);
  }

  function updateGoalNote(nextValue: string) {
    invalidateRecommendationResult();
    setGoalNote(nextValue);
  }

  function canProceedFromStep(step: AiStep) {
    if (step === 1) {
      return selectedFocusAreas.length > 0;
    }
    if (step === 2) {
      return Boolean(selectedTimeHorizon && selectedRiskStyle);
    }
    if (step === 3) {
      return Boolean(selectedGoalPreset);
    }
    return Boolean(recommendation);
  }

  function goToNextAiStep() {
    if (activeAiStep === 1 && !canProceedFromStep(1)) {
      return;
    }
    if (activeAiStep === 2 && !canProceedFromStep(2)) {
      return;
    }
    if (activeAiStep === 3 && !canProceedFromStep(3)) {
      return;
    }
    setActiveAiStep((current) => Math.min(4, current + 1) as AiStep);
  }

  function goToPreviousAiStep() {
    setActiveAiStep((current) => Math.max(1, current - 1) as AiStep);
  }

  async function handleGenerateRecommendation(followUpQuestion?: string) {
    if (!analysis) {
      setAiError("Bitte fuehre zuerst eine Analyse durch.");
      return;
    }
    if (selectedFocusAreas.length === 0) {
      setAiError("Bitte waehle mindestens einen Analysefokus aus.");
      setActiveAiStep(1);
      return;
    }
    if (!selectedProfile) {
      setAiError("Bitte lege zuerst Zeithorizont und Risikotyp fest.");
      setActiveAiStep(2);
      return;
    }

    setActiveAiStep(4);
    setIsGeneratingRecommendation(true);
    setAiError(null);

    const combinedGoalNote = [goalNote.trim(), followUpQuestion ? `Schnellfrage: ${followUpQuestion}` : ""]
      .filter(Boolean)
      .join("\n");

    try {
      const nextRecommendation = await recommendPortfolio({
        analysis,
        focusAreas: selectedFocusAreas,
        investorProfile: selectedProfile,
        goalPreset: selectedGoalPreset,
        goalNote: combinedGoalNote || undefined,
      });
      setRecommendation(nextRecommendation);
      setLastFollowUp(followUpQuestion ?? null);
    } catch (caughtError) {
      setRecommendation(null);
      setAiError(caughtError instanceof Error ? caughtError.message : "KI-Auswertung konnte nicht geladen werden.");
    } finally {
      setIsGeneratingRecommendation(false);
    }
  }

  async function handleExport(format: "csv" | "pdf") {
    if (!analysis) {
      setExportFeedback("Bitte zuerst eine Analyse erstellen");
      return;
    }

    setIsExporting(format);
    setExportFeedback(null);
    try {
      const report = await exportPortfolioReport(format, analysis, recommendation?.actionItems ?? analysis.recommendations);
      const url = URL.createObjectURL(report);
      const link = document.createElement("a");
      link.href = url;
      link.download = `portfolio-analyse.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setExportFeedback(`${format.toUpperCase()}-Export erstellt`);
    } catch (caughtError) {
      setExportFeedback(caughtError instanceof Error ? caughtError.message : "Export konnte nicht erstellt werden.");
    } finally {
      setIsExporting(null);
    }
  }

  return (
    <div className="dashboard-screen">
      <header className="app-header">
        <div className="header-copy">
          <p className="eyebrow">Portfolio Workspace</p>
          <h1>Portfolioanalyse</h1>
          <p>Historische Kennzahlen, Risiken und gefuehrte Entscheidungen an einem Ort.</p>
        </div>

        <div className="header-actions" aria-label="Analyse Steuerung">
          <div className="workspace-switch" role="tablist" aria-label="Arbeitsbereich">
            <button
              type="button"
              className={workspaceView === "analysis" ? "active" : ""}
              onClick={() => handleWorkspaceChange("analysis")}
            >
              Analyse
            </button>
            <button
              type="button"
              className={workspaceView === "ai" ? "active" : ""}
              onClick={() => handleWorkspaceChange("ai")}
              disabled={!canOpenAiWorkspace}
            >
              KI-Bericht
            </button>
          </div>

          <div className="period-switch" role="group" aria-label="Zeitraum">
            {periodOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={periodYears === option.value ? "active" : ""}
                onClick={() => handlePeriodChange(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className={`status-pill ${isLoading ? "loading" : isLive ? "live" : "fallback"}`} aria-live="polite">
            <span />
            {isLoading ? "Daten werden geladen" : isLive ? "Live-Daten" : "Demo-Daten"}
          </div>

          <div className="export-actions" aria-label="Bericht exportieren">
            <button
              type="button"
              className="export-button"
              onClick={() => handleExport("csv")}
              disabled={!analysis || isExporting !== null}
              title={analysis ? "CSV-Bericht herunterladen" : "Export wird nach der Analyse verfuegbar"}
            >
              {isExporting === "csv" ? <RefreshCw className="spinning" size={14} /> : <FileSpreadsheet size={14} />}
              CSV
            </button>
            <button
              type="button"
              className="export-button"
              onClick={() => handleExport("pdf")}
              disabled={!analysis || isExporting !== null}
              title={analysis ? "PDF-Bericht herunterladen" : "Export wird nach der Analyse verfuegbar"}
            >
              {isExporting === "pdf" ? <RefreshCw className="spinning" size={14} /> : <FileText size={14} />}
              PDF
            </button>
          </div>

          <button className="toolbar-button primary" type="button" onClick={handleAnalyze} disabled={isLoading}>
            {isLoading ? <RefreshCw className="spinning" size={16} /> : <Database size={16} />}
            {isLoading ? "Analyse laeuft" : "Analyse starten"}
          </button>
        </div>
      </header>

      <div className="dashboard-layout">
        <aside className="portfolio-sidebar panel" aria-label="Portfolio Builder">
          <div className="builder-header">
            <div>
              <span className="section-kicker">Portfolio</span>
              <h2>Aktuelle Allokation</h2>
              <p>Gewichte festlegen, dann analysieren.</p>
            </div>
            <button className="ghost-button reset-button" type="button" onClick={resetPortfolio} title="Standardportfolio wiederherstellen">
              <RotateCcw size={15} />
              <span>Zuruecksetzen</span>
            </button>
          </div>

          <div className="builder-status" aria-label="Portfolio Status">
            <span>{formatShortDateRange(startDate, endDate)}</span>
            <span aria-hidden="true">•</span>
            <strong>{assets.length} Positionen</strong>
          </div>

          <details className="portfolio-library">
            <summary>
              <span><Save size={14} aria-hidden="true" /> Arbeitsstand speichern oder laden</span>
              <span className="library-count">{savedPortfolios.length}</span>
            </summary>
            <div className="library-content" aria-labelledby="portfolio-library-title">
              <strong id="portfolio-library-title">Lokaler Arbeitsstand</strong>
              <div className="library-save-row">
                <input
                  aria-label="Name des Portfolios"
                  placeholder="z. B. Langfristig"
                  value={portfolioName}
                  onChange={(event) => setPortfolioName(event.target.value)}
                />
                <button type="button" className="compact-action" onClick={handleSavePortfolio}>
                  <Save size={14} />
                  Speichern
                </button>
              </div>
              <div className="library-load-row">
                <select
                  aria-label="Gespeichertes Portfolio laden"
                  value={activeSavedPortfolioId}
                  onChange={(event) => handleLoadPortfolio(event.target.value)}
                >
                  <option value="">Gespeicherte Portfolios</option>
                  {savedPortfolios.map((portfolio) => (
                    <option key={portfolio.id} value={portfolio.id}>
                      {portfolio.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="icon-action danger"
                  onClick={handleDeletePortfolio}
                  disabled={!activeSavedPortfolioId}
                  aria-label="Ausgewaehltes Portfolio loeschen"
                  title="Ausgewaehltes Portfolio loeschen"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              {saveFeedback ? <p className="library-feedback" role="status">{saveFeedback}</p> : null}
            </div>
          </details>

          <section className="builder-grid" aria-label="Portfolio Positionen">
            <div className="holding-list-heading" aria-hidden="true">
              <span>Instrument</span>
              <span>Gewicht</span>
            </div>
            {assets.map((asset, index) => (
              <article className="holding-row" key={asset.id}>
                <div className="row-index" style={{ backgroundColor: asset.color }}>
                  {index + 1}
                </div>

                <label className="holding-instrument">
                  <input
                    aria-label={`Ticker ${index + 1}`}
                    placeholder="z. B. AAPL"
                    value={asset.ticker}
                    onChange={(event) => updateAsset(index, { ticker: event.target.value })}
                  />
                  <small>{asset.name}</small>
                </label>

                <button
                  type="button"
                  className="search-trigger"
                  onClick={() => openSearchModal(index)}
                  aria-label={`Position ${index + 1} suchen`}
                  title="Instrument suchen"
                >
                  <Search size={15} />
                </button>

                <label className="holding-weight">
                  <input
                    aria-label={`Gewichtung ${asset.ticker || index + 1}`}
                    min="0"
                    max="100"
                    step="1"
                    type="number"
                    value={asset.weight}
                    onChange={(event) => updateAsset(index, { weight: Number(event.target.value) })}
                  />
                  <span>%</span>
                </label>

                <button
                  type="button"
                  className="row-remove"
                  onClick={() => removeAssetRow(index)}
                  disabled={assets.length <= 2}
                  aria-label={`Position ${index + 1} entfernen`}
                >
                  <X size={15} />
                </button>
              </article>
            ))}
          </section>

          <div className="sidebar-actions">
            <div className="add-position-shell" ref={addMenuRef}>
              <button
                type="button"
                className="toolbar-button add-position-toggle"
                onClick={() => setIsAddMenuOpen((currentValue) => !currentValue)}
                disabled={assets.length >= 10}
                aria-label="Position hinzufuegen"
                aria-expanded={isAddMenuOpen}
                aria-controls="add-position-menu"
                title="Position hinzufuegen"
              >
                <Plus size={15} />
                <span>Hinzufuegen</span>
                <ChevronDown size={14} className={`add-position-chevron ${isAddMenuOpen ? "open" : ""}`} />
              </button>

              {isAddMenuOpen ? (
                <div className="add-position-menu" id="add-position-menu" role="menu" aria-label="Position hinzufuegen">
                  {addPositionOptions.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      className="add-position-option"
                      onClick={() => handleAddPosition(option)}
                      role="menuitem"
                    >
                      <span className="add-position-swatch" style={{ backgroundColor: option.accent }} aria-hidden="true" />
                      <span className="add-position-copy">
                        <strong>{option.label}</strong>
                        <span>{option.description}</span>
                      </span>
                      {option.ticker ? (
                        <span className="add-position-ticker">{option.ticker}</span>
                      ) : (
                        <span className="add-position-ticker muted">Custom</span>
                      )}
                    </button>
                  ))}
                  <p className="add-position-hint">
                    Die Auswahl legt die erste Zeile an. Danach kannst du jeden Ticker im Feld oder per Lupe anpassen.
                  </p>
                </div>
              ) : null}
            </div>
            <button className="sidebar-primary" type="button" onClick={handleAnalyze} disabled={isLoading}>
              <TrendingUp size={15} />
              Jetzt auswerten
            </button>
          </div>

          <div className={`weight-sum ${isWeightSumValid ? "valid" : "invalid"}`}>
            <span>Gewichtungssumme</span>
            <strong>{weightSum.toFixed(0)} %</strong>
          </div>
        </aside>

        <main className="analysis-board">
          {error ? <div className="notice error">{error}</div> : null}
          {workspaceView === "ai" && aiError ? <div className="notice error">{aiError}</div> : null}
          {exportFeedback ? <div className="notice feedback" role="status"><Download size={14} />{exportFeedback}</div> : null}

          {isLoading ? (
            <AnalysisSkeleton />
          ) : workspaceView === "analysis" ? (
            <>
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
                  icon={<ShieldCheck size={18} />}
                  label="Sharpe Ratio"
                  value={activeMetrics.sharpeRatio.toFixed(2)}
                  helper={`Optimiert: ${activeOptimizedMetrics.sharpeRatio.toFixed(2)}`}
                  tone="positive"
                />
                <MetricCard
                  icon={<AlertTriangle size={18} />}
                  label="Value at Risk (95%)"
                  value={`-${formatPercent(activeMetrics.valueAtRisk)}`}
                  helper="Historisch auf Basis des Analysezeitraums"
                  tone="warning"
                />
              </section>

              <article className="panel analysis-cta-panel">
                <div className="ai-mark analysis-cta-mark">
                  <BrainCircuit size={22} />
                </div>
                <div className="analysis-cta-copy">
                  <h2>KI-Auswertung mit Anlegerprofil</h2>
                  <p>
                    Nach der Analyse kannst du in einen gefuehrten KI-Workspace wechseln und Fokus, Anlegerprofil und
                    Verbesserungsziel festlegen.
                  </p>
                </div>
                <button
                  type="button"
                  className="toolbar-button primary"
                  disabled={!canOpenAiWorkspace}
                  onClick={() => handleWorkspaceChange("ai")}
                >
                  {canOpenAiWorkspace ? "Zur KI-Auswertung wechseln" : "Erst Analyse durchfuehren"}
                </button>
              </article>

              <article className="panel performance-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Normalisierte Wertentwicklung</h2>
                    <p>
                      {hiddenChartAssets.length > 0
                        ? "Portfolio plus die vier groessten Positionen im Vergleich."
                        : "Portfolio plus alle ausgewaehlten Positionen im Vergleich."}
                    </p>
                  </div>
                </div>
                <div className="legend-row">
                  <span className="legend-chip portfolio-line">Portfolio</span>
                  {chartAssets.map((asset) => (
                    <span className="legend-chip" key={asset.id}>
                      <span className="legend-dot" style={{ backgroundColor: asset.color }} />
                      {asset.ticker}
                    </span>
                  ))}
                </div>
                {hiddenChartAssets.length > 0 ? (
                  <div className="chart-overflow-row">
                    <span className="chart-overflow-label">Nicht im Chart:</span>
                    {hiddenChartAssets.map((asset) => (
                      <span className="legend-chip legend-chip-muted" key={`hidden-${asset.id}`}>
                        <span className="legend-dot" style={{ backgroundColor: asset.color }} />
                        {asset.ticker}
                      </span>
                    ))}
                  </div>
                ) : null}
                <div className="chart-frame performance-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={activePerformance} margin={{ top: 10, right: 18, left: 2, bottom: 0 }}>
                      <CartesianGrid stroke="#dbe6f2" strokeDasharray="4 4" />
                      <XAxis dataKey="month" tickLine={false} axisLine={false} minTickGap={18} />
                      <YAxis
                        tickLine={false}
                        axisLine={false}
                        domain={["dataMin - 3", "dataMax + 4"]}
                        tickFormatter={(value) => Number(value).toFixed(0)}
                        width={42}
                      />
                      <Tooltip contentStyle={{ borderRadius: 10, borderColor: "#d8dee8" }} />
                      <Line
                        dataKey="portfolio"
                        name="Portfolio"
                        stroke="#0b3b63"
                        dot={false}
                        isAnimationActive={false}
                        strokeWidth={3}
                        type="monotone"
                      />
                      {chartAssets.map((asset) => (
                        <Line
                          dataKey={asset.ticker}
                          key={asset.id}
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

              <section className="analysis-detail-grid">
                <article className="panel heatmap-panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Korrelationsmatrix</h2>
                      <p>Zeigt, welche Positionen sich historisch aehnlich bewegen.</p>
                    </div>
                  </div>
                  <div className="heatmap-scroll">
                    <CorrelationHeatmap assets={displayAssets} values={activeCorrelationMatrix} />
                  </div>
                  <div className="correlation-scale" aria-hidden="true">
                    <span>-1,0</span>
                    <div />
                    <span>1,0</span>
                  </div>
                </article>

                <div className="analysis-side-column">
                  <article className="panel comparison-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Optimierte Alternative</h2>
                        <p>Eine datenbasierte Vergleichsvariante fuer ein besseres Rendite-Risiko-Verhaeltnis.</p>
                      </div>
                    </div>

                    <div className="comparison-metrics">
                      <div>
                        <span>Rendite</span>
                        <strong>{formatPercent(activeOptimizedMetrics.expectedReturn)}</strong>
                      </div>
                      <div>
                        <span>Volatilitaet</span>
                        <strong>{formatPercent(activeOptimizedMetrics.volatility)}</strong>
                      </div>
                      <div>
                        <span>Sharpe</span>
                        <strong>{activeOptimizedMetrics.sharpeRatio.toFixed(2)}</strong>
                      </div>
                    </div>

                    <div className="weight-comparison-list">
                      {optimizationRows.map((row) => (
                        <div className="comparison-row" key={row.id}>
                          <strong>{row.ticker || "Offene Position"}</strong>
                          <span>{percentFormatter.format(row.current)}</span>
                          <span className={row.delta >= 0 ? "delta-positive" : "delta-negative"}>
                            {row.delta >= 0 ? "+" : ""}
                            {percentFormatter.format(row.delta)}
                          </span>
                          <span>{percentFormatter.format(row.optimized)}</span>
                        </div>
                      ))}
                    </div>
                  </article>

                  <article className="panel findings-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Auffaelligkeiten</h2>
                        <p>Regelbasierte Hinweise, die spaeter in die KI-Auswertung einfliessen.</p>
                      </div>
                    </div>

                    <div className="finding-list">
                      {activeRiskFindings.slice(0, 4).map((finding, index) => (
                        <article className={`finding-card severity-${finding.severity}`} key={`${finding.type}-${index}`}>
                          <strong>{getFindingTitle(finding)}</strong>
                          <p>{finding.message}</p>
                        </article>
                      ))}
                    </div>
                  </article>
                </div>
              </section>
            </>
          ) : (
            <section className="ai-workspace">
              <div className="kpi-row ai-kpi-row" aria-label="KPI Snapshot">
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
                  icon={<ShieldCheck size={18} />}
                  label="Sharpe Ratio"
                  value={activeMetrics.sharpeRatio.toFixed(2)}
                  helper={`Optimiert: ${activeOptimizedMetrics.sharpeRatio.toFixed(2)}`}
                  tone="positive"
                />
                <MetricCard
                  icon={<AlertTriangle size={18} />}
                  label="Value at Risk (95%)"
                  value={`-${formatPercent(activeMetrics.valueAtRisk)}`}
                  helper={`Zeitraum: ${periodOptions.find((option) => option.value === periodYears)?.label ?? "5 Jahre"}`}
                  tone="warning"
                />
              </div>

              <article className="panel ai-workspace-panel">
                <div className="panel-heading ai-workspace-heading">
                  <div>
                    <h2>KI-Auswertung</h2>
                    <p>
                      Lege Analysefokus, Anlegerprofil und Verbesserungsziel fest. Danach erzeugt die KI eine
                      nachvollziehbare Portfolio-Auswertung.
                    </p>
                  </div>
                  <button type="button" className="ghost-button" onClick={() => handleWorkspaceChange("analysis")}>
                    Zur Analyse
                  </button>
                </div>

                <div className="ai-stepper" role="list" aria-label="KI Schritte">
                  {[
                    { id: 1 as AiStep, title: "Analysefokus" },
                    { id: 2 as AiStep, title: "Anlegerprofil" },
                    { id: 3 as AiStep, title: "Verbesserungsziel" },
                    { id: 4 as AiStep, title: "KI-Auswertung" },
                  ].map((step) => {
                    const isActive = activeAiStep === step.id;
                    const isDone = activeAiStep > step.id || (step.id === 4 && Boolean(recommendation));
                    return (
                      <button
                        key={step.id}
                        type="button"
                        className={`ai-step ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}
                        onClick={() => setActiveAiStep(step.id)}
                      >
                        <span className="ai-step-index">{isDone ? <Check size={14} /> : step.id}</span>
                        <span>{step.title}</span>
                      </button>
                    );
                  })}
                </div>

                <div className="ai-context-strip">
                  <article className="ai-context-card">
                    <span>Analysefokus</span>
                    <strong>{selectedFocusAreas.map((area) => focusAreaLabel(area)).join(", ")}</strong>
                    <p>Die KI priorisiert diese Themen in der finalen Auswertung.</p>
                  </article>
                  <article className="ai-context-card">
                    <span>Anlegerprofil</span>
                    <strong>{selectedProfile ? profileLabel(selectedProfile) : "Noch nicht ausgewaehlt"}</strong>
                    <p>
                      {selectedProfile
                        ? profileDescription(selectedProfile)
                        : "Waehle Zeithorizont und Risikotyp, damit die KI passend priorisiert."}
                    </p>
                  </article>
                  <article className="ai-context-card">
                    <span>Verbesserungsziel</span>
                    <strong>{goalPresetLabel(selectedGoalPreset)}</strong>
                    <p>{goalPresetOptions.find((option) => option.id === selectedGoalPreset)?.description}</p>
                  </article>
                </div>

                {activeAiStep === 1 ? (
                  <div className="ai-step-content">
                    <div className="panel ai-inner-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>1. Was soll die KI besonders analysieren?</h2>
                          <p>Die Fokusauswahl bestimmt, welche Aspekte im finalen Report besonders stark gewichtet werden.</p>
                        </div>
                      </div>

                      <div className="selection-grid">
                        {focusAreaOptions.map((option) => {
                          const isSelected = selectedFocusAreas.includes(option.id);
                          return (
                            <button
                              key={option.id}
                              type="button"
                              className={`selection-card ${isSelected ? "selected" : ""}`}
                              onClick={() => toggleFocusArea(option.id)}
                            >
                              <strong>{option.label}</strong>
                              <p>{option.description}</p>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="ai-step-grid">
                      <article className="panel sector-panel">
                        <div className="panel-heading">
                          <div>
                            <h2>Branchengewichtung</h2>
                            <p>So verteilt sich dein Portfolio aktuell ueber Branchen und Themenfelder.</p>
                          </div>
                        </div>
                        <SectorAllocationBars items={activeSectorAllocation} />
                      </article>

                      <article className="panel findings-panel">
                        <div className="panel-heading">
                          <div>
                            <h2>Wichtige Auffaelligkeiten</h2>
                            <p>Diese Hinweise bilden die Datenbasis fuer die spaetere KI-Interpretation.</p>
                          </div>
                        </div>

                        <div className="finding-list">
                          {activeRiskFindings.slice(0, 4).map((finding, index) => (
                            <article className={`finding-card severity-${finding.severity}`} key={`${finding.type}-${index}`}>
                              <strong>{getFindingTitle(finding)}</strong>
                              <p>{finding.message}</p>
                            </article>
                          ))}
                        </div>
                      </article>
                    </div>
                  </div>
                ) : null}

                {activeAiStep === 2 ? (
                  <div className="ai-step-content">
                    <div className="panel ai-inner-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>2. Welches Anlegerprofil soll die KI beruecksichtigen?</h2>
                          <p>Die Auswahl steuert, ob die KI eher auf Stabilitaet, Balance oder Wachstum priorisiert.</p>
                        </div>
                      </div>

                      <div className="profile-groups">
                        <section className="profile-group">
                          <h3>Zeithorizont</h3>
                          <div className="selection-grid compact">
                            {timeHorizonOptions.map((option) => (
                              <button
                                key={option.id}
                                type="button"
                                className={`selection-card ${selectedTimeHorizon === option.id ? "selected" : ""}`}
                                onClick={() => selectTimeHorizon(option.id)}
                              >
                                <strong>{option.label}</strong>
                                <p>{option.description}</p>
                              </button>
                            ))}
                          </div>
                        </section>

                        <section className="profile-group">
                          <h3>Risikotyp</h3>
                          <div className="selection-grid compact">
                            {riskStyleOptions.map((option) => (
                              <button
                                key={option.id}
                                type="button"
                                className={`selection-card ${selectedRiskStyle === option.id ? "selected" : ""}`}
                                onClick={() => selectRiskStyle(option.id)}
                              >
                                <strong>{option.label}</strong>
                                <p>{option.description}</p>
                              </button>
                            ))}
                          </div>
                        </section>
                      </div>
                    </div>
                  </div>
                ) : null}

                {activeAiStep === 3 ? (
                  <div className="ai-step-content">
                    <div className="panel ai-inner-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>3. Was ist dein Verbesserungsziel?</h2>
                          <p>Die KI kombiniert jetzt dein Ziel mit den Kennzahlen, der Branchenstruktur und dem Anlegerprofil.</p>
                        </div>
                      </div>

                      <div className="selection-grid">
                        {goalPresetOptions.map((option) => (
                          <button
                            key={option.id}
                            type="button"
                            className={`selection-card ${selectedGoalPreset === option.id ? "selected" : ""}`}
                            onClick={() => selectGoalPreset(option.id)}
                          >
                            <strong>{option.label}</strong>
                            <p>{option.description}</p>
                          </button>
                        ))}
                      </div>

                      <label className="goal-note-field">
                        <span>Optionaler Zusatzfokus</span>
                        <textarea
                          rows={4}
                          placeholder="z. B. Bitte besonders auf Branchenbreite und Nachrichtenlage bei Tech-Titeln achten."
                          value={goalNote}
                          onChange={(event) => updateGoalNote(event.target.value)}
                        />
                      </label>
                    </div>
                  </div>
                ) : null}

                {activeAiStep === 4 ? (
                  <div className="ai-step-content">
                    <div className="panel ai-inner-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>4. KI-Auswertung erzeugen</h2>
                          <p>
                            Die KI verbindet jetzt deine Auswahl mit der historischen Analyse, der Branchenstruktur und
                            optionalen News-Hinweisen.
                          </p>
                        </div>
                        <button
                          type="button"
                          className="toolbar-button primary"
                          onClick={() => handleGenerateRecommendation()}
                          disabled={isGeneratingRecommendation}
                        >
                          {isGeneratingRecommendation ? <RefreshCw className="spinning" size={15} /> : <BrainCircuit size={15} />}
                          {isGeneratingRecommendation ? "KI analysiert" : recommendation ? "Neu generieren" : "KI-Auswertung erstellen"}
                        </button>
                      </div>

                      <div className="generation-summary">
                        <div>
                          <span>Aktiver Fokus</span>
                          <strong>{selectedFocusAreas.map((area) => focusAreaLabel(area)).join(", ")}</strong>
                        </div>
                        <div>
                          <span>Anlegerprofil</span>
                          <strong>{selectedProfile ? profileLabel(selectedProfile) : "Nicht gesetzt"}</strong>
                        </div>
                        <div>
                          <span>Ziel</span>
                          <strong>{goalPresetLabel(selectedGoalPreset)}</strong>
                        </div>
                      </div>

                      {isGeneratingRecommendation ? (
                        <div className="notice loading">
                          <RefreshCw className="spinning" size={14} />
                          Die KI erstellt gerade die Auswertung inklusive Profilbezug, Branchenblick und Handlungsschritten.
                        </div>
                      ) : null}
                    </div>

                    {recommendation ? (
                      <div className="recommendation-grid">
                        <article className="panel recommendation-hero">
                          <div className="panel-heading">
                            <div>
                              <h2>Kurzfazit</h2>
                              <p>Die KI fasst die aktuelle Portfolio-Situation auf Basis deiner Auswahl zusammen.</p>
                            </div>
                          </div>
                          <p>{recommendation.summary}</p>
                        </article>

                        <section className="quick-followup" aria-labelledby="quick-followup-title">
                          <div>
                            <span>Weiterdenken</span>
                            <strong id="quick-followup-title">Eine Frage gezielt vertiefen</strong>
                            <p>
                              {lastFollowUp
                                ? `Letzte Schnellfrage: ${lastFollowUp}`
                                : "Die Frage wird als zusätzlicher Kontext mit der bestehenden Analyse ausgewertet."}
                            </p>
                          </div>
                          <div className="quick-followup-actions">
                            {quickFollowUpQuestions.map((question) => (
                              <button
                                key={question}
                                type="button"
                                onClick={() => handleGenerateRecommendation(question)}
                                disabled={isGeneratingRecommendation}
                              >
                                <MessageCircleQuestion size={14} />
                                {question}
                              </button>
                            ))}
                          </div>
                        </section>

                        <article className="panel ai-result-panel">
                          <div className="panel-heading">
                            <div>
                              <h2>Profilbezug</h2>
                              <p>So wurde dein Anlegerprofil in die Interpretation einbezogen.</p>
                            </div>
                          </div>
                          <p>{recommendation.profileFit}</p>
                        </article>

                        <article className="panel ai-result-panel">
                          <div className="panel-heading">
                            <div>
                              <h2>Analyse-Highlights</h2>
                              <p>Die wichtigsten Kennzahlen- und Risikoaussagen fuer deine Auswahl.</p>
                            </div>
                          </div>
                          <ul className="report-list">
                            {recommendation.analysisHighlights.map((item) => (
                              <li key={item}>{item}</li>
                            ))}
                          </ul>
                        </article>

                        <article className="panel ai-result-panel">
                          <div className="panel-heading">
                            <div>
                              <h2>Branchenblick</h2>
                              <p>Einordnung der aktuellen Schwerpunkte und moeglicher Luecken.</p>
                            </div>
                          </div>
                          <ul className="report-list">
                            {recommendation.sectorInsights.map((item) => (
                              <li key={item}>{item}</li>
                            ))}
                          </ul>
                        </article>

                        <article className="panel ai-result-panel">
                          <div className="panel-heading">
                            <div>
                              <h2>Konkrete Handlungsschritte</h2>
                              <p>Die KI leitet daraus nachvollziehbare naechste Schritte ab.</p>
                            </div>
                          </div>
                          <ol className="report-list ordered">
                            {recommendation.actionItems.map((item) => (
                              <li key={item}>{item}</li>
                            ))}
                          </ol>
                        </article>

                        <article className="panel ai-result-panel">
                          <div className="panel-heading">
                            <div>
                              <h2>Empfohlene Gewichtungsanpassungen</h2>
                              <p>Diese Anpassungen orientieren sich an deiner Zielsetzung und der Vergleichsvariante.</p>
                            </div>
                          </div>
                          <div className="weight-adjustment-list">
                            {recommendation.weightAdjustments.map((adjustment) => (
                              <article className="weight-adjustment-card" key={`${adjustment.ticker}-${adjustment.suggestedWeight}`}>
                                <div className="weight-adjustment-head">
                                  <strong>{adjustment.ticker}</strong>
                                  <span>
                                    {percentFormatter.format(adjustment.currentWeight)} →{" "}
                                    {percentFormatter.format(adjustment.suggestedWeight)}
                                  </span>
                                </div>
                                <p>{adjustment.reason}</p>
                              </article>
                            ))}
                          </div>
                        </article>

                        <div className="ai-result-split">
                          <article className="panel ai-result-panel">
                            <div className="panel-heading">
                              <div>
                                <h2>Neue Titelideen</h2>
                                <p>Beispielkandidaten fuer eine naechste Folgeanalyse.</p>
                              </div>
                            </div>
                            {recommendation.newIdeas.length > 0 ? (
                              <div className="idea-list">
                                {recommendation.newIdeas.map((idea) => (
                                  <article className="idea-card" key={idea.ticker}>
                                    <div className="idea-head">
                                      <strong>{idea.ticker}</strong>
                                      <span>{idea.sector}</span>
                                    </div>
                                    <p>{idea.name}</p>
                                    <small>{idea.reason}</small>
                                  </article>
                                ))}
                              </div>
                            ) : (
                              <p className="empty-copy">Aktuell wurden keine zusaetzlichen Titelideen abgeleitet.</p>
                            )}
                          </article>

                          <article className="panel ai-result-panel">
                            <div className="panel-heading">
                              <div>
                                <h2>Pruefkandidaten im Bestand</h2>
                                <p>Positionen, die im Kontext deiner Zielsetzung besondere Aufmerksamkeit verdienen.</p>
                              </div>
                            </div>
                            {recommendation.reviewCandidates.length > 0 ? (
                              <ul className="report-list">
                                {recommendation.reviewCandidates.map((candidate) => (
                                  <li key={`${candidate.ticker}-${candidate.reason}`}>
                                    <strong>{candidate.ticker}:</strong> {candidate.reason}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="empty-copy">Keine besonderen Pruefkandidaten gefunden.</p>
                            )}
                          </article>
                        </div>

                        <article className="panel ai-result-panel">
                          <div className="panel-heading">
                            <div>
                              <h2>Aktuelle Nachrichtenhinweise</h2>
                              <p>Nur fuer aktuell gehaltene Titel und nur, wenn verfuegbare Newsdaten geladen werden konnten.</p>
                            </div>
                          </div>
                          {recommendation.newsSignals.length > 0 ? (
                            <div className="news-list">
                              {recommendation.newsSignals.map((signal) => (
                                <a className="news-card" href={signal.url} key={`${signal.ticker}-${signal.url}`} target="_blank" rel="noreferrer">
                                  <div className="news-head">
                                    <strong>{signal.ticker}</strong>
                                    <span className={`sentiment-pill ${signal.sentimentLabel}`}>{sentimentLabel(signal.sentimentLabel)}</span>
                                  </div>
                                  <p>{signal.headline}</p>
                                </a>
                              ))}
                            </div>
                          ) : (
                            <p className="empty-copy">Keine aktuellen Nachrichtenhinweise verfuegbar.</p>
                          )}
                        </article>

                        <footer className="ai-report-footer">
                          <p>{recommendation.disclaimer}</p>
                          <span>
                            Quelle: {analysis?.dataSource ?? "Demo-Daten"} | Interpretation:{" "}
                            {recommendation.source === "ollama" ? `Ollama ${recommendation.model}` : "Regel-Fallback"}
                          </span>
                          <span>Zeitraum: {formatShortDateRange(startDate, endDate)}</span>
                          <span>Letzte Aktualisierung: {analysis ? formatDateTime(analysis.updatedAt) : "noch keine Live-Analyse"}</span>
                        </footer>
                      </div>
                    ) : null}
                  </div>
                ) : null}

                <div className="ai-step-actions">
                  <button type="button" className="ghost-button" onClick={goToPreviousAiStep} disabled={activeAiStep === 1}>
                    Zurueck
                  </button>
                  {activeAiStep < 4 ? (
                    <button
                      type="button"
                      className="toolbar-button primary"
                      onClick={goToNextAiStep}
                      disabled={
                        (activeAiStep === 1 && selectedFocusAreas.length === 0) ||
                        (activeAiStep === 2 && !selectedProfile) ||
                        isGeneratingRecommendation
                      }
                    >
                      Weiter
                    </button>
                  ) : null}
                </div>
              </article>
            </section>
          )}
        </main>
      </div>

      {isSearchOpen ? (
        <div className="search-modal-backdrop" role="presentation" onClick={closeSearchModal}>
          <section
            className="search-modal panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="security-search-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="panel-heading search-modal-header">
              <div>
                <h2 id="security-search-title">Position suchen</h2>
                <p>Suche nach Aktien und ETFs per Name oder Ticker und uebernimm den Treffer direkt ins Portfolio.</p>
              </div>
              <button type="button" className="row-remove modal-close" onClick={closeSearchModal} aria-label="Suche schliessen">
                <X size={15} />
              </button>
            </div>

            <label className="search-field">
              <span>Suche</span>
              <div className="ticker-input-group modal-input-group">
                <input
                  autoFocus
                  aria-label="Instrument suchen"
                  placeholder="z. B. Porsche, Apple, SPY"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                <div className="search-field-icon" aria-hidden="true">
                  <Search size={15} />
                </div>
              </div>
            </label>

            <div className="search-helper-row">
              <span>Aktuelle Zeile: Position {(searchRowIndex ?? 0) + 1}</span>
              <span>Datenquelle: Lokaler Schnellkatalog + Yahoo Finance</span>
            </div>

            {searchError ? <div className="notice error">{searchError}</div> : null}
            {!searchError && searchQuery.trim().length < MIN_SEARCH_QUERY_LENGTH ? (
              <div className="notice">Bitte mindestens 2 Zeichen eingeben, um passende Titel zu suchen.</div>
            ) : null}
            {isSearching ? (
              <div className="notice loading">
                <RefreshCw className="spinning" size={14} />
                Suche nach passenden Aktien und ETFs laeuft.
              </div>
            ) : null}

            {!isSearching && !searchError && searchQuery.trim().length >= MIN_SEARCH_QUERY_LENGTH ? (
              searchResults.length > 0 ? (
                <div className="search-results" role="list">
                  {searchResults.map((result) => (
                    <button
                      key={`${result.symbol}-${result.exchange}`}
                      type="button"
                      className="search-result"
                      onClick={() => applySearchSelection(result)}
                    >
                      <div className="search-result-copy">
                        <strong>{result.symbol}</strong>
                        <span>{result.name}</span>
                      </div>
                      <div className="search-result-meta">
                        <span>{formatInstrumentType(result.type)}</span>
                        <span>{result.exchange}</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="notice">Keine passenden Aktien oder ETFs gefunden.</div>
              )
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  );
}

function AnalysisSkeleton() {
  return (
    <section className="analysis-skeleton" aria-live="polite" aria-label="Analyse wird geladen">
      <div className="skeleton-intro">
        <RefreshCw className="spinning" size={17} />
        <div>
          <strong>Historische Daten werden ausgewertet</strong>
          <span>Kurse, Kennzahlen und die Vergleichsgewichtung werden vorbereitet.</span>
        </div>
      </div>
      <div className="skeleton-kpis" aria-hidden="true">
        {Array.from({ length: 4 }, (_, index) => (
          <div className="skeleton-block metric-skeleton" key={index}>
            <span />
            <strong />
            <small />
          </div>
        ))}
      </div>
      <div className="skeleton-block chart-skeleton" aria-hidden="true">
        <span className="skeleton-chart-title" />
        <div className="skeleton-chart-lines" />
      </div>
      <div className="skeleton-detail-row" aria-hidden="true">
        <div className="skeleton-block detail-skeleton" />
        <div className="skeleton-block detail-skeleton" />
      </div>
    </section>
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

function CorrelationHeatmap({ assets, values }: { assets: DisplayAsset[]; values: number[][] }) {
  return (
    <div className="heatmap" role="table" aria-label="Korrelationsmatrix">
      <div className="heatmap-row header-row" style={{ gridTemplateColumns: `60px repeat(${assets.length}, minmax(52px, 1fr))` }}>
        <span />
        {assets.map((asset, index) => (
          <strong key={asset.id}>{asset.ticker || `P${index + 1}`}</strong>
        ))}
      </div>

      {assets.map((asset, rowIndex) => (
        <div
          className="heatmap-row"
          key={asset.id}
          style={{ gridTemplateColumns: `60px repeat(${assets.length}, minmax(52px, 1fr))` }}
        >
          <strong>{asset.ticker || `P${rowIndex + 1}`}</strong>
          {assets.map((columnAsset, columnIndex) => {
            const value = values[rowIndex]?.[columnIndex] ?? 0;
            return (
              <span
                className="heatmap-cell"
                key={`${asset.id}-${columnAsset.id}`}
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

function SectorAllocationBars({ items }: { items: ApiSectorAllocation[] }) {
  return (
    <div className="sector-list">
      {items.map((item) => (
        <article className="sector-row" key={item.sector}>
          <div className="sector-row-head">
            <strong>{item.sector}</strong>
            <span>{percentFormatter.format(item.weight)}</span>
          </div>
          <div className="sector-bar-track" aria-hidden="true">
            <div className="sector-bar-fill" style={{ width: `${Math.max(item.weight * 100, 6)}%` }} />
          </div>
          <small>{item.tickers.join(", ")}</small>
        </article>
      ))}
    </div>
  );
}

function buildDemoRiskFindings(
  assets: AssetInput[],
  weights: number[],
  metrics: { volatility: number; diversificationScore: number; sharpeRatio: number },
  correlationValues: number[][],
): ApiRiskFinding[] {
  const findings: ApiRiskFinding[] = [];
  const dominantIndex = weights.reduce((maxIndex, weight, index) => (weight > weights[maxIndex] ? index : maxIndex), 0);
  const dominantLabel = assets[dominantIndex].ticker || `Position ${dominantIndex + 1}`;
  if ((weights[dominantIndex] ?? 0) >= 0.3) {
    findings.push({
      type: "concentration",
      severity: weights[dominantIndex] >= 0.45 ? "high" : "medium",
      message: `${dominantLabel} ist mit ${percentFormatter.format(weights[dominantIndex])} die groesste Einzelposition und praegt das Portfolio besonders stark.`,
    });
  }

  const strongestPair = findStrongestCorrelationPair(assets, correlationValues);
  if (strongestPair && strongestPair.value >= 0.75) {
    findings.push({
      type: "correlation",
      severity: "medium",
      message: `${strongestPair.left} und ${strongestPair.right} bewegen sich in der Demo historisch recht aehnlich. Das kann die Diversifikation begrenzen.`,
    });
  }

  if (metrics.diversificationScore < 60) {
    findings.push({
      type: "diversification",
      severity: "medium",
      message: `Der Diversifikationswert liegt bei ${metrics.diversificationScore.toFixed(1)} von 100. Eine breitere Gewichtung wirkt deshalb sinnvoll.`,
    });
  }

  if (metrics.volatility >= 0.24) {
    findings.push({
      type: "volatility",
      severity: metrics.volatility >= 0.32 ? "high" : "medium",
      message: `Die Demo-Volatilitaet von ${formatPercent(metrics.volatility)} zeigt, dass das Portfolio spuerbar schwanken kann.`,
    });
  }

  if (metrics.sharpeRatio < 0.6) {
    findings.push({
      type: "risk_return",
      severity: "low",
      message: "Das Rendite-Risiko-Verhaeltnis ist in der Demo noch ausbaufaehig. Genau hier setzt die optimierte Alternative an.",
    });
  }

  return findings.slice(0, 4);
}

function buildFallbackSectorAllocation(assets: DisplayAsset[], weights: number[]): ApiSectorAllocation[] {
  const grouped = new Map<string, { weight: number; tickers: string[] }>();
  assets.forEach((asset, index) => {
    const sector = asset.sector || "Unbekannt";
    const current = grouped.get(sector) ?? { weight: 0, tickers: [] };
    current.weight += weights[index] ?? 0;
    if (asset.ticker) {
      current.tickers.push(asset.ticker);
    }
    grouped.set(sector, current);
  });

  return Array.from(grouped.entries())
    .map(([sector, value]) => ({
      sector,
      weight: Number(value.weight.toFixed(6)),
      tickers: value.tickers,
    }))
    .sort((left, right) => right.weight - left.weight);
}

function inferFallbackSector(ticker: string, name: string) {
  const normalized = `${ticker} ${name}`.toUpperCase();
  if (normalized.includes("AGG") || normalized.includes("BOND") || normalized.includes("TREASURY")) {
    return "Fixed Income";
  }
  if (normalized.includes("VNQ") || normalized.includes("REAL ESTATE")) {
    return "Real Estate";
  }
  if (normalized.includes("IEFA")) {
    return "International Equities";
  }
  if (normalized.includes("SPY") || normalized.includes("VTI") || normalized.includes("ETF")) {
    return "ETF / Multi-Sektor";
  }
  if (["AAPL", "MSFT", "QQQ", "NVDA"].some((value) => normalized.includes(value))) {
    return "Information Technology";
  }
  if (["GOOG", "GOOGL", "META"].some((value) => normalized.includes(value))) {
    return "Communication Services";
  }
  return "Unbekannt";
}

function inferFallbackInstrumentType(ticker: string, name: string, index: number): "EQUITY" | "ETF" {
  const normalized = `${ticker} ${name}`.toUpperCase();
  if (normalized.includes("ETF") || ["SPY", "AGG", "QQQ", "VTI", "BND", "VNQ", "IEFA", "TLT"].includes(ticker)) {
    return "ETF";
  }
  if (!ticker && index >= 2) {
    return "ETF";
  }
  return "EQUITY";
}

function getCorrelationColor(value: number) {
  if (value < 0) {
    return `rgba(207, 72, 54, ${0.18 + Math.abs(value) * 0.42})`;
  }

  return `rgba(11, 86, 146, ${0.16 + value * 0.56})`;
}

function getFindingTitle(finding: ApiRiskFinding) {
  const titles: Record<ApiRiskFinding["type"], string> = {
    concentration: "Konzentrationsrisiko",
    correlation: "Hohe Korrelation",
    diversification: "Diversifikation",
    volatility: "Volatilitaet",
    risk_return: "Rendite-Risiko-Profil",
  };
  return titles[finding.type];
}

function findStrongestCorrelationPair(assets: AssetInput[], values: number[][]) {
  let strongest: { left: string; right: string; value: number } | null = null;
  for (let rowIndex = 0; rowIndex < assets.length; rowIndex += 1) {
    for (let columnIndex = rowIndex + 1; columnIndex < assets.length; columnIndex += 1) {
      const value = values[rowIndex]?.[columnIndex] ?? 0;
      if (!strongest || value > strongest.value) {
        strongest = {
          left: assets[rowIndex].ticker || `Position ${rowIndex + 1}`,
          right: assets[columnIndex].ticker || `Position ${columnIndex + 1}`,
          value,
        };
      }
    }
  }
  return strongest;
}

function focusAreaLabel(area: FocusArea) {
  return focusAreaOptions.find((option) => option.id === area)?.label ?? area;
}

function goalPresetLabel(goalPreset: GoalPreset) {
  return goalPresetOptions.find((option) => option.id === goalPreset)?.label ?? goalPreset;
}

function profileLabel(profile: InvestorProfile) {
  return `${timeHorizonLabel(profile.timeHorizon)} + ${riskStyleLabel(profile.riskStyle)}`;
}

function profileDescription(profile: InvestorProfile) {
  if (profile.riskStyle === "defensive") {
    return "Die KI priorisiert breite Diversifikation, geringere Konzentration und robustere Branchenverteilung.";
  }
  if (profile.riskStyle === "aggressive") {
    return "Die KI laesst Wachstumsschwerpunkte eher zu, bewertet Konzentrationsrisiken aber weiterhin kritisch.";
  }
  return "Die KI sucht eine nachvollziehbare Balance zwischen Stabilitaet, Branchenbreite und Renditechancen.";
}

function timeHorizonLabel(value: TimeHorizon) {
  const mapping: Record<TimeHorizon, string> = {
    short_term: "kurzfristig",
    mid_term: "mittelfristig",
    long_term: "langfristig",
  };
  return mapping[value];
}

function riskStyleLabel(value: RiskStyle) {
  const mapping: Record<RiskStyle, string> = {
    defensive: "defensiv",
    balanced: "ausgewogen",
    aggressive: "aggressiv",
  };
  return mapping[value];
}

function sentimentLabel(value: RecommendationResult["newsSignals"][number]["sentimentLabel"]) {
  const labels = {
    positive: "positiv",
    neutral: "neutral",
    negative: "kritisch",
    mixed: "gemischt",
  } as const;
  return labels[value];
}

function buildPeriodRange(periodYears: PeriodPreset) {
  const end = new Date();
  const start = addYears(end, -periodYears);
  return {
    startDate: toInputDate(start),
    endDate: toInputDate(end),
  };
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

function formatInstrumentType(type: SecuritySearchResult["type"]) {
  if (type === "ETF") {
    return "ETF";
  }
  return "Aktie";
}

function useDebouncedValue<T>(value: T, delay: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebouncedValue(value), delay);
    return () => window.clearTimeout(timeoutId);
  }, [delay, value]);

  return debouncedValue;
}

export default App;
