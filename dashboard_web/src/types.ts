export type StrategyInfo = {
  name: string;
  label: string;
  description: string;
  chart_type: string;
};

export type StrategySignal = {
  date: string;
  signal_type: string;
  confidence: number;
  metadata: Record<string, unknown>;
};

export type StrategyAnalysis = {
  name: string;
  label: string;
  description: string;
  chart_type: string;
  signals: StrategySignal[];
  latest_metadata?: Record<string, unknown> | null;
  extras: Record<string, unknown>;
};

export type AggregatedSignal = {
  date: string;
  signal_type: string;
  confidence: number;
  metadata: Record<string, unknown>;
};

export type PriceBar = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  adj_close: number;
  volume: number;
  average_volume?: number | null;
  volume_change?: number | null;
  fifty_two_week_high?: number | null;
  relative_strength?: number | null;
  earnings_growth?: number | null;
  fast_ema?: number | null;
  slow_ema?: number | null;
  atr?: number | null;
};

export type SymbolAnalysis = {
  symbol: string;
  start: string;
  end: string;
  interval: string;
  price_bars: PriceBar[];
  strategies: StrategyAnalysis[];
  aggregated_signals: AggregatedSignal[];
};

export type SymbolSearchResult = {
  symbol: string;
  name: string;
  type: string;
  region: string;
  currency?: string;
  match_score: number;
};

