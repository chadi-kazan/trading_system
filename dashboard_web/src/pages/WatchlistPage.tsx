import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { SavedSignal, WatchlistStatus } from "../hooks/useWatchlist";
import { FinalScoreChart } from "../components/FinalScoreChart";
import { WATCHLIST_STATUSES } from "../hooks/useWatchlist";
import { formatDisplayDate } from "../utils/date";

interface WatchlistPageProps {
  items: SavedSignal[];
  remove: (symbol: string) => Promise<void>;
}

const STATUS_COLORS: Record<WatchlistStatus, string> = {
  "Watch List": "bg-slate-100 text-slate-700",
  "Has Potential": "bg-blue-100 text-blue-700",
  "Keep Close Eye": "bg-amber-100 text-amber-700",
  "In My Portfolio": "bg-emerald-100 text-emerald-700",
  "Trim Candidate": "bg-rose-100 text-rose-700",
};

export function WatchlistPage({ items, remove }: WatchlistPageProps) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter((item) => item.symbol.toLowerCase().includes(normalized));
  }, [items, query]);

  const handleOpen = (symbol: string) => {
    const record = items.find((entry) => entry.symbol.toUpperCase() === symbol.toUpperCase());
    navigate(`/symbols/${symbol}`, { state: { status: record?.status ?? WATCHLIST_STATUSES[0] } });
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8 px-4 pb-20 pt-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-slate-900">Saved Watchlist</h1>
        <p className="text-base text-slate-600">
          Signals you saved with snapshots of their confidence breakdowns. Click any card to jump back to the dashboard and
          refresh the analysis.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search symbol"
            className="w-full rounded-xl border border-slate-200 px-4 py-2 text-sm shadow-inner shadow-slate-100 transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 sm:w-80"
          />
          <div className="flex flex-wrap gap-2 text-xs text-slate-500">
            {WATCHLIST_STATUSES.map((status) => (
              <span key={status} className={`rounded-full px-3 py-1 ${STATUS_COLORS[status]}`}>
                {status}
              </span>
            ))}
          </div>
        </div>
      </header>

      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500 shadow-sm shadow-slate-200/60">
          Nothing saved yet. Head to the dashboard, load a symbol, and use the "Save to watchlist" controls.
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {filtered.map((item) => (
            <article key={item.id} className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">{item.symbol}</h2>
                  <p className="text-xs text-slate-500">Saved on {formatDisplayDate(item.savedAt)}</p>
                </div>
                <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${STATUS_COLORS[item.status]}`}>
                  {item.status}
                </span>
              </div>
              <FinalScoreChart scores={item.finalScores} average={item.averageScore} />
              {item.aggregatedSignal && (
                <div className="rounded-xl border border-slate-100 bg-slate-50/70 px-4 py-3 text-xs text-slate-600">
                  Latest aggregated signal when saved: {item.aggregatedSignal.signal_type} (confidence {item.aggregatedSignal.confidence.toFixed(2)})
                </div>
              )}
              <div className="flex flex-wrap gap-3 text-xs">
                <button
                  className="inline-flex items-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:opacity-90"
                  onClick={() => handleOpen(item.symbol)}
                >
                  Open in dashboard
                </button>
                <button
                  className="inline-flex items-center rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-500 transition hover:border-rose-300 hover:text-rose-500"
                  onClick={() => remove(item.symbol)}
                >
                  Remove
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
