import { useEffect, useMemo, useState } from "react";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { fetchStrategies, fetchSymbolAnalysis, searchSymbols } from "./api";
import type { AggregatedSignal, StrategyInfo, SymbolAnalysis, SymbolSearchResult } from "./types";
import { SearchPanel } from "./components/SearchPanel";
import { PriceChart } from "./components/PriceChart";
import { StrategyCard } from "./components/StrategyCard";
import { AggregatedSignals } from "./components/AggregatedSignals";
import { ScenarioCallouts } from "./components/ScenarioCallouts";
import { SignalGuide } from "./pages/SignalGuide";
import { GlossaryPage } from "./pages/GlossaryPage";

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

function DashboardPage({ strategiesMeta }: { strategiesMeta: StrategyInfo[] }) {
  const [searchResults, setSearchResults] = useState<SymbolSearchResult[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<SymbolSearchResult | null>(null);
  const [analysis, setAnalysis] = useState<SymbolAnalysis | null>(null);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");

  const aggregatedSignals: AggregatedSignal[] = analysis?.aggregated_signals ?? [];
  const annotations = useMemo(() => extractAnnotations(analysis?.strategies), [analysis?.strategies]);
  const strategyCards = useMemo(() => analysis?.strategies ?? [], [analysis]);
  const latestAggregated = aggregatedSignals.at(-1) ?? null;

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
    loadSymbolAnalysis(result.symbol).catch(() => undefined);
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
                Strategies loaded: {strategiesMeta.length}  -  Data source: Yahoo Finance + Alpha Vantage fundamentals
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
            Interval: 1d  -  Lookback: 3 years  -  Hover charts or badges for interpretation cues
          </p>
        </div>

        <ScenarioCallouts aggregatedSignals={aggregatedSignals} strategies={strategyCards} />

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
];

function AppLayout({ strategies }: { strategies: StrategyInfo[] }) {
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
        <Route path="/" element={<DashboardPage strategiesMeta={strategies} />} />
        <Route path="/guides/signals" element={<SignalGuide />} />
        <Route path="/guides/glossary" element={<GlossaryPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </div>
  );
}

export default function App() {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch((err) => console.error(err));
  }, []);

  return (
    <BrowserRouter>
      <AppLayout strategies={strategies} />
    </BrowserRouter>
  );
}
