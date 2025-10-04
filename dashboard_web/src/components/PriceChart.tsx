import { ResponsiveContainer, AreaChart, Area, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from "recharts";
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
    <div className="panel price-chart">
      <h2>Price & Trend</h2>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 16, right: 16, bottom: 8, left: 0 }}>
          <defs>
            <linearGradient id="closeGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="date" hide minTickGap={32} />
          <YAxis domain={["dataMin", "dataMax"]} width={60} />
          <Tooltip formatter={tooltipFormatter} />
          <Legend />
          <Area type="monotone" dataKey="close" name="Close" stroke="#2563eb" fillOpacity={1} fill="url(#closeGradient)" />
          <Line type="monotone" dataKey="fast_ema" name="Fast EMA" stroke="#f97316" dot={false} strokeWidth={2} isAnimationActive={false} />
          <Line type="monotone" dataKey="slow_ema" name="Slow EMA" stroke="#7c3aed" dot={false} strokeWidth={2} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
