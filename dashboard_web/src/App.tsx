import { useEffect, useMemo, useState } from "react";
import { BrowserRouter, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { fetchStrategies, fetchSymbolAnalysis, searchSymbols } from "./api";
import type { AggregatedSignal, StrategyInfo, StrategyScore, SymbolAnalysis, SymbolSearchResult } from "./types";
import { SearchPanel } from "./components/SearchPanel";
import { PriceChart } from "./components/PriceChart";
import { StrategyCard } from "./components/StrategyCard";
import { AggregatedSignals } from "./components/AggregatedSignals";
import { ScenarioCallouts } from "./components/ScenarioCallouts";
import { FinalScoreChart } from "./components/FinalScoreChart";
import { WatchlistPage } from "./pages/WatchlistPage";
import { SignalGuide } from "./pages/SignalGuide";
import { GlossaryPage } from "./pages/GlossaryPage";
import { StrategyWeightsPage } from "./pages/StrategyWeightsPage";
import { useWatchlist, WATCHLIST_STATUSES } from "./hooks/useWatchlist";
import type { SavedSignal, WatchlistStatus } from "./hooks/useWatchlist";
import { useStrategyMetrics } from "./hooks/useStrategyMetrics";

const THREE_YEARS_AGO = new Date();
THREE_YEARS_AGO.setDate(THREE_YEARS_AGO.getDate() - 365 * 3);

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
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
    annotations.breakout = typeof danZanger.latest_metadata.breakout_price === "number" ? danZanger.latest_metadata.breakout_price : null;
    annotations.handleHigh = typeof danZanger.latest_metadata.right_peak === "number" ? danZanger.latest_metadata.right_peak : null;
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

function DashboardPage({
  strategiesMeta,
  onSave,
  watchlistItems,
  strategyWeights,
}: {
  strategiesMeta: StrategyInfo[];
  onSave: (payload: SavePayload) => Promise<void> | void;
  watchlistItems: SavedSignal[];
  strategyWeights: Record<string, number>;
}) {
  const location = useLocation();
  const navigate = useNavigate();

  const [searchResults, setSearchResults] = useState<SymbolSearchResult[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<SymbolSearchResult | null>(null);
  const [analysis, setAnalysis] = useState<SymbolAnalysis | null>(null);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<WatchlistStatus>(WATCHLIST_STATUSES[0]);
  const [pendingAutoSave, setPendingAutoSave] = useState<WatchlistStatus | null>(null);

  const aggregatedSignals: AggregatedSignal[] = analysis?.aggregated_signals ?? [];
  const annotations = useMemo(() => extractAnnotations(analysis?.strategies), [analysis?.strategies]);
  const strategyCards = useMemo(() => analysis?.strategies ?? [], [analysis]);
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
    if (finalScores.length === 0) {
      return 0;
    }
    const weightedSum = finalScores.reduce((sum, entry) => {
      const weight = strategyWeights[entry.name] ?? 0;
      return sum + entry.value * weight;
    }, 0);
    const totalWeight = finalScores.reduce((sum, entry) => sum + (strategyWeights[entry.name] ?? 0), 0);
    if (totalWeight > 0) {
      return weightedSum / totalWeight;
    }
    return finalScores.reduce((sum, entry) => sum + entry.value, 0) / finalScores.length;
  }, [finalScores, strategyWeights]);
  const latestAggregated = aggregatedSignals.at(-1) ?? null;

  useEffect(() => {
    const state = (location.state as { symbol?: string; status?: WatchlistStatus } | undefined) || {};
    if (state.symbol) {
      const symbol = state.symbol.toUpperCase();
      const existing = watchlistItems.find((item) => item.symbol.toUpperCase() === symbol);
      setSelectedStatus(existing?.status ?? WATCHLIST_STATUSES[0]);
      setPendingAutoSave(existing?.status ?? WATCHLIST_STATUSES[0]);
      setSelectedSymbol({
        symbol,
        name: existing?.symbol ?? symbol,
        type: existing ? "" : "",
        region: "",
        currency: "",
        match_score: 0,
      });
      loadSymbolAnalysis(symbol).catch(() => undefined);
      navigate(location.pathname, { replace: true });
    }
  }, [location.state, watchlistItems, navigate]);

  useEffect(() => {
    if (analysis && selectedSymbol && pendingAutoSave) {
      handleSave(pendingAutoSave);
      setPendingAutoSave(null);
    }
  }, [analysis, selectedSymbol, pendingAutoSave]);

  const performSearch = async (query: string) => {
    setLoadingSearch(true);
    setError(null);
    try {
      const results = await searchSymbols(query);
      setSearchResults(results);
      setLastQuery(query);
    } catch (err) {
      console.error(err);
      setError((err as Error).message);
    } finally {
      setLoadingSearch(false);
    }
  };

  const loadSymbolAnalysis = async (symbol: string) => {
    setLoadingAnalysis(true);
    setError(null);
    try {
      const data = await fetchSymbolAnalysis({
        symbol,
        start: formatDate(THREE_YEARS_AGO),
        end: formatDate(new Date()),
        interval: "1d",
      });
      setAnalysis(data);
    } catch (err) {
      console.error(err);
      setError((err as Error).message);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleSelectSymbol = (result: SymbolSearchResult) => {
    setSelectedSymbol(result);
    const existing = watchlistItems.find((item) => item.symbol.toUpperCase() === result.symbol.toUpperCase());
    setSelectedStatus(existing?.status ?? WATCHLIST_STATUSES[0]);
    loadSymbolAnalysis(result.symbol).catch(() => undefined);
  };

  const handleSave = (statusOverride?: WatchlistStatus) => {
    if (!selectedSymbol || !analysis || finalScores.length === 0) return;
    void onSave({
      symbol: selectedSymbol.symbol,
      status: statusOverride ?? selectedStatus,
      finalScores,
      averageScore,
      aggregatedSignal: aggregatedSignals.at(-1) ?? null,
    });
  };

  return (
    <div className="mx-auto w-full max-w-7xl gap-8 px-6 py-10 lg:grid lg:grid-cols-[360px,1fr]">
      <aside className="lg:sticky lg:top-8 lg:self-start">
        <SearchPanel
          onSearch={performSearch}
          results={searchResults}
          onSelectSymbol={handleSelectSymbol}
          loading={loadingSearch}
          lastQuery={lastQuery}
          activeSymbol={selectedSymbol?.symbol ?? null}
        />
      </aside>

      <section className="mt-8 flex flex-col gap-6 lg:mt-0">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-sm shadow-slate-200/60">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Signal Dashboard</h2>
              <p className="text-sm text-slate-500">
                Strategies loaded: {strategiesMeta.length} - Data source: Yahoo Finance + Alpha Vantage fundamentals
              </p>
            </div>
            {selectedSymbol && (
              <div className="flex flex-wrap items-center gap-3">
                <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-4 py-1 text-xs font-semibold uppercase tracking-widest text-slate-600">
                  {selectedSymbol.symbol}
                </span>
                <button
                  className="inline-flex items-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={() => loadSymbolAnalysis(selectedSymbol.symbol)}
                  disabled={loadingAnalysis}
                >
                  {loadingAnalysis ? "Refreshing..." : "Manual Refresh"}
                </button>
              </div>
            )}
          </div>
          <p className="mt-3 text-xs uppercase tracking-wide text-slate-400">
            Interval: 1d - Lookback: 3 years - Hover charts or badges for interpretation cues
          </p>
        </div>

        <ScenarioCallouts aggregatedSignals={aggregatedSignals} strategies={strategyCards} />
        <div className="grid gap-4 lg:grid-cols-[1fr,260px]">
          <FinalScoreChart scores={finalScores} average={averageScore} />
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/60">
            <h3 className="text-sm font-semibold text-slate-900">Save to watchlist</h3>
            <p className="mt-2 text-xs text-slate-500">
              Tag the symbol with a status and capture the latest score snapshot for future review.
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
                disabled={!selectedSymbol || !analysis || finalScores.length === 0}
                onClick={() => handleSave()}
                className="inline-flex w-full items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Save symbol snapshot
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-4 text-sm text-rose-700 shadow-sm shadow-rose-200/40">
            <strong className="font-semibold">API message:</strong> {error}
          </div>
        )}

        {analysis && (
          <>
            <PriceChart data={analysis.price_bars} annotations={annotations} latestAggregated={latestAggregated} />
            <AggregatedSignals signals={aggregatedSignals} />
            <div className="grid gap-6 md:grid-cols-2">
              {strategyCards.map((strategy) => (
                <StrategyCard key={strategy.name} strategy={strategy} />
              ))}
            </div>
          </>
        )}

        {!analysis && !loadingAnalysis && (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center text-sm text-slate-500 shadow-sm shadow-slate-200/60">
            Select a symbol from the left to view cross-strategy insights.
          </div>
        )}

        {loadingAnalysis && (
          <div className="rounded-2xl border border-blue-200 bg-blue-50 px-6 py-5 text-sm text-blue-700 shadow-sm shadow-blue-200/40">
            Fetching the latest prices and strategy signals...
          </div>
        )}
      </section>
    </div>
  );
}

