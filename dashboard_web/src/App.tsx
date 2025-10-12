import { useEffect, useMemo, useState } from "react";
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  fetchSectorScores,
  fetchStrategies,
  fetchSymbolAnalysis,
  searchSymbols,
} from "./api";
import type {
  AggregatedSignal,
  StrategyInfo,
  StrategyScore,
  SymbolAnalysis,
  SymbolSearchResult,
} from "./types";
import { PriceChart } from "./components/PriceChart";
import { StrategyCard } from "./components/StrategyCard";
import { AggregatedSignals } from "./components/AggregatedSignals";
import { ScenarioCallouts } from "./components/ScenarioCallouts";
import { FinalScoreChart } from "./components/FinalScoreChart";
import { SignalComparisonPanel } from "./components/SignalComparisonPanel";
import { FundamentalsCard } from "./components/FundamentalsCard";
import { SearchPage } from "./pages/SearchPage";
import { WatchlistPage } from "./pages/WatchlistPage";
import { SignalGuide } from "./pages/SignalGuide";
import { GlossaryPage } from "./pages/GlossaryPage";
import { StrategyWeightsPage } from "./pages/StrategyWeightsPage";
import { RussellMomentumPage } from "./pages/RussellMomentumPage";
import { SPMomentumPage } from "./pages/SPMomentumPage";
import { useWatchlist, WATCHLIST_STATUSES } from "./hooks/useWatchlist";
import type { SavedSignal, WatchlistStatus } from "./hooks/useWatchlist";
import { useStrategyMetrics } from "./hooks/useStrategyMetrics";
import { Tooltip, InfoIcon } from "./components/Tooltip";

const THREE_YEARS_AGO = new Date();
THREE_YEARS_AGO.setDate(THREE_YEARS_AGO.getDate() - 365 * 3);

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatMultiplier(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "x1.00";
  return `x${value.toFixed(2)}`;
}

type MetricDescriptor = {
  label: string;
  ideal: string;
  compare: (n: number) => string;
  format?: (n: number) => string;
  chipClass?: string;
  chipLabel?: string;
};

const MACRO_DESCRIPTORS: Record<string, MetricDescriptor> = {
  vix: {
    label: "VIX level",
    ideal: "Below 20 (calm volatility)",
    format: (v) => v.toFixed(2),
    compare: (v) => {
      if (v < 18) return "Volatility backdrop is calm.";
      if (v < 25) return "Volatility is elevated but manageable.";
      return "Volatility stress detected.";
    },
  },
  vix_score: {
    label: "VIX score",
    ideal: "Above 0.60",
    format: (v) => formatPercent(v, 0),
    compare: (v) => {
      if (v >= 0.7) return "Volatility supports risk-taking.";
      if (v >= 0.5) return "Volatility readings are neutral.";
      return "Volatility signals caution.";
    },
  },
  credit_ratio: {
    label: "HYG/LQD ratio",
    ideal: "Above 0.97",
    format: (v) => v.toFixed(3),
    compare: (v) => {
      if (v >= 0.98) return "Credit markets signal confidence.";
      if (v >= 0.95) return "Credit tone is neutral.";
      return "Credit markets defensive; monitor spreads.";
    },
  },
  credit_score: {
    label: "Credit score",
    ideal: "Above 0.60",
    format: (v) => formatPercent(v, 0),
    compare: (v) => {
      if (v >= 0.7) return "Supportive credit momentum.";
      if (v >= 0.5) return "Mixed credit signals.";
      return "Credit stress building; reduce risk.";
    },
  },
  spy_20d_return: {
    label: "SPY 20D return",
    ideal: "Positive momentum",
    format: (v) => formatPercent(v, 1),
    compare: (v) => {
      if (v >= 0.05) return "Equity momentum is strong.";
      if (v >= 0) return "Trend is modestly positive.";
      return "Equity trend is negative.";
    },
  },
  trend_score: {
    label: "Trend score",
    ideal: "Above 0.55",
    format: (v) => formatPercent(v, 0),
    compare: (v) => {
      if (v >= 0.65) return "Trend regime is risk-on.";
      if (v >= 0.5) return "Trend regime is balanced.";
      return "Trend regime defensive.";
    },
  },
};

const DEFAULT_MACRO_DESCRIPTOR: MetricDescriptor = {
  label: "Metric",
  ideal: "Monitor for context",
  compare: () => "No benchmark available.",
  format: (v) => v.toFixed(3),
};

