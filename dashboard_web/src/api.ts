import type {
  StrategyInfo,
  SymbolAnalysis,
  SymbolSearchResult,
} from "../types";

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