function NotFoundPage() {
  return (
    <div className="mx-auto flex min-h-[50vh] w-full max-w-2xl flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-3xl font-semibold text-slate-900">Page not found</h1>
      <p className="text-sm text-slate-500">
        The page you were looking for does not exist. Use the navigation above to return to the dashboard or browse the guides.
      </p>
      <NavLink
        to="/"
        className="inline-flex items-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20"
      >
        Back to dashboard
      </NavLink>
    </div>
  );
}

const navLinks = [
  { label: "Dashboard", to: "/" },
  { label: "Signal Guide", to: "/guides/signals" },
  { label: "Glossary", to: "/guides/glossary" },
  { label: "Watchlist", to: "/watchlist" },
  { label: "Strategy Health", to: "/diagnostics/strategy-weights" },
];

function AppLayout({
  strategies,
  watchlistItems,
  handleSaveWatchlist,
  removeFromWatchlist,
  strategyWeights,
}: {
  strategies: StrategyInfo[];
  watchlistItems: SavedSignal[];
  handleSaveWatchlist: (payload: SavePayload) => void;
  removeFromWatchlist: (id: string) => Promise<void>;
  strategyWeights: Record<string, number>;
}) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-slate-900 px-6 pb-5 pt-8 text-white shadow-lg shadow-slate-900/40">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Small-Cap Growth Dashboard</h1>
              <p className="mt-2 text-sm text-slate-300">
                Track CAN SLIM, Dan Zanger, trend-following, and Livermore patterns with actionable, explainable signals.
              </p>
            </div>
          </div>
          <nav className="flex flex-wrap gap-2 text-sm font-medium">
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  `rounded-full px-4 py-2 transition focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                    isActive ? "bg-white text-slate-900 shadow" : "bg-slate-800/60 text-slate-200 hover:bg-slate-700/80"
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
        <Route
          path="/"
          element={
            <DashboardPage
              strategiesMeta={strategies}
              onSave={handleSaveWatchlist}
              watchlistItems={watchlistItems}
              strategyWeights={strategyWeights}
            />
          }
        />
        <Route path="/guides/signals" element={<SignalGuide />} />
        <Route path="/guides/glossary" element={<GlossaryPage />} />
        <Route path="/watchlist" element={<WatchlistPage items={watchlistItems} remove={removeFromWatchlist} />} />
        <Route path="/diagnostics/strategy-weights" element={<StrategyWeightsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
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
      if (entry.reliability_weight === null || entry.reliability_weight === undefined) {
        return;
      }
      const updatedAt = new Date(entry.updated_at).getTime();
      if (Number.isNaN(updatedAt)) {
        return;
      }
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

  return (
    <BrowserRouter>
      <AppLayout
        strategies={strategies}
        watchlistItems={watchlistItems}
        handleSaveWatchlist={handleSaveWatchlist}
        removeFromWatchlist={remove}
        strategyWeights={strategyWeights}
      />
    </BrowserRouter>
  );
}




