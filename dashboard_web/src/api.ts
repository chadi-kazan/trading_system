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

// deployed on https://trading-system-jwophbwp8-chadis-projects-70db7a5c.vercel.app/
const DEFAULT_API_BASE = "http://localhost:8000";
const apiBase = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE;

const ACCESS_KEY_STORAGE = "app_access_key";

function getAccessKey(): string | null {
  return localStorage.getItem(ACCESS_KEY_STORAGE);
}

function getAuthHeaders(additionalHeaders?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {};
  const accessKey = getAccessKey();

  if (accessKey) {
    headers["X-App-Access-Key"] = accessKey;
  }

  if (additionalHeaders) {
    Object.assign(headers, additionalHeaders);
  }

  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    // Handle authentication errors by clearing invalid access key
    if (response.status === 401 || response.status === 403) {
      localStorage.removeItem(ACCESS_KEY_STORAGE);
      window.location.reload(); // Reload to show login screen
    }
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchStrategies(): Promise<StrategyInfo[]> {
  const response = await fetch(`${apiBase}/api/strategies`, {
    headers: getAuthHeaders(),
  });
  return handleResponse<StrategyInfo[]>(response);
}

export async function searchSymbols(query: string): Promise<SymbolSearchResult[]> {
  const params = new URLSearchParams({ q: query });
  const response = await fetch(`${apiBase}/api/search?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
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
    {
      headers: getAuthHeaders(),
    },
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
  const response = await fetch(`${apiBase}/api/watchlist`, {
    headers: getAuthHeaders(),
  });
  return handleResponse<WatchlistItem[]>(response);
}

export async function saveWatchlistItem(payload: WatchlistUpsertPayload): Promise<WatchlistItem> {
  const response = await fetch(`${apiBase}/api/watchlist`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  return handleResponse<WatchlistItem>(response);
}

export async function deleteWatchlistItem(symbol: string): Promise<void> {
  const response = await fetch(`${apiBase}/api/watchlist/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Failed to remove watchlist entry (${response.status})`);
  }
}
export async function fetchStrategyMetrics(includeHistory = true): Promise<StrategyMetricSummary[]> {
  const params = includeHistory ? '?include_history=true' : '';
  const response = await fetch(`${apiBase}/api/strategy-metrics${params}`, {
    headers: getAuthHeaders(),
  });
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
  const response = await fetch(`${apiBase}/api/russell/momentum?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
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
  const response = await fetch(`${apiBase}/api/sp500/momentum?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse<MomentumResponse>(response);
}
export async function fetchSectorScores(symbol: string, timeframe: MomentumTimeframe = "week"): Promise<SectorScoreResponse> {
  const params = new URLSearchParams({
    symbol,
    timeframe,
  });
  const response = await fetch(`${apiBase}/api/momentum/sector-scores?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse<SectorScoreResponse>(response);
}

// Admin API functions
export type AdminRefreshResponse = {
  status: string;
  message: string;
  output?: string;
};

export type AdminStatusResponse = {
  russell_last_updated: string | null;
  fundamentals_last_updated: string | null;
};

export async function refreshRussell(apiKey: string): Promise<AdminRefreshResponse> {
  const response = await fetch(`${apiBase}/api/admin/refresh-russell`, {
    method: "POST",
    headers: getAuthHeaders({ "X-Admin-API-Key": apiKey }),
  });
  return handleResponse<AdminRefreshResponse>(response);
}

export async function refreshFundamentals(
  apiKey: string,
  includeRussell = true,
  includeSP500 = true,
  limit?: number,
): Promise<AdminRefreshResponse> {
  const params = new URLSearchParams();
  if (includeRussell) params.set("include_russell", "true");
  if (includeSP500) params.set("include_sp500", "true");
  if (limit) params.set("limit", String(limit));

  const response = await fetch(`${apiBase}/api/admin/refresh-fundamentals?${params.toString()}`, {
    method: "POST",
    headers: getAuthHeaders({ "X-Admin-API-Key": apiKey }),
  });
  return handleResponse<AdminRefreshResponse>(response);
}

export async function refreshAll(apiKey: string): Promise<AdminRefreshResponse> {
  const response = await fetch(`${apiBase}/api/admin/refresh-all`, {
    method: "POST",
    headers: getAuthHeaders({ "X-Admin-API-Key": apiKey }),
  });
  return handleResponse<AdminRefreshResponse>(response);
}

export async function getAdminStatus(apiKey: string): Promise<AdminStatusResponse> {
  const response = await fetch(`${apiBase}/api/admin/refresh-status`, {
    headers: getAuthHeaders({ "X-Admin-API-Key": apiKey }),
  });
  return handleResponse<AdminStatusResponse>(response);
}

