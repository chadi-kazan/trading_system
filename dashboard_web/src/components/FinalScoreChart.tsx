import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export type StrategyScore = {
  name: string;
  label: string;
  value: number;
};

interface FinalScoreChartProps {
  scores: StrategyScore[];
  average: number;
}

const COLORS = ["#2563eb", "#f97316", "#22c55e", "#7c3aed", "#0ea5e9", "#facc15"];

const tooltipFormatter = (value: number | string) => {
  if (typeof value === "number") {
    return `${value.toFixed(1)}%`;
  }
  return value;
};

export function FinalScoreChart({ scores, average }: FinalScoreChartProps) {
  const total = scores.reduce((sum, item) => sum + item.value, 0);
  const hasData = total > 0;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Final Score</h2>
          <p className="text-xs text-slate-500">
            Weighted blend of the latest signals from each strategy. Use it as a quick gauge, not a substitute for the
            individual playbooks.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[240px,1fr]">
        <div className="relative h-56">
          {hasData ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={scores}
                  dataKey="value"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius="60%"
                  outerRadius="100%"
                  paddingAngle={2}
                >
                  {scores.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={tooltipFormatter} labelClassName="text-sm font-semibold" />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              No recent signals to score yet.
            </div>
          )}
          {hasData && (
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="text-xs uppercase tracking-wide text-slate-400">Average</span>
              <span className="text-3xl font-semibold text-slate-900">{average.toFixed(0)}%</span>
            </div>
          )}
        </div>
        <div className="space-y-3 text-sm text-slate-600">
          {scores.map((score, index) => (
            <div key={score.name} className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/70 px-4 py-2">
              <div className="flex items-center gap-2">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <span className="font-medium text-slate-800">{score.label}</span>
              </div>
              <span className="font-semibold text-slate-900">{score.value.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

