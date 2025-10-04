import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PriceBar } from "../types";

interface PriceChartProps {
  data: PriceBar[];
}

const tooltipFormatter = (value: number | string | Array<number | string>) => {
  if (Array.isArray(value)) return value;
  if (typeof value === "number") return value.toFixed(2);
  return value;
};

export function PriceChart({ data }: PriceChartProps) {
  const chartData = data.map((bar) => ({
    date: new Date(bar.date).toLocaleDateString(),
    close: bar.close,
    fast_ema: bar.fast_ema ?? null,
    slow_ema: bar.slow_ema ?? null,
  }));

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">Price & Trend</h2>
        <span className="text-xs font-medium text-slate-400">Close with EMA overlays</span>
      </div>
      <div className="mt-4 h-[340px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
            <defs>
              <linearGradient id="closeGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="date" minTickGap={32} tick={{ fontSize: 12 }} />
            <YAxis domain={["dataMin", "dataMax"]} tick={{ fontSize: 12 }} width={60} />
            <Tooltip formatter={tooltipFormatter} labelClassName="text-sm font-semibold" />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area type="monotone" dataKey="close" name="Close" stroke="#2563eb" fill="url(#closeGradient)" strokeWidth={2} />
            <Line type="monotone" dataKey="fast_ema" name="Fast EMA" stroke="#f97316" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line type="monotone" dataKey="slow_ema" name="Slow EMA" stroke="#7c3aed" dot={false} strokeWidth={2} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
