import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchRussellMomentum } from "../api";
import type { RussellMomentumEntry, RussellMomentumResponse, RussellTimeframe } from "../types";
import type { SavedSignal, WatchlistStatus } from "../hooks/useWatchlist";
import { WATCHLIST_STATUSES } from "../hooks/useWatchlist";

const TIMEFRAME_OPTIONS: Array<{ label: string; value: RussellTimeframe; hint: string }> = [
  { label: "1 Day", value: "day", hint: "Yesterday's close vs latest close." },
  { label: "1 Week", value: "week", hint: "Last 5 trading sessions." },
  { label: "1 Month", value: "month", hint: "Trailing 21 trading sessions." },
  { label: "YTD", value: "ytd", hint: "Performance since the start of the year." },
];

const LIMIT_OPTIONS = [10, 25, 50, 100, 150, 200];

type LeaderboardView = "gainers" | "laggards";

const VIEW_OPTIONS: Array<{ label: string; value: LeaderboardView; description: string }> = [
  { label: "Top Risers", value: "gainers", description: "Strongest percentage moves over the selected window." },
  { label: "Underperformers", value: "laggards", description: "Weakest percentage moves over the selected window." },
];

type RussellMomentumPageProps = {
  watchlistItems: SavedSignal[];
  onSaveWatchlist: (symbol: string, status: WatchlistStatus) => Promise<unknown>;
};

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const rounded = Number.parseFloat(value.toFixed(2));
  return `${rounded > 0 ? "+" : ""}${rounded.toFixed(2)}%`;
}

function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString();
}

function getRankClass(changePercent: number): string {
  if (Number.isNaN(changePercent)) {
    return "";
  }
  if (changePercent >= 15) return "bg-emerald-500/10 text-emerald-600";
  if (changePercent >= 5) return "bg-emerald-400/10 text-emerald-500";
  if (changePercent <= -10) return "bg-rose-500/10 text-rose-600";
  if (changePercent <= -3) return "bg-rose-400/10 text-rose-500";
  return "bg-slate-200 text-slate-600";
}

