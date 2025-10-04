import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AggregatedSignal, PriceBar } from "../types";

interface PriceChartProps {
  data: PriceBar[];
  annotations?: {
    breakout?: number | null;
    handleHigh?: number | null;
    atrStop?: number | null;
  };
  latestAggregated?: AggregatedSignal | null;
}

const descriptorMap: Record<string, string> = {
  close: "Closing price reflects where the market settled each day.",
  fast_ema: "Fast EMA tracks near-term momentum; staying above it signals trend health.",
  slow_ema: "Slow EMA smooths longer-term direction; crossovers mark shifts.",
};

type TooltipPayload = {
  name: string;
  value: number;
  stroke?: string;
  dataKey: string;
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || payload.length === 0) return null;
  const entries = payload as TooltipPayload[];
  return (
    <div className="rounded-xl border border-slate-200 bg-white/95 px-4 py-3 text-sm shadow-lg shadow-slate-200/70">
      <p className="font-semibold text-slate-800">{label}</p>
      <ul className="mt-2 space-y-2">
        {entries.map((entry) => (
          <li key={entry.dataKey} className="space-y-1">
            <div className="flex items-center gap-2 text-slate-700">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: entry.stroke ?? "#0f172a" }}
              />
              <span className="font-medium">{entry.name}</span>
              <span className="text-xs text-slate-500">{entry.value.toFixed(2)}</span>
            </div>
            {descriptorMap[entry.dataKey] && (
              <p className="text-xs text-slate-500">{descriptorMap[entry.dataKey]}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PriceChart({ data, annotations, latestAggregated }: PriceChartProps) {
  const chartData = data.map((bar) => ({
    date: new Date(bar.date).toLocaleDateString(),
    close: bar.close,
    fast_ema: bar.fast_ema ?? null,
    slow_ema: bar.slow_ema ?? null,
  }));

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Price & Trend</h2>
          <p className="text-xs text-slate-500">
            Hover to reveal why each curve matters. Reference markers highlight breakout levels, handle highs, and ATR stops.
          </p>
        </div>
        {latestAggregated && (
          <div className="rounded-full bg-blue-50 px-4 py-1 text-xs font-medium text-blue-700">
            Latest aggregated: {latestAggregated.signal_type} · Confidence {latestAggregated.confidence.toFixed(2)}
          </div>
        )}
      </div>
      <div className="mt-4 h-[360px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 24, right: 24, bottom: 16, left: 0 }}>
            <defs>
              <linearGradient id="closeGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} minTickGap={28} />
            <YAxis domain={["dataMin", "dataMax"]} tick={{ fontSize: 12 }} width={70} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey="close" name="Close" stroke="#2563eb" fill="url(#closeGradient)" strokeWidth={2} />
            <Line type="monotone" dataKey="fast_ema" name="Fast EMA" stroke="#f97316" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line type="monotone" dataKey="slow_ema" name="Slow EMA" stroke="#7c3aed" dot={false} strokeWidth={2} isAnimationActive={false} />
            {annotations?.breakout && (
              <ReferenceLine
                y={annotations.breakout}
                stroke="#16a34a"
                strokeDasharray="4 4"
                label={{
                  value: "Breakout",
                  position: "right",
                  fill: "#16a34a",
                  fontSize: 11,
                }}
              />
            )}
            {annotations?.handleHigh && (
              <ReferenceLine
                y={annotations.handleHigh}
                stroke="#38bdf8"
                strokeDasharray="2 6"
                label={{
                  value: "Handle High",
                  position: "right",
                  fill: "#0ea5e9",
                  fontSize: 11,
                }}
              />
            )}
            {annotations?.atrStop && (
              <ReferenceLine
                y={annotations.atrStop}
                stroke="#ef4444"
                strokeDasharray="5 3"
                label={{
                  value: "ATR Stop",
                  position: "right",
                  fill: "#dc2626",
                  fontSize: 11,
                }}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 grid gap-3 text-xs text-slate-500 sm:grid-cols-3">
        <div>
          <span className="font-semibold text-slate-700">Breakout line:</span> Shows where price cleared resistance; revisit if price retests this zone.
        </div>
        <div>
          <span className="font-semibold text-slate-700">Handle high:</span> Staying above this suggests the handle remained constructive.
        </div>
        <div>
          <span className="font-semibold text-slate-700">ATR stop:</span> Dynamic risk guardrail derived from trend-following strategy.
        </div>
      </div>
    </section>
  );
}
