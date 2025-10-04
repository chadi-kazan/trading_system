import { ResponsiveContainer, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from "recharts";
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
            <PolarGrid />
            <PolarAngleAxis dataKey="factor" tick={{ fontSize: 10 }} />
            <PolarRadiusAxis angle={30} domain={[0, 1]} />
            <Radar name="Score" dataKey="score" stroke="#2563eb" fill="#2563eb" fillOpacity={0.4} />
          </RadarChart>
        </ResponsiveContainer>
      );
    }
  }

  if (confidenceData.length === 0) {
    return <div style={{ textAlign: "center", color: "#6b7280" }}>No signals yet</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={confidenceData} margin={{ top: 12, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" hide minTickGap={32} />
        <YAxis domain={[0, 1]} width={40} />
        <Tooltip formatter={tooltipFormatter} />
        <Area type="monotone" dataKey="confidence" name="Confidence" stroke="#22c55e" fill="url(#confidenceGradient)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function renderMetadata(strategy: StrategyAnalysis) {
  if (!strategy.latest_metadata) return null;
  const entries = Object.entries(strategy.latest_metadata).slice(0, 6);
  if (entries.length === 0) return null;

  return (
    <div className="signal-meta">
      <strong>Latest Metadata</strong>
      <ul style={{ paddingLeft: "1rem", marginTop: "0.4rem" }}>
        {entries.map(([key, value]) => (
          <li key={key}>
            {key.replace(/_/g, " ")}: {typeof value === "number" ? value.toFixed(3) : String(value)}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function StrategyCard({ strategy }: StrategyCardProps) {
  return (
    <div className="panel strategy-card">
      <h3>{strategy.label}</h3>
      <p style={{ margin: 0, color: "#4b5563" }}>{strategy.description}</p>
      {renderConfidenceChart(strategy)}
      {renderMetadata(strategy)}
    </div>
  );
}
