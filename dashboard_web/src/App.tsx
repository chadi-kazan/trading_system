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
    <div className="app-shell">
      <header className="app-header">
        <h1>Small-Cap Growth Dashboard</h1>
        <p style={{ marginTop: "0.4rem", color: "rgba(255,255,255,0.8)" }}>
          Explore strategy signals, confidence trends, and aggregated views for any symbol using the FastAPI backend.
        </p>
      </header>

      <main className="app-content">
        <SearchPanel
          onSearch={performSearch}
          results={searchResults}
          onSelectSymbol={handleSelectSymbol}
          loading={loadingSearch}
          lastQuery={lastQuery}
        />

        <div className="charts-container">
          {error && (
            <div className="panel" style={{ borderLeft: "4px solid #dc2626" }}>
              <strong style={{ color: "#dc2626" }}>Error:</strong> {error}
            </div>
          )}

          {selectedSymbol && (
            <div className="panel">
              <h2>{selectedSymbol.symbol}</h2>
              <p style={{ marginTop: "0.25rem" }}>{selectedSymbol.name}</p>
              <div className="refresh-row">
                <button className="primary" onClick={() => loadSymbolAnalysis(selectedSymbol.symbol)} disabled={loadingAnalysis}>
                  {loadingAnalysis ? "Refreshing…" : "Manual Refresh"}
                </button>
                <span style={{ color: "#6b7280", fontSize: "0.9rem" }}>
                  Interval: 1d · Lookback: 3 years
                </span>
              </div>
            </div>
          )}

          {analysis && (
            <>
              <PriceChart data={analysis.price_bars} />
              <AggregatedSignals signals={analysis.aggregated_signals} />
              <div className="strategy-grid">
                {strategyCards.map((strategy) => (
                  <StrategyCard key={strategy.name} strategy={strategy} />
                ))}
              </div>
            </>
          )}

          {!analysis && !loadingAnalysis && (
            <div className="panel" style={{ textAlign: "center", color: "#6b7280" }}>
              <p>Select a symbol to view strategy insights.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