export function RussellMomentumPage({ watchlistItems, onSaveWatchlist }: RussellMomentumPageProps): JSX.Element {
  const navigate = useNavigate();
  const [timeframe, setTimeframe] = useState<RussellTimeframe>("week");
  const [limit, setLimit] = useState<number>(50);
  const [view, setView] = useState<LeaderboardView>("gainers");
  const [data, setData] = useState<RussellMomentumResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<number>(0);
  const [statusOverrides, setStatusOverrides] = useState<Record<string, WatchlistStatus>>({});
  const [savingSymbol, setSavingSymbol] = useState<string | null>(null);
  const [saveFeedback, setSaveFeedback] = useState<Record<string, { type: "success" | "error"; message: string }>>({});
  const watchlistMap = useMemo(() => {
    const map = new Map<string, SavedSignal>();
    watchlistItems.forEach((item) => {
      map.set(item.symbol.toUpperCase(), item);
    });
    return map;
  }, [watchlistItems]);
  const defaultStatus = WATCHLIST_STATUSES[0];

  const getSelectedStatus = (symbol: string): WatchlistStatus => {
    const upper = symbol.toUpperCase();
    return statusOverrides[upper] ?? watchlistMap.get(upper)?.status ?? defaultStatus;
  };

  const handleStatusChange = (symbol: string, status: WatchlistStatus) => {
    const upper = symbol.toUpperCase();
    setStatusOverrides((prev) => ({ ...prev, [upper]: status }));
  };

  const handleSaveSymbol = async (symbol: string) => {
    const upper = symbol.toUpperCase();
    const status = getSelectedStatus(upper);
    setSavingSymbol(upper);
    try {
      await onSaveWatchlist(upper, status);
      setSaveFeedback((prev) => ({
        ...prev,
        [upper]: { type: "success", message: `Tracked as ${status}` },
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update watchlist";
      setSaveFeedback((prev) => ({
        ...prev,
        [upper]: { type: "error", message },
      }));
    } finally {
      setSavingSymbol(null);
    }
  };

  const handleAnalyzeSymbol = (symbol: string) => {
    const status = getSelectedStatus(symbol);
    navigate("/", { state: { symbol: symbol.toUpperCase(), status } });
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchRussellMomentum(timeframe, limit)
      .then((response) => {
        if (!cancelled) {
          setData(response);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Failed to load Russell momentum data.";
          setError(message);
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [timeframe, limit, refreshToken]);

  const entries: RussellMomentumEntry[] = useMemo(() => {
    if (!data) {
      return [];
    }
    return view === "gainers" ? data.top_gainers : data.top_losers;
  }, [data, view]);

  const baselineSummary = useMemo(() => {
    if (!data || !data.baseline_symbol) {
      return null;
    }
    return {
      symbol: data.baseline_symbol,
      change: data.baseline_change_percent,
      price: data.baseline_last_price,
    };
  }, [data]);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-500">Russell 2000 Momentum</p>
          <h2 className="text-3xl font-semibold text-slate-900 sm:text-4xl">Momentum Leaderboard</h2>
          <p className="max-w-2xl text-sm text-slate-600">
            Scan Russell 2000 constituents for the strongest and weakest performers across multiple time horizons. Use these
            snapshots to seed deeper strategy analysis or refresh your watchlist.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setRefreshToken((token) => token + 1)}
          className="inline-flex items-center justify-center rounded-md border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:border-blue-300 hover:text-blue-600 hover:shadow"
        >
          Refresh Data
        </button>
      </header>

      <section className="grid gap-4 rounded-xl bg-white p-6 shadow-sm shadow-slate-200">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {TIMEFRAME_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setTimeframe(option.value)}
                className={`rounded-full border px-4 py-2 text-sm transition focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 ${
                  timeframe === option.value
                    ? "border-blue-500 bg-blue-500 text-white shadow"
                    : "border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-600"
                }`}
                title={option.hint}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-500">
            <label htmlFor="limit-select" className="font-medium text-slate-600">
              Top Count
            </label>
            <select
              id="limit-select"
              value={limit}
              onChange={(event) => setLimit(Number.parseInt(event.target.value, 10))}
              className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-200"
            >
              {LIMIT_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  Top {value}
                </option>
              ))}
            </select>
            {baselineSummary ? (
              <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                Benchmark {baselineSummary.symbol}: {formatPercent(baselineSummary.change)}
              </span>
            ) : null}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryTile label="Universe Size" value={data?.universe_size} suffix="symbols" />
          <SummaryTile label="Evaluated" value={data?.evaluated_symbols} suffix="symbols" />
          <SummaryTile label="Skipped" value={data?.skipped_symbols} suffix="symbols" />
          <SummaryTile
            label="Generated"
            value={data ? new Date(data.generated_at).toLocaleString() : "—"}
            isString
          />
        </div>
      </section>

      <section className="rounded-xl bg-white p-6 shadow-sm shadow-slate-200">
        <div className="flex flex-col gap-3 border-b border-slate-100 pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-xl font-semibold text-slate-900">
              {view === "gainers" ? "Top Risers" : "Underperformers"}
            </h3>
            <p className="text-sm text-slate-500">
              {VIEW_OPTIONS.find((option) => option.value === view)?.description ?? ""}
            </p>
          </div>
          <div className="flex gap-2">
            {VIEW_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setView(option.value)}
                className={`rounded-full border px-4 py-2 text-sm transition focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 ${
                  view === option.value
                    ? "border-blue-500 bg-blue-500 text-white shadow"
                    : "border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-600"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <p className="text-sm text-slate-500">Loading Russell 2000 momentum...</p>
          </div>
        ) : error ? (
          <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
            {error}
          </div>
        ) : entries.length === 0 ? (
          <div className="flex h-40 items-center justify-center">
            <p className="text-sm text-slate-500">No symbols matched the selected filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-3 pr-4">Rank</th>
                  <th className="py-3 pr-4">Symbol</th>
                  <th className="py-3 pr-4">Company</th>
                  <th className="py-3 pr-4">Sector</th>
                  <th className="py-3 pr-4 text-right">Last Price</th>
                  <th className="py-3 pr-4 text-right">Change</th>
                  <th className="py-3 pr-4 text-right">Change %</th>
                  <th className="py-3 pr-4 text-right">Volume</th>
                  <th className="py-3 pr-4 text-right">Rel. Vol</th>
                  <th className="py-3 pr-4 text-right">Data Points</th>
                  <th className="py-3 pr-4 text-right">Updated</th>
                  <th className="py-3 pr-4 text-right">Watchlist</th>
                  <th className="py-3 pl-4 text-right">Quick Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {entries.map((entry, index) => {
                  const symbolKey = entry.symbol.toUpperCase();
                  return (
                    <TableRow
                      key={entry.symbol}
                      entry={entry}
                      index={index}
                      currentStatus={getSelectedStatus(symbolKey)}
                      onStatusChange={handleStatusChange}
                      onSaveWatchlist={handleSaveSymbol}
                      onAnalyze={handleAnalyzeSymbol}
                      isSaving={savingSymbol === symbolKey}
                      feedback={saveFeedback[symbolKey] ?? null}
                      isTracked={watchlistMap.has(symbolKey)}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function SummaryTile({
  label,
  value,
  suffix,
  isString = false,
}: {
  label: string;
  value: number | string | null | undefined;
  suffix?: string;
  isString?: boolean;
}) {
  const display =
    value === null || value === undefined
      ? "—"
      : isString
        ? String(value)
        : Number.isFinite(value)
          ? Number(value).toLocaleString()
          : String(value);
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-900">
        {display} {suffix ? <span className="text-xs font-medium text-slate-400">{suffix}</span> : null}
      </p>
    </div>
  );
}

type TableRowProps = {
  entry: RussellMomentumEntry;
  index: number;
  currentStatus: WatchlistStatus;
  onStatusChange: (symbol: string, status: WatchlistStatus) => void;
  onSaveWatchlist: (symbol: string) => void;
  onAnalyze: (symbol: string) => void;
  isSaving: boolean;
  feedback: { type: "success" | "error"; message: string } | null;
  isTracked: boolean;
};

function TableRow({
  entry,
  index,
  currentStatus,
  onStatusChange,
  onSaveWatchlist,
  onAnalyze,
  isSaving,
  feedback,
  isTracked,
}: TableRowProps): JSX.Element {
  const changeClass =
    entry.change_percent > 0
      ? "text-emerald-600"
      : entry.change_percent < 0
        ? "text-rose-600"
        : "text-slate-600";
  const relativeVolume = entry.relative_volume ?? null;
  const lastUpdated = new Date(entry.updated_at);
  const statusId = `status-${entry.symbol}`;
  const trackLabel = isTracked ? "Update" : "Add";
  const feedbackClass =
    feedback?.type === "success"
      ? "text-emerald-600"
      : feedback?.type === "error"
        ? "text-rose-600"
        : "text-slate-500";

  return (
    <tr className="align-middle">
      <td className="whitespace-nowrap py-3 pr-4">
        <span
          className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${getRankClass(entry.change_percent)}`}
        >
          {index + 1}
        </span>
      </td>
      <td className="whitespace-nowrap py-3 pr-4 font-semibold text-slate-900">{entry.symbol}</td>
      <td className="max-w-xs truncate py-3 pr-4 text-slate-600" title={entry.name ?? undefined}>
        {entry.name ?? "—"}
      </td>
      <td className="whitespace-nowrap py-3 pr-4 text-slate-500">{entry.sector ?? "—"}</td>
      <td className="whitespace-nowrap py-3 pr-4 text-right font-medium text-slate-900">
        {formatCurrency(entry.last_price)}
      </td>
      <td className={`whitespace-nowrap py-3 pr-4 text-right ${changeClass}`}>{formatCurrency(entry.change_absolute)}</td>
      <td className={`whitespace-nowrap py-3 pr-4 text-right font-semibold ${changeClass}`}>
        {formatPercent(entry.change_percent)}
      </td>
      <td className="whitespace-nowrap py-3 pr-4 text-right text-slate-500">{formatNumber(entry.volume ?? null)}</td>
      <td className="whitespace-nowrap py-3 pr-4 text-right text-slate-500">
        {relativeVolume ? relativeVolume.toFixed(2) : "—"}
        {relativeVolume && relativeVolume > 1.5 ? (
          <span className="ml-1 inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-600">
            Elevated
          </span>
        ) : null}
      </td>
      <td className="whitespace-nowrap py-3 pr-4 text-right text-slate-500">{entry.data_points}</td>
      <td className="whitespace-nowrap py-3 pr-4 text-right text-slate-400">
        {Number.isNaN(lastUpdated.getTime()) ? "—" : lastUpdated.toLocaleDateString()}
      </td>
      <td className="whitespace-nowrap py-3 pr-4 text-right">
        <div className="flex flex-col items-end gap-2">
          <select
            id={statusId}
            value={currentStatus}
            onChange={(event) => onStatusChange(entry.symbol, event.target.value as WatchlistStatus)}
            className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            {WATCHLIST_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          {isTracked ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-600">
              Tracked
            </span>
          ) : null}
        </div>
      </td>
      <td className="whitespace-nowrap py-3 pl-4 text-right">
        <div className="flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={() => onSaveWatchlist(entry.symbol)}
            disabled={isSaving}
            className={`inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-semibold transition ${
              isSaving
                ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                : "border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-600"
            }`}
          >
            {isSaving ? "Saving…" : `${trackLabel} Watchlist`}
          </button>
          <button
            type="button"
            onClick={() => onAnalyze(entry.symbol)}
            className="inline-flex items-center rounded-md border border-blue-500 bg-blue-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-300 focus:ring-offset-2"
          >
            Analyze
          </button>
        </div>
        {feedback ? <p className={`mt-1 text-xs ${feedbackClass}`}>{feedback.message}</p> : null}
      </td>
    </tr>
  );
}

export default RussellMomentumPage;
