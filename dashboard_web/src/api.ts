import type {
  AggregatedSignal,
  MomentumResponse,
  MomentumTimeframe,
  StrategyInfo,
  StrategyMetricSummary,
  StrategyScore,
  SymbolAnalysis,
  SymbolSearchResult,
  WatchlistItem,
  WatchlistStatus,
} from "./types";

const DEFAULT_API_BASE = "http://localhost:8000";
const apiBase = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE;

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchStrategies(): Promise<StrategyInfo[]> {
  const response = await fetch(`${apiBase}/api/strategies`);
  return handleResponse<StrategyInfo[]>(response);
}

export async function searchSymbols(query: string): Promise<SymbolSearchResult[]> {
  const params = new URLSearchParams({ q: query });
  const response = await fetch(`${apiBase}/api/search?${params.toString()}`);
  const data = await handleResponse<{ query: string; results: SymbolSearchResult[] }>(response);
  return data.results;
}

export type SymbolRequestParams = {
  symbol: string;
  start?: string;
  end?: string;
  interval?: string;
};

export async function fetchSymbolAnalysis(
  params: SymbolRequestParams,
): Promise<SymbolAnalysis> {
  const search = new URLSearchParams();
  if (params.start) search.set("start", params.start);
  if (params.end) search.set("end", params.end);
  if (params.interval) search.set("interval", params.interval);

  const response = await fetch(
    `${apiBase}/api/symbols/${encodeURIComponent(params.symbol)}?${search.toString()}`,
  );
  return handleResponse<SymbolAnalysis>(response);
}

export type WatchlistUpsertPayload = {
  symbol: string;
  status: WatchlistStatus;
  final_scores: StrategyScore[];
  average_score: number;
  aggregated_signal?: AggregatedSignal | null;
};

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const response = await fetch(`${apiBase}/api/watchlist`);
  return handleResponse<WatchlistItem[]>(response);
}

export async function saveWatchlistItem(payload: WatchlistUpsertPayload): Promise<WatchlistItem> {
  const response = await fetch(`${apiBase}/api/watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse<WatchlistItem>(response);
}

export async function deleteWatchlistItem(symbol: string): Promise<void> {
  const response = await fetch(`${apiBase}/api/watchlist/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Failed to remove watchlist entry (${response.status})`);
  }
}
export async function fetchStrategyMetrics(includeHistory = true): Promise<StrategyMetricSummary[]> {
  const params = includeHistory ? '?include_history=true' : '';
  const response = await fetch(`${apiBase}/api/strategy-metrics${params}`);
  return handleResponse<StrategyMetricSummary[]>(response);
}

export async function fetchRussellMomentum(
  timeframe: MomentumTimeframe,
  limit = 50,
): Promise<MomentumResponse> {
  const params = new URLSearchParams({
    timeframe,
    limit: String(limit),
  });
  const response = await fetch(`${apiBase}/api/russell/momentum?${params.toString()}`);
  return handleResponse<MomentumResponse>(response);
}

export async function fetchSpMomentum(
  timeframe: MomentumTimeframe,
  limit = 50,
): Promise<MomentumResponse> {
  const params = new URLSearchParams({
    timeframe,
    limit: String(limit),
  });
  const response = await fetch(`${apiBase}/api/sp500/momentum?${params.toString()}`);
  return handleResponse<MomentumResponse>(response);
}

