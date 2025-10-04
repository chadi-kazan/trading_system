import { useState } from "react";
import type { SymbolSearchResult } from "../types";

interface SearchPanelProps {
  onSearch: (query: string) => Promise<void>;
  results: SymbolSearchResult[];
  onSelectSymbol: (symbol: SymbolSearchResult) => void;
  loading: boolean;
  lastQuery: string;
  activeSymbol?: string | null;
}

export function SearchPanel({
  onSearch,
  results,
  onSelectSymbol,
  loading,
  lastQuery,
  activeSymbol,
}: SearchPanelProps) {
  const [input, setInput] = useState(lastQuery);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    await onSearch(trimmed);
  };

  return (
    <section className="flex flex-col gap-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
        <h2 className="text-lg font-semibold text-slate-900">Symbol Search</h2>
        <p className="mt-1 text-sm text-slate-500">
          Search any ticker; Alpha Vantage matches appear first with a local universe fallback.
        </p>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="space-y-2">
            <label htmlFor="symbol-input" className="text-sm font-medium text-slate-600">
              Symbol or Keyword
            </label>
            <input
              id="symbol-input"
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="e.g. PLUG, software"
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-base shadow-inner shadow-slate-100 transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
            />
          </div>
          <div className="flex items-center justify-between">
            <button
              type="submit"
              className="inline-flex items-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
            >
              {loading ? "Searching…" : "Search"}
            </button>
            {lastQuery && !loading && (
              <span className="text-xs uppercase tracking-wide text-slate-400">Last query: {lastQuery}</span>
            )}
          </div>
        </form>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-slate-900">Matches</h3>
          <span className="text-xs font-medium text-slate-400">{results.length} result{results.length === 1 ? "" : "s"}</span>
        </div>
        <div className="mt-4 space-y-2">
          {results.length === 0 && (
            <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center text-sm text-slate-500">
              Try searching for a ticker symbol or industry keyword.
            </p>
          )}
          {results.map((item) => {
            const isActive = activeSymbol && item.symbol.toUpperCase() === activeSymbol.toUpperCase();
            return (
              <button
                key={`${item.symbol}-${item.region}`}
                type="button"
                onClick={() => onSelectSymbol(item)}
                className={`w-full rounded-xl border px-4 py-3 text-left transition focus:outline-none focus:ring-2 focus:ring-blue-500/60 ${
                  isActive
                    ? "border-blue-200 bg-blue-50 text-blue-700 shadow-inner"
                    : "border-transparent bg-slate-50/60 text-slate-700 hover:border-slate-200 hover:bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold uppercase tracking-wide text-slate-800">
                    {item.symbol}
                  </div>
                  {item.match_score > 0 && (
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                      Score {item.match_score.toFixed(2)}
                    </span>
                  )}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {item.name || "Unnamed"} · {item.region}
                  {item.currency ? ` · ${item.currency}` : ""}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
