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

export type StrategyScore = {
  name: string;
  label: string;
  value: number;
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

export type WatchlistStatus =
  | "Watch List"
  | "Has Potential"
  | "Keep Close Eye"
  | "In My Portfolio"
  | "Trim Candidate";

export type WatchlistItem = {
  id: string;
  symbol: string;
  status: WatchlistStatus;
  saved_at: string;
  average_score: number;
  final_scores: StrategyScore[];
  aggregated_signal?: AggregatedSignal | null;
};
export type StrategyMetricHistory = {
  observed_at: string;
  reliability_weight?: number | null;
  avg_excess_return?: number | null;
  volatility?: number | null;
  max_drawdown?: number | null;
  win_rate?: number | null;
  sample_size?: number | null;
  correlation_penalty?: number | null;
  regime_fit?: number | null;
  decay_lambda?: number | null;
  extras: Record<string, unknown>;
};

export type StrategyMetricSummary = {
  strategy: {
    id: string;
    label: string;
    description?: string | null;
    default_weight?: number | null;
  };
  regime: {
    slug: string;
    name: string;
    description?: string | null;
    detection_notes?: string | null;
  };
  sample_size: number;
  wins: number;
  win_rate?: number | null;
  avg_excess_return?: number | null;
  volatility?: number | null;
  max_drawdown?: number | null;
  decay_lambda?: number | null;
  reliability_weight?: number | null;
  correlation_penalty?: number | null;
  regime_fit?: number | null;
  last_sampled_at?: string | null;
  updated_at: string;
  extras: Record<string, unknown>;
  history: StrategyMetricHistory[];
};

