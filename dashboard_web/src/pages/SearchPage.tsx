import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SearchPanel } from "../components/SearchPanel";
import { searchSymbols } from "../api";
import type { SymbolSearchResult } from "../types";
import type { SavedSignal } from "../hooks/useWatchlist";

type SearchPageProps = {
  watchlistItems: SavedSignal[];
};

export function SearchPage({ watchlistItems }: SearchPageProps) {
  const navigate = useNavigate();
  const [results, setResults] = useState<SymbolSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [activeSymbol, setActiveSymbol] = useState<string | null>(null);

  const performSearch = async (query: string) => {
    setLoading(true);
    setError(null);
    try {
      const matches = await searchSymbols(query);
      setResults(matches);
      setLastQuery(query);
    } catch (err) {
      setError((err as Error).message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSymbol = (symbol: SymbolSearchResult) => {
    setActiveSymbol(symbol.symbol);
    navigate(`/symbols/${symbol.symbol}`, { state: { fromSearch: true } });
  };

  const hasWatchlist = watchlistItems.length > 0;
  const topWatchlist = hasWatchlist ? watchlistItems.slice(0, 6) : [];

  return (
    <div className="mx-auto w-full max-w-6xl space-y-8 px-6 pb-16 pt-10">
      <header className="space-y-3">
        <h1 className="text-3xl font-semibold text-slate-900">Find a Signal</h1>
        <p className="text-base text-slate-600">
          Search for tickers or keywords to analyse fundamentals, strategy confidence, and macro overlays on the dedicated dashboard.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[460px,1fr]">
        <SearchPanel
          onSearch={performSearch}
          results={results}
          onSelectSymbol={handleSelectSymbol}
          loading={loading}
          lastQuery={lastQuery}
          activeSymbol={activeSymbol}
        />

        <aside className="space-y-4">
          {error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50/80 px-5 py-4 text-sm text-rose-700 shadow-sm shadow-rose-200/40">
              <span className="font-semibold">Search error:</span> {error}
            </div>
          ) : null}

          {hasWatchlist ? (
            <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm shadow-slate-200/60">
              <h2 className="text-sm font-semibold text-slate-900">Recently saved</h2>
              <p className="mt-1 text-xs text-slate-500">Jump back into symbols you saved to the watchlist.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {topWatchlist.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelectSymbol({ symbol: item.symbol, name: "", type: "", region: "", match_score: 0 })}
                    className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-blue-300 hover:text-blue-600"
                  >
                    {item.symbol}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-6 text-sm text-slate-500 shadow-sm shadow-slate-200/60">
              Save interesting tickers from the dashboard to revisit them here.
            </div>
          )}

          <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-xs text-slate-500 shadow-sm shadow-slate-200/60">
            <h2 className="text-sm font-semibold text-slate-900">Search Tips</h2>
            <ul className="mt-3 space-y-2">
              <li>Type a ticker (e.g. <span className="font-semibold">PLUG</span>) or keyword like <span className="font-semibold">software</span>.</li>
              <li>Use the watchlist to pin favourites and revisit their dashboards.</li>
              <li>Macro and fundamentals overlays appear once you open a symbol detail page.</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}