const EARNINGS_DESCRIPTORS: Record<string, MetricDescriptor> = {
  score: {
    label: "Composite score",
    ideal: ">= 0.70",
    format: (v) => formatPercent(v, 0),
    compare: (v) =>
      v >= 0.7 ? "Earnings momentum is strong." : v >= 0.5 ? "Earnings momentum is mixed." : "Earnings momentum is weak.",
    chipClass: "rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700",
    chipLabel: "Score",
  },
  multiplier: {
    label: "Confidence multiplier",
    ideal: ">= x0.90",
    format: (v) => formatMultiplier(v),
    compare: (v) =>
      v >= 0.9 ? "Earnings outlook boosts signals." : v >= 0.8 ? "Earnings outlook is neutral." : "Earnings outlook dilutes conviction.",
    chipClass: "rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700",
    chipLabel: "Multiplier",
  },
  positive_ratio: {
    label: "Beat ratio",
    ideal: ">= 60% beats",
    format: (v) => formatPercent(v, 0),
    compare: (v) =>
      v >= 0.65 ? "Companies consistently beating estimates." : v >= 0.5 ? "Beat rate acceptable." : "Beat rate is soft.",
    chipClass: "rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-600",
    chipLabel: "Beats",
  },
  surprise_average: {
    label: "Average surprise",
    ideal: ">= +5%",
    format: (v) => formatPercent(v, 1),
    compare: (v) =>
      v >= 0.05 ? "Upside surprises support momentum." : v >= 0 ? "Surprise trend is steady." : "Negative surprises drag momentum.",
    chipClass: "rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-600",
    chipLabel: "Avg surprise",
  },
  eps_trend: {
    label: "EPS trend",
    ideal: "Positive QoQ",
    format: (v) => formatPercent(v, 1),
    compare: (v) =>
      v >= 0.05 ? "EPS growth is accelerating." : v >= 0 ? "EPS trend is stable." : "EPS trend is declining.",
    chipClass: "rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-600",
    chipLabel: "EPS trend",
  },
};

const DEFAULT_EARNINGS_DESCRIPTOR: MetricDescriptor = {
  label: "Metric",
  ideal: "Refer to context",
  compare: () => "No benchmark available.",
  format: (v) => v.toFixed(3),
  chipClass: "rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-medium text-slate-700",
  chipLabel: "Metric",
};
function getMacroDescriptor(key: string): MetricDescriptor {
  return MACRO_DESCRIPTORS[key] ?? {
    ...DEFAULT_MACRO_DESCRIPTOR,
    label: key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()),
  };
}

function getEarningsDescriptor(key: string): MetricDescriptor {
  return EARNINGS_DESCRIPTORS[key] ?? {
    ...DEFAULT_EARNINGS_DESCRIPTOR,
    label: key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()),
  };
}

function extractAnnotations(strategies: SymbolAnalysis["strategies"] | undefined) {
  const annotations: {
    breakout?: number | null;
    handleHigh?: number | null;
    atrStop?: number | null;
  } = {};

  if (!strategies) return annotations;

  const danZanger = strategies.find((strategy) => strategy.name === "dan_zanger_cup_handle");
  if (danZanger?.latest_metadata) {
    annotations.breakout =
      typeof danZanger.latest_metadata.breakout_price === "number" ? danZanger.latest_metadata.breakout_price : null;
    annotations.handleHigh =
      typeof danZanger.latest_metadata.right_peak === "number" ? danZanger.latest_metadata.right_peak : null;
  }

  const trend = strategies.find((strategy) => strategy.name === "trend_following");
  if (trend?.extras?.latest_stop_price) {
    annotations.atrStop = typeof trend.extras.latest_stop_price === "number" ? trend.extras.latest_stop_price : null;
  }

  return annotations;
}
type SavePayload = {
  symbol: string;
  status: WatchlistStatus;
  finalScores: StrategyScore[];
  averageScore: number;
  aggregatedSignal?: AggregatedSignal | null;
};

