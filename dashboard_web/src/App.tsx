import { useEffect, useMemo, useState } from "react";
import { fetchStrategies, fetchSymbolAnalysis, searchSymbols } from "./api";
import type { StrategyInfo, SymbolAnalysis, SymbolSearchResult } from "./types";
import { SearchPanel } from "./components/SearchPanel";
import { PriceChart } from "./components/PriceChart";
import { StrategyCard } from "./components/StrategyCard";
import { AggregatedSignals } from "./components/AggregatedSignals";

const THREE_YEARS_AGO = new Date();
THREE_YEARS_AGO.setDate(THREE_YEARS_AGO.getDate() - 365 * 3);

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

export default function App() {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [searchResults, setSearchResults] = useState<SymbolSearchResult[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<SymbolSearchResult | null>(null);
  const [analysis, setAnalysis] = useState<SymbolAnalysis | null>(null);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch((err) => {
      console.error(err);
    });
  }, []);

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

  const strategyCards = useMemo(() => analysis?.strategies ?? [], [analysis]);

  return (
    <div className="min-h-screen bg-slate-50 pb-16">
      <header className="bg-slate-900 px-6 py-8 text-white shadow-lg shadow-slate-900/40">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Small-Cap Growth Dashboard</h1>
              <p className="mt-1 text-sm text-slate-300">
                Explore signals across Dan Zanger, CAN SLIM, EMA Trend Following, and Livermore breakout strategies.
              </p>
            </div>
            {selectedSymbol && (
              <span className="inline-flex items-center rounded-full border border-slate-700/60 bg-slate-800/70 px-4 py-1 text-xs font-semibold uppercase tracking-widest text-slate-200">
                {selectedSymbol.symbol}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-slate-400">
            <span>Strategies loaded: {strategies.length}</span>
            <span>·</span>
            <span>Data source: Yahoo Finance + Alpha Vantage fundamentals</span>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl gap-8 px-6 py-10 lg:grid lg:grid-cols-[360px,1fr]">
        <div className="lg:sticky lg:top-8 lg:self-start">
          <SearchPanel
            onSearch={performSearch}
            results={searchResults}
            onSelectSymbol={handleSelectSymbol}
            loading={loadingSearch}
            lastQuery={lastQuery}
            activeSymbol={selectedSymbol?.symbol}
          />
        </div>

        <div className="mt-8 flex flex-col gap-6 lg:mt-0">
          {error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-4 text-sm text-rose-700 shadow-sm shadow-rose-200/40">
              <strong className="font-semibold">API message:</strong> {error}
            </div>
          )}

          {selectedSymbol && (
            <div className="rounded-2xl border border-slate-200 bg-white px-6 py-4 shadow-sm shadow-slate-200/60">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{selectedSymbol.symbol}</h2>
                  <p className="text-sm text-slate-500">{selectedSymbol.name}</p>
                </div>
                <button
                  className="inline-flex items-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={() => loadSymbolAnalysis(selectedSymbol.symbol)}
                  disabled={loadingAnalysis}
                >
                  {loadingAnalysis ? "Refreshing…" : "Manual Refresh"}
                </button>
              </div>
              <p className="mt-3 text-xs uppercase tracking-wide text-slate-400">
                Interval: 1d • Lookback: 3 years
              </p>
            </div>
          )}

          {analysis && (
            <>
              <PriceChart data={analysis.price_bars} />
              <AggregatedSignals signals={analysis.aggregated_signals} />
              <div className="grid gap-6 md:grid-cols-2">
                {strategyCards.map((strategy) => (
                  <StrategyCard key={strategy.name} strategy={strategy} />
                ))}
              </div>
            </>
          )}

          {!analysis && !loadingAnalysis && (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center text-sm text-slate-500 shadow-sm shadow-slate-200/60">
              Select a symbol to view cross-strategy insights.
            </div>
          )}

          {loadingAnalysis && (
            <div className="rounded-2xl border border-blue-200 bg-blue-50 px-6 py-5 text-sm text-blue-700 shadow-sm shadow-blue-200/40">
              Fetching the latest prices and strategy signals…
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
