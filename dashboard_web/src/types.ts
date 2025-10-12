export type StrategyInfo = {
  name: string;
  label: string;
  description: string;
  chart_type: string;
  investment_bounds?: string | null;
  score_guidance?: string | null;
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
  investment_bounds?: string | null;
  score_guidance?: string | null;
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

export type MacroOverlay = {
  regime: string;
  score: number;
  multiplier: number;
  factors: Record<string, number>;
  notes?: string | null;
  updated_at: string;
};

export type EarningsQuality = {
  score?: number | null;
  multiplier?: number | null;
  surprise_average?: number | null;
  positive_ratio?: number | null;
  eps_trend?: number | null;
};

export type SymbolAnalysis = {
  symbol: string;
  start: string;
  end: string;
  interval: string;
  price_bars: PriceBar[];
  strategies: StrategyAnalysis[];
  aggregated_signals: AggregatedSignal[];
  macro_overlay?: MacroOverlay | null;
  earnings_quality?: EarningsQuality | null;
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

export type MomentumTimeframe = "day" | "week" | "month" | "ytd";

export type SectorStrategyScore = {
  strategy: string;
  average_score: number;
  sample_size: number;
};

export type SectorScoreResponse = {
  symbol: string;
  sector?: string | null;
  universe?: string | null;
  timeframe: string;
  sample_size: number;
  strategy_scores: SectorStrategyScore[];
};

export type MomentumEntry = {
  symbol: string;
  name?: string | null;
  sector?: string | null;
  last_price: number;
  change_absolute: number;
  change_percent: number;
  reference_price: number;
  updated_at: string;
  volume?: number | null;
  average_volume?: number | null;
  relative_volume?: number | null;
  data_points: number;
  strategy_scores: Record<string, number>;
  final_score?: number | null;
  overlays?: Record<string, number | null>;
};

export type MomentumResponse = {
  timeframe: MomentumTimeframe;
  generated_at: string;
  universe_size: number;
  evaluated_symbols: number;
  skipped_symbols: number;
  baseline_symbol?: string | null;
  baseline_change_percent?: number | null;
  baseline_last_price?: number | null;
  top_gainers: MomentumEntry[];
  top_losers: MomentumEntry[];
};

