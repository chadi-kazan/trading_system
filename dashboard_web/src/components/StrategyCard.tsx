import {
  Area,
  AreaChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { StrategyAnalysis } from "../types";
import { formatDisplayDate } from "../utils/date";

interface StrategyCardProps {
  strategy: StrategyAnalysis;
}

const tooltipFormatter = (value: number | string | Array<number | string>) => {
  if (Array.isArray(value)) return value;
  if (typeof value === "number") return value.toFixed(2);
  return value;
};

function getBadge(strategy: StrategyAnalysis): { tone: "positive" | "neutral" | "warning"; text: string } {
  const meta = strategy.latest_metadata ?? {};
  switch (strategy.name) {
    case "dan_zanger_cup_handle": {
      const pullback = typeof meta.handle_pullback === "number" ? meta.handle_pullback : undefined;
      const breakout = typeof meta.breakout_price === "number" ? meta.breakout_price : undefined;
      const rightPeak = typeof meta.right_peak === "number" ? meta.right_peak : undefined;
      if (pullback && pullback >= 0.05 && pullback <= 0.15 && breakout && rightPeak && breakout > rightPeak) {
        return { tone: "positive", text: "Breakout strength confirmed" };
      }
      if (!pullback || !breakout) {
        return { tone: "neutral", text: "Awaiting confirmation" };
      }
      return { tone: "warning", text: "Handle may be too deep" };
    }
    case "can_slim": {
      const score = typeof meta.total_score === "number" ? meta.total_score : undefined;
      if (score && score >= 0.85) return { tone: "positive", text: "Leadership candidate" };
      if (score && score >= 0.75) return { tone: "neutral", text: "Watchlist prospect" };
      return { tone: "warning", text: "Needs stronger fundamentals" };
    }
    case "trend_following": {
      const spread = typeof meta.fast_ema === "number" && typeof meta.slow_ema === "number"
        ? meta.fast_ema - meta.slow_ema
        : undefined;
      if (spread && spread > 0) return { tone: "positive", text: "Momentum aligned" };
      if (!spread) return { tone: "neutral", text: "Tracking trend" };
      return { tone: "warning", text: "Momentum fading" };
    }
    case "livermore_breakout": {
      const rangePct = typeof meta.range_pct === "number" ? meta.range_pct : undefined;
      if (rangePct && rangePct <= 0.12) return { tone: "positive", text: "Tight setup" };
      if (!rangePct) return { tone: "neutral", text: "Monitoring base" };
      return { tone: "warning", text: "Base becoming loose" };
    }
    default:
      return { tone: "neutral", text: "Monitoring" };
  }
}

function renderConfidenceChart(strategy: StrategyAnalysis) {
  const confidenceData = strategy.signals.map((signal) => ({
    date: formatDisplayDate(signal.date),
    confidence: signal.confidence,
  }));

  if (strategy.chart_type === "factor-radar" && strategy.latest_metadata) {
    const scores = Object.entries(strategy.latest_metadata)
      .filter(([key]) => key.endsWith("_score"))
      .map(([key, value]) => ({ factor: key.replace(/_/g, " "), score: Number(value) }));

    if (scores.length > 0) {
      return (
        <ResponsiveContainer width="100%" height={220}>
          <RadarChart data={scores} outerRadius="80%">
            <PolarGrid stroke="#e5e7eb" />
            <PolarAngleAxis dataKey="factor" tick={{ fontSize: 10, fill: "#475569" }} />
            <PolarRadiusAxis angle={30} domain={[0, 1]} tick={{ fontSize: 10, fill: "#475569" }} />
            <Radar name="Score" dataKey="score" stroke="#2563eb" fill="#2563eb" fillOpacity={0.4} />
          </RadarChart>
        </ResponsiveContainer>
      );
    }
  }

  if (confidenceData.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
        No signals yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={confidenceData} margin={{ top: 12, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`confidenceGradient-${strategy.name}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} width={36} />
        <Tooltip formatter={tooltipFormatter} />
        <Area
          type="monotone"
          dataKey="confidence"
          name="Confidence"
          stroke="#22c55e"
          fill={`url(#confidenceGradient-${strategy.name})`}
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function renderMetadata(strategy: StrategyAnalysis) {
  if (!strategy.latest_metadata) return null;
  const entries = Object.entries(strategy.latest_metadata)
    .filter(([key]) => !key.endsWith("_score"))
    .slice(0, 6);
  if (entries.length === 0) return null;

  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50/60 px-4 py-3 text-sm text-slate-600">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Latest Metadata</span>
      <ul className="mt-2 space-y-1">
        {entries.map(([key, value]) => (
          <li key={key} className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-slate-500">{key.replace(/_/g, " ")}</span>
            <span className="text-sm text-slate-700">
              {typeof value === "number" ? value.toFixed(3) : String(value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function StrategyCard({ strategy }: StrategyCardProps) {
  const badge = getBadge(strategy);
  const badgeStyles: Record<typeof badge.tone, string> = {
    positive: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    neutral: "bg-slate-100 text-slate-700 border border-slate-200",
    warning: "bg-amber-50 text-amber-700 border border-amber-200",
  };
  const tooltipLines = [
    strategy.description,
    strategy.investment_bounds ? `Investment criteria: ${strategy.investment_bounds}` : null,
  ].filter(Boolean);
  const tooltipText = tooltipLines.join("\n");

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3
            className="text-base font-semibold text-slate-900"
            title={tooltipText.length > 0 ? tooltipText : undefined}
          >
            {strategy.label}
          </h3>
          <p className="mt-1 text-sm leading-relaxed text-slate-500">{strategy.description}</p>
          {strategy.investment_bounds ? (
            <p className="mt-1 text-xs text-slate-400">
              Investment criteria: <span className="font-medium text-slate-500">{strategy.investment_bounds}</span>
            </p>
          ) : null}
        </div>
        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${badgeStyles[badge.tone]}`}>
          {badge.text}
        </span>
      </div>
      {renderConfidenceChart(strategy)}
      {renderMetadata(strategy)}
    </article>
  );
}