type SymbolDashboardProps = {
  strategiesMeta: StrategyInfo[];
  onSave: (payload: SavePayload) => void;
  watchlistItems: SavedSignal[];
  strategyWeights: Record<string, number>;
};
function SymbolDashboardPage({
  strategiesMeta,
  onSave,
  watchlistItems,
  strategyWeights,
}: SymbolDashboardProps) {
  const { symbol: symbolParam } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const symbol = symbolParam?.toUpperCase() ?? null;

  const [analysis, setAnalysis] = useState<SymbolAnalysis | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sectorScores, setSectorScores] = useState<Record<string, { average: number; sampleSize: number }> | null>(null);
  const [sectorContext, setSectorContext] = useState<{ sector?: string | null; sampleSize: number; universe?: string | null } | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<WatchlistStatus>(WATCHLIST_STATUSES[0]);
  const [symbolMeta, setSymbolMeta] = useState<SymbolSearchResult | null>(null);

  const [comparisonAnalyses, setComparisonAnalyses] = useState<Record<string, SymbolAnalysis>>({});
  const [comparisonInputs, setComparisonInputs] = useState<{ primary: string; secondary: string }>({ primary: symbol ?? "", secondary: "" });
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [activeComparison, setActiveComparison] = useState<{ primary: string; secondary: string } | null>(null);

  useEffect(() => {
    if (!symbol) {
      setAnalysis(null);
      setSectorScores(null);
      setSectorContext(null);
      return;
    }
    const existing = watchlistItems.find((item) => item.symbol.toUpperCase() === symbol);
    setSelectedStatus(existing?.status ?? WATCHLIST_STATUSES[0]);
  }, [symbol, watchlistItems]);

  useEffect(() => {
    if (!symbol) return;
    setLoadingAnalysis(true);
    setError(null);
    fetchSymbolAnalysis({
      symbol,
      start: formatDate(THREE_YEARS_AGO),
      end: formatDate(new Date()),
      interval: "1d",
    })
      .then((data) => setAnalysis(data))
      .catch((err) => {
        setError((err as Error).message);
        setAnalysis(null);
      })
      .finally(() => setLoadingAnalysis(false));
  }, [symbol]);

  useEffect(() => {
    if (!symbol) {
      setSectorScores(null);
      setSectorContext(null);
      return;
    }
    fetchSectorScores(symbol)
      .then((response) => {
        const scores: Record<string, { average: number; sampleSize: number }> = {};
        response.strategy_scores.forEach((entry) => {
          scores[entry.strategy] = { average: entry.average_score, sampleSize: entry.sample_size };
        });
        setSectorScores(scores);
        setSectorContext({ sector: response.sector, sampleSize: response.sample_size, universe: response.universe ?? null });
      })
      .catch(() => {
        setSectorScores(null);
        setSectorContext(null);
      });
  }, [symbol]);

  useEffect(() => {
    if (!symbol) return;
    setComparisonInputs((prev) => ({ ...prev, primary: symbol }));
    setComparisonAnalyses({});
    setComparisonError(null);
    setActiveComparison(null);
  }, [symbol]);

  useEffect(() => {
    const state = location.state as { status?: WatchlistStatus } | undefined;
    if (state?.status && symbol) setSelectedStatus(state.status);
    if (state) navigate(location.pathname, { replace: true, state: undefined });
  }, [location, navigate, symbol]);

  useEffect(() => {
    if (!symbol) {
      setSymbolMeta(null);
      return;
    }
    searchSymbols(symbol)
      .then((matches) => {
        const direct = matches.find((item) => item.symbol.toUpperCase() === symbol);
        if (direct) setSymbolMeta(direct);
      })
      .catch(() => undefined);
  }, [symbol]);
  const aggregatedSignals = analysis?.aggregated_signals ?? [];
  const annotations = useMemo(() => extractAnnotations(analysis?.strategies), [analysis?.strategies]);
  const strategyCards = useMemo(() => analysis?.strategies ?? [], [analysis]);
  const macroOverlay = analysis?.macro_overlay ?? null;
  const macroFactorEntries = macroOverlay ? Object.entries(macroOverlay.factors ?? {}) : [];
  const earningsQuality = analysis?.earnings_quality ?? null;
  const fundamentalsSnapshot = analysis?.fundamentals ?? null;

  const finalScores: StrategyScore[] = useMemo(() => {
    if (!strategyCards.length) return [];
    return strategyCards.map((strategy) => {
      const latest = strategy.signals.at(-1);
      const raw = typeof latest?.confidence === "number" ? latest.confidence : 0;
      const clamped = Math.max(0, Math.min(raw, 1));
      return {
        name: strategy.name,
        label: strategy.label,
        value: clamped * 100,
      };
    });
  }, [strategyCards]);

  const averageScore = useMemo(() => {
    if (finalScores.length === 0) return 0;
    const weightedSum = finalScores.reduce((sum, entry) => {
      const weight = strategyWeights[entry.name] ?? 0;
      return sum + entry.value * weight;
    }, 0);
    const totalWeight = finalScores.reduce((sum, entry) => sum + (strategyWeights[entry.name] ?? 0), 0);
    if (totalWeight > 0) return weightedSum / totalWeight;
    return finalScores.reduce((sum, entry) => sum + entry.value, 0) / finalScores.length;
  }, [finalScores, strategyWeights]);

  const latestAggregated = aggregatedSignals.at(-1) ?? null;

  const handleSave = (statusOverride?: WatchlistStatus) => {
    if (!symbol || !analysis || finalScores.length === 0) return;
    onSave({
      symbol,
      status: statusOverride ?? selectedStatus,
      finalScores,
      averageScore,
      aggregatedSignal: aggregatedSignals.at(-1) ?? null,
    });
  };

  const fetchComparisonAnalysis = useMemo(
    () =>
      async (target: string) => {
        const key = target.toUpperCase();
        if (analysis && key === symbol) {
          setComparisonAnalyses((prev) => ({ ...prev, [key]: analysis }));
          return analysis;
        }
        const cached = comparisonAnalyses[key];
        if (cached) return cached;
        const data = await fetchSymbolAnalysis({
          symbol: key,
          start: formatDate(THREE_YEARS_AGO),
          end: formatDate(new Date()),
          interval: "1d",
        });
        setComparisonAnalyses((prev) => ({ ...prev, [key]: data }));
        return data;
      },
    [analysis, comparisonAnalyses, symbol],
  );

  const comparisonRows = useMemo(() => {
    if (!activeComparison) return [];
    const primary =
      comparisonAnalyses[activeComparison.primary.toUpperCase()] ??
      (symbol === activeComparison.primary.toUpperCase() ? analysis ?? undefined : undefined);
    const secondary =
      comparisonAnalyses[activeComparison.secondary.toUpperCase()] ??
      (symbol === activeComparison.secondary.toUpperCase() ? analysis ?? undefined : undefined);
    if (!primary || !secondary) return [];

    return strategiesMeta.map((meta) => {
      const scoreFor = (payload: SymbolAnalysis) => {
        const strat = payload.strategies.find((item) => item.name === meta.name);
        if (!strat) return null;
        const latest = strat.signals.at(-1);
        if (!latest || typeof latest.confidence !== "number") return null;
        return Math.max(0, Math.min(latest.confidence, 1)) * 100;
      };
      const primaryScore = scoreFor(primary);
      const secondaryScore = scoreFor(secondary);
      const difference =
        primaryScore !== null && secondaryScore !== null ? primaryScore - secondaryScore : null;
      return {
        strategy: meta.name,
        label: meta.label,
        primaryScore,
        secondaryScore,
        difference,
      };
    });
  }, [activeComparison, analysis, comparisonAnalyses, strategiesMeta, symbol]);

  const comparisonSummary = useMemo(() => {
    if (!activeComparison) return null;
    const take = (payload: SymbolAnalysis | undefined) => {
      const latest = payload?.aggregated_signals.at(-1);
      if (!latest || typeof latest.confidence !== "number") return null;
      return Math.max(0, Math.min(latest.confidence, 1)) * 100;
    };
    const primary =
      take(
        comparisonAnalyses[activeComparison.primary.toUpperCase()] ??
        (symbol === activeComparison.primary.toUpperCase() ? analysis ?? undefined : undefined),
      );
    const secondary =
      take(
        comparisonAnalyses[activeComparison.secondary.toUpperCase()] ??
        (symbol === activeComparison.secondary.toUpperCase() ? analysis ?? undefined : undefined),
      );
    return { primaryScore: primary, secondaryScore: secondary };
  }, [activeComparison, analysis, comparisonAnalyses, symbol]);

  const handleCompare = async () => {
    const primary = comparisonInputs.primary.trim().toUpperCase();
    const secondary = comparisonInputs.secondary.trim().toUpperCase();
    if (!primary || !secondary) {
      setComparisonError("Enter two symbols to compare.");
      return;
    }
    if (primary === secondary) {
      setComparisonError("Choose two different symbols to compare.");
      return;
    }
    setLoadingComparison(true);
    setComparisonError(null);
    try {
      await Promise.all([fetchComparisonAnalysis(primary), fetchComparisonAnalysis(secondary)]);
      setActiveComparison({ primary, secondary });
    } catch (err) {
      setComparisonError(err instanceof Error ? err.message : "Unable to run comparison.");
    } finally {
      setLoadingComparison(false);
    }
  };

  const handleComparisonChange = (field: "primary" | "secondary", value: string) => {
    setComparisonInputs((prev) => ({ ...prev, [field]: value.toUpperCase() }));
    setComparisonError(null);
  };

  const handleSwapComparison = () => {
    setComparisonInputs((prev) => ({ primary: prev.secondary, secondary: prev.primary }));
    setComparisonError(null);
  };

  const symbolLabel = symbolMeta?.symbol ?? symbol ?? "";
  const symbolName =
    symbolMeta && symbolMeta.name && symbolMeta.name.toUpperCase() !== symbolMeta.symbol.toUpperCase()
      ? symbolMeta.name
      : null;
  return (
    <div className="mx-auto w-full max-w-7xl space-y-8 px-6 pb-16 pt-10">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-semibold text-slate-900">{symbolLabel}</h1>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-500 transition hover:border-blue-300 hover:text-blue-600"
            >
              Back to search
            </button>
          </div>
          {symbolName ? <p className="text-xs text-slate-500">{symbolName}</p> : null}
          {sectorContext ? (
            <p className="mt-1 text-xs text-slate-500">
              Sector snapshot: {sectorContext.sector ?? "Unknown"} -{" "}
              {sectorContext.universe === "russell"
                ? "Small-cap (Russell 2000)"
                : sectorContext.universe === "sp500"
                  ? "Large-cap (S&P 500)"
                  : "Tracked universe"}{" "}
              ({sectorContext.sampleSize} symbols)
            </p>
          ) : (
            <p className="mt-1 text-xs text-slate-500">Sector snapshot unavailable.</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-4 py-1 text-xs font-semibold uppercase tracking-widest text-slate-600">
            {sectorContext?.universe === "sp500" ? "Large Cap" : "Small Cap"}
          </span>
          <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-4 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            Strategies: {strategiesMeta.length}
          </span>
        </div>
      </header>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-4 text-sm text-rose-700 shadow-sm shadow-rose-200/40">
          <strong className="font-semibold">Analysis error:</strong> {error}
        </div>
      ) : null}

      {loadingAnalysis && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50 px-6 py-5 text-sm text-blue-700 shadow-sm shadow-blue-200/40">
          Fetching the latest prices, fundamentals, and strategy signals...
        </div>
      )}

      {!loadingAnalysis && !analysis ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500 shadow-sm shadow-slate-200/60">
          Unable to load analysis for this symbol. Try again from the search page.
        </div>
      ) : null}

      {analysis ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr),minmax(0,1fr)]">
          <div className="space-y-6">
            <SignalCarousel
              finalScores={finalScores}
              averageScore={averageScore}
              aggregatedSignals={aggregatedSignals}
              latestAggregated={latestAggregated ?? null}
              strategyCards={strategyCards}
              sectorScores={sectorScores}
            />

            <div className="grid gap-6 lg:grid-cols-2">
              <FundamentalsCard fundamentals={fundamentalsSnapshot} />
              <MacroEarningsCard
                macroOverlay={macroOverlay}
                macroFactorEntries={macroFactorEntries}
                earningsQuality={earningsQuality}
              />
            </div>

            <ScenarioCallouts aggregatedSignals={aggregatedSignals} strategies={strategyCards} />
            <PriceChart data={analysis.price_bars} annotations={annotations} latestAggregated={latestAggregated} />

            <SignalComparisonPanel
              inputs={comparisonInputs}
              onInputChange={handleComparisonChange}
              onSwap={handleSwapComparison}
              onCompare={handleCompare}
              loading={loadingComparison}
              error={comparisonError}
              rows={comparisonRows}
              summary={comparisonSummary}
              activePair={activeComparison}
              strategyOrder={strategiesMeta}
            />
          </div>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
              <h3 className="text-sm font-semibold text-slate-900">Save to watchlist</h3>
              <p className="mt-2 text-xs text-slate-500">
                Capture this signal snapshot for future review and watchlist alerts.
              </p>
              <div className="mt-4 space-y-3">
                <select
                  value={selectedStatus}
                  onChange={(event) => setSelectedStatus(event.target.value as WatchlistStatus)}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm shadow-inner shadow-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
                >
                  {WATCHLIST_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => handleSave()}
                  disabled={finalScores.length === 0}
                  className="inline-flex w-full items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Save symbol snapshot
                </button>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm shadow-slate-200/60">
              <h3 className="text-sm font-semibold text-slate-900">Next steps</h3>
              <ul className="mt-3 space-y-2 text-xs">
                <li>Review scenario callouts for tactical actions aligned with the latest signal.</li>
                <li>Use the comparison tool to benchmark this ticker against a peer.</li>
                <li>Jump back to the search page to explore additional prospects.</li>
              </ul>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
