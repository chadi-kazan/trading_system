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

interface StrategyCardProps {
  strategy: StrategyAnalysis;
}

const tooltipFormatter = (value: number | string | Array<number | string>) => {
  if (Array.isArray(value)) return value;
  if (typeof value === "number") return value.toFixed(2);
  return value;
};

function renderConfidenceChart(strategy: StrategyAnalysis) {
  const confidenceData = strategy.signals.map((signal) => ({
    date: new Date(signal.date).toLocaleDateString(),
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
    <div className="rounded-xl border border-slate-100 bg-slate-50/60 px-4 py-3 text-sm text-slate-600">
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
  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{strategy.label}</h3>
          <p className="mt-1 text-sm leading-relaxed text-slate-500">{strategy.description}</p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-500">
          {strategy.chart_type}
        </span>
      </div>
      {renderConfidenceChart(strategy)}
      {renderMetadata(strategy)}
    </article>
  );
}
