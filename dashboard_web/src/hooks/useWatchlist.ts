import { useCallback, useEffect, useState } from "react";
import {
  deleteWatchlistItem,
  fetchWatchlist,
  saveWatchlistItem,
  type WatchlistUpsertPayload,
} from "../api";
import type { AggregatedSignal, StrategyScore, WatchlistItem as ApiWatchlistItem, WatchlistStatus } from "../types";
export type { WatchlistStatus } from "../types";

export const WATCHLIST_STATUSES: WatchlistStatus[] = [
  "Watch List",
  "Has Potential",
  "Keep Close Eye",
  "In My Portfolio",
  "Trim Candidate",
];

export type SavedSignal = {
  id: string;
  symbol: string;
  status: WatchlistStatus;
  savedAt: string;
  averageScore: number;
  finalScores: StrategyScore[];
  aggregatedSignal: AggregatedSignal | null;
};

function mapFromApi(item: ApiWatchlistItem): SavedSignal {
  return {
    id: item.id,
    symbol: item.symbol,
    status: item.status,
    savedAt: item.saved_at,
    averageScore: item.average_score,
    finalScores: item.final_scores ?? [],
    aggregatedSignal: item.aggregated_signal ?? null,
  };
}

export function useWatchlist() {
  const [items, setItems] = useState<SavedSignal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWatchlist();
      setItems(data.map(mapFromApi));
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [refresh]);

  const save = useCallback(async (payload: WatchlistUpsertPayload) => {
    setError(null);
    try {
      const saved = mapFromApi(await saveWatchlistItem(payload));
      setItems((prev) => {
        const next = prev.filter((item) => item.id !== saved.id);
        next.push(saved);
        next.sort((a, b) => b.savedAt.localeCompare(a.savedAt));
        return next;
      });
      return saved;
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : "Failed to save watchlist entry";
      setError(message);
      throw err;
    }
  }, []);

  const remove = useCallback(async (symbol: string) => {
    setError(null);
    try {
      await deleteWatchlistItem(symbol);
      setItems((prev) => prev.filter((item) => item.symbol.toUpperCase() !== symbol.toUpperCase()));
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : "Failed to delete watchlist entry";
      setError(message);
      throw err;
    }
  }, []);

  return {
    items,
    loading,
    error,
    refresh,
    save,
    remove,
  };
}