type MacroEarningsCardProps = {
  macroOverlay: SymbolAnalysis["macro_overlay"] | null | undefined;
  macroFactorEntries: Array<[string, number]>;
  earningsQuality: SymbolAnalysis["earnings_quality"] | null | undefined;
};

function MacroEarningsCard({
  macroOverlay,
  macroFactorEntries,
  earningsQuality,
}: MacroEarningsCardProps) {
  const earningsMetrics = useMemo(
    () =>
      earningsQuality
        ? [
          { key: "score", value: earningsQuality.score ?? null },
          { key: "multiplier", value: earningsQuality.multiplier ?? null },
          { key: "positive_ratio", value: earningsQuality.positive_ratio ?? null },
          { key: "surprise_average", value: earningsQuality.surprise_average ?? null },
          { key: "eps_trend", value: earningsQuality.eps_trend ?? null },
        ]
        : [],
    [earningsQuality],
  );

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <h3 className="text-sm font-semibold text-slate-900">Macro & Earnings Context</h3>
      {macroOverlay ? (
        <div className="space-y-2 text-xs text-slate-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-700">Macro regime</p>
              <p className="text-[11px] text-slate-500">{macroOverlay.notes ?? "Macro overlay score derived from VIX, credit spreads, and SPY trend."}</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold text-slate-900">{macroOverlay.regime.replace(/_/g, " ")}</p>
              <p className="text-xs text-slate-500">
                Score {formatPercent(macroOverlay.score, 0)} - {formatMultiplier(macroOverlay.multiplier)}
              </p>
            </div>
          </div>
          {macroFactorEntries.length ? (
            <ul className="mt-2 grid gap-2 sm:grid-cols-2">
              {macroFactorEntries.map(([name, rawValue]) => {
                const descriptor = getMacroDescriptor(name);
                const numericValue = typeof rawValue === "number" && Number.isFinite(rawValue) ? rawValue : null;
                const display =
                  numericValue !== null
                    ? descriptor.format
                      ? descriptor.format(numericValue)
                      : numericValue.toFixed(3)
                    : "--";
                const tooltipContent = (
                  <div className="space-y-1 text-left">
                    <p className="text-xs font-semibold text-slate-100">{descriptor.label}</p>
                    <p className="text-[11px] text-slate-300">Ideal: {descriptor.ideal}</p>
                    <p className="text-[11px] text-slate-300">
                      {numericValue !== null ? descriptor.compare(numericValue) : "No recent readings."}
                    </p>
                  </div>
                );
                return (
                  <li key={name} className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/70 px-2 py-2">
                    <div className="flex items-center gap-1 text-xs font-medium text-slate-500">
                      <span className="uppercase tracking-wide text-slate-400">{descriptor.label}</span>
                      <Tooltip content={tooltipContent}>
                        <button
                          type="button"
                          className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-400 transition hover:text-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400/40"
                          aria-label={`More information about ${descriptor.label}`}
                        >
                          <InfoIcon />
                        </button>
                      </Tooltip>
                    </div>
                    <span className="text-sm font-semibold text-slate-800">{display}</span>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      ) : (
        <p className="text-xs text-slate-500">Macro overlay unavailable.</p>
      )}

      {earningsMetrics.length ? (
        <div className="border-t border-slate-100 pt-3 text-xs text-slate-600">
          <p className="font-semibold text-slate-700">Earnings quality</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {earningsMetrics.map(({ key, value }) => {
              const descriptor = getEarningsDescriptor(key);
              const numericValue = typeof value === "number" && Number.isFinite(value) ? value : null;
              const display =
                numericValue !== null
                  ? descriptor.format
                    ? descriptor.format(numericValue)
                    : numericValue.toFixed(3)
                  : "--";
              const tooltipContent = (
                <div className="space-y-1 text-left">
                  <p className="text-xs font-semibold text-slate-100">{descriptor.label}</p>
                  <p className="text-[11px] text-slate-300">Ideal: {descriptor.ideal}</p>
                  <p className="text-[11px] text-slate-300">
                    {numericValue !== null ? descriptor.compare(numericValue) : "No recent readings."}
                  </p>
                </div>
              );
              return (
                <Tooltip key={key} content={tooltipContent}>
                  <span className={descriptor.chipClass ?? DEFAULT_EARNINGS_DESCRIPTOR.chipClass ?? ""}>
                    {(descriptor.chipLabel ?? descriptor.label) + ": " + display}
                  </span>
                </Tooltip>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="text-xs text-slate-500">No earnings quality metrics available.</p>
      )}
    </article>
  );
}

type SignalCarouselProps = {
  finalScores: StrategyScore[];
  averageScore: number;
  aggregatedSignals: AggregatedSignal[];
  latestAggregated: AggregatedSignal | null;
  strategyCards: StrategyAnalysis[];
  sectorScores: Record<string, { average: number; sampleSize: number }> | null;
};

function SignalCarousel({
  finalScores,
  averageScore,
  aggregatedSignals,
  latestAggregated,
  strategyCards,
  sectorScores,
}: SignalCarouselProps) {
  const [index, setIndex] = useState(0);

  const slides = useMemo(() => {
    const overviewSlide = {
      key: "overview",
      title: "Signal overview",
      description:
        "Composite confidence + aggregated signals across strategies.",
      meta: (
        <div className="text-right">
          <span className="text-xs uppercase tracking-wide text-slate-400">Latest aggregated</span>
          <p className="text-xl font-semibold text-slate-900">
            {latestAggregated ? formatPercent(Math.max(0, Math.min(latestAggregated.confidence, 1)), 0) : "--"}
          </p>
        </div>
      ),
      content: (
        <div className="grid h-full gap-4 md:grid-cols-[1.4fr,1fr]">
          <FinalScoreChart scores={finalScores} average={averageScore} />
          <AggregatedSignals signals={aggregatedSignals} />
        </div>
      ),
    };

    const result = [overviewSlide];

    if (strategyCards.length > 0) {
      result.push({
        key: "strategies",
        title: "Strategy breakdown",
        description: "Review per-strategy signals in one place to compare confidence, setups, and sector context.",
        meta: null,
        content: (
          <div className="grid h-full gap-4 md:grid-cols-2">
            {strategyCards.map((strategy) => (
              <StrategyCard
                key={strategy.name}
                strategy={strategy}
                sectorScore={sectorScores?.[strategy.name] ?? null}
              />
            ))}
          </div>
        ),
      });
    }

    return result;
  }, [aggregatedSignals, averageScore, finalScores, latestAggregated, sectorScores, strategyCards]);

  useEffect(() => {
    if (index >= slides.length) {
      setIndex(Math.max(slides.length - 1, 0));
    }
  }, [index, slides.length]);

  const activeSlide = slides[index] ?? slides[0];

  const handlePrevious = () => {
    if (slides.length <= 1) return;
    setIndex((prev) => (prev - 1 + slides.length) % slides.length);
  };

  const handleNext = () => {
    if (slides.length <= 1) return;
    setIndex((prev) => (prev + 1) % slides.length);
  };

  return (
    <section className="flex min-h-[320px] flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/60 sm:p-6 md:min-h-[360px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{activeSlide.title}</h2>
          <p className="text-xs text-slate-500">{activeSlide.description}</p>
        </div>
        <div className="flex items-start gap-3">
          {activeSlide.meta}
          {slides.length > 1 ? (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handlePrevious}
                aria-label="Previous slide"
                className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:border-blue-300 hover:text-blue-600 disabled:opacity-40"
                disabled={slides.length <= 1}
              >
                <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-4 w-4">
                  <path
                    d="M9.5 4.5 6 8l3.5 3.5"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <button
                type="button"
                onClick={handleNext}
                aria-label="Next slide"
                className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:border-blue-300 hover:text-blue-600 disabled:opacity-40"
                disabled={slides.length <= 1}
              >
                <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-4 w-4">
                  <path
                    d="M6.5 4.5 10 8l-3.5 3.5"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex-1">{activeSlide.content}</div>

      {slides.length > 1 ? (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <div className="flex items-center gap-1">
            {slides.map((slide, slideIndex) => (
              <span
                key={slide.key}
                className={`h-2 w-2 rounded-full transition ${slideIndex === index ? "bg-blue-500" : "bg-slate-300"
                  }`}
              />
            ))}
          </div>
          <span className="text-xs font-semibold text-slate-500">
            {index + 1} / {slides.length}
          </span>
        </div>
      ) : null}
    </section>
  );
}

const navLinks = [
  { label: "Search", to: "/" },
  { label: "Watchlist", to: "/watchlist" },
  { label: "Russell Momentum", to: "/russell/momentum" },
  { label: "S&P Momentum", to: "/sp500/momentum" },
  { label: "Signal Guides", to: "/guides/signals" },
  { label: "Glossary", to: "/guides/glossary" },
  { label: "Strategy Health", to: "/diagnostics/strategy-weights" },
];

type AppLayoutProps = {
  strategies: StrategyInfo[];
  watchlistItems: SavedSignal[];
  handleSaveWatchlist: (payload: SavePayload) => void;
  handleQuickWatchlist: (symbol: string, status: WatchlistStatus) => Promise<unknown>;
  removeFromWatchlist: (id: string) => Promise<void>;
  strategyWeights: Record<string, number>;
};

function AppLayout({
  strategies,
  watchlistItems,
  handleSaveWatchlist,
  handleQuickWatchlist,
  removeFromWatchlist,
  strategyWeights,
}: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-slate-900 text-white">
        <div className="mx-auto flex flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Small-Cap Growth Toolkit</h1>
            <p className="text-xs text-slate-300">
              Search, analyse, and monitor actionable signals across CAN SLIM, Zanger, trend-following, and Livermore models.
            </p>
          </div>
          <nav className="flex w-full flex-row flex-wrap gap-2 overflow-x-auto text-sm font-medium sm:w-auto">
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  `rounded-full px-4 py-2 transition focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900 ${isActive ? "bg-white text-slate-900 shadow" : "bg-slate-800/60 text-slate-200 hover:bg-slate-700/80"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <Routes>
        <Route path="/" element={<SearchPage watchlistItems={watchlistItems} />} />
        <Route
          path="/symbols/:symbol"
          element={
            <SymbolDashboardPage
              strategiesMeta={strategies}
              onSave={handleSaveWatchlist}
              watchlistItems={watchlistItems}
              strategyWeights={strategyWeights}
            />
          }
        />
        <Route
          path="/russell/momentum"
          element={
            <RussellMomentumPage
              watchlistItems={watchlistItems}
              onSaveWatchlist={handleQuickWatchlist}
            />
          }
        />
        <Route
          path="/sp500/momentum"
          element={
            <SPMomentumPage
              watchlistItems={watchlistItems}
              onSaveWatchlist={handleQuickWatchlist}
            />
          }
        />
        <Route path="/watchlist" element={<WatchlistPage items={watchlistItems} remove={removeFromWatchlist} />} />
        <Route path="/guides/signals" element={<SignalGuide />} />
        <Route path="/guides/glossary" element={<GlossaryPage />} />
        <Route path="/diagnostics/strategy-weights" element={<StrategyWeightsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </div>
  );
}

function NotFoundPage() {
  return (
    <div className="mx-auto flex min-h-[50vh] w-full max-w-2xl flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-3xl font-semibold text-slate-900">Page not found</h1>
      <p className="text-sm text-slate-500">
        The page you were looking for does not exist. Use the navigation above to return to search or browse guides.
      </p>
      <NavLink
        to="/"
        className="inline-flex items-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20"
      >
        Back to search
      </NavLink>
    </div>
  );
}

export default function App() {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const { items: watchlistItems, save: persistWatchlist, remove } = useWatchlist();
  const { metrics: strategyMetrics } = useStrategyMetrics(false);

  const strategyWeights = useMemo(() => {
    const latest = new Map<string, { weight: number; updatedAt: number }>();
    strategyMetrics.forEach((entry) => {
      if (entry.reliability_weight === null || entry.reliability_weight === undefined) return;
      const updatedAt = new Date(entry.updated_at).getTime();
      if (Number.isNaN(updatedAt)) return;
      const existing = latest.get(entry.strategy.id);
      if (!existing || updatedAt > existing.updatedAt) {
        latest.set(entry.strategy.id, { weight: entry.reliability_weight, updatedAt });
      }
    });
    const result: Record<string, number> = {};
    latest.forEach((value, key) => {
      result[key] = value.weight;
    });
    return result;
  }, [strategyMetrics]);

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch((err) => console.error(err));
  }, []);

  const handleSaveWatchlist = ({ symbol, status, finalScores, averageScore, aggregatedSignal }: SavePayload) => {
    void persistWatchlist({
      symbol: symbol.toUpperCase(),
      status,
      final_scores: finalScores,
      average_score: averageScore,
      aggregated_signal: aggregatedSignal ?? null,
    });
  };

  const handleQuickWatchlist = (symbol: string, status: WatchlistStatus) =>
    persistWatchlist({
      symbol: symbol.toUpperCase(),
      status,
      final_scores: [],
      average_score: 0,
      aggregated_signal: null,
    });

  return (
    <BrowserRouter>
      <AppLayout
        strategies={strategies}
        watchlistItems={watchlistItems}
        handleSaveWatchlist={handleSaveWatchlist}
        handleQuickWatchlist={handleQuickWatchlist}
        removeFromWatchlist={remove}
        strategyWeights={strategyWeights}
      />
    </BrowserRouter>
  );
}
