import type { StrategyInfo } from "../types";

type ComparisonInputs = {
  primary: string;
  secondary: string;
};

type ComparisonRow = {
  strategy: string;
  label: string;
  primaryScore: number | null;
  secondaryScore: number | null;
  difference: number | null;
};

type ComparisonSummary = {
  primaryScore: number | null;
  secondaryScore: number | null;
};

type SignalComparisonPanelProps = {
  inputs: ComparisonInputs;
  onInputChange: (field: keyof ComparisonInputs, value: string) => void;
  onSwap: () => void;
  onCompare: () => void;
  loading: boolean;
  error: string | null;
  rows: ComparisonRow[];
  summary: ComparisonSummary | null;
  activePair: { primary: string; secondary: string } | null;
  strategyOrder: StrategyInfo[];
};

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(1)}%`;
}

function formatDifference(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  if (Math.abs(value) < 0.05) return "~0.0%";
  const rounded = value.toFixed(1);
  if (value > 0) return `+${rounded}%`;
  return `${rounded}%`;
}

export function SignalComparisonPanel({
  inputs,
  onInputChange,
  onSwap,
  onCompare,
  loading,
  error,
  rows,
  summary,
  activePair,
  strategyOrder,
}: SignalComparisonPanelProps) {
  const hasResults = activePair && rows.length > 0;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-sm shadow-slate-200/60">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Compare Signals</h3>
          <p className="text-sm text-slate-500">Review strategy scores for two tickers side-by-side.</p>
        </div>
        <button
          type="button"
          onClick={onSwap}
          className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:border-blue-200 hover:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-300/50"
        >
          Swap Symbols
        </button>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm text-slate-500">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Primary Symbol</span>
          <input
            value={inputs.primary}
            onChange={(event) => onInputChange("primary", event.target.value.toUpperCase())}
            placeholder="e.g. AAPL"
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 shadow-inner shadow-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            maxLength={8}
            autoCapitalize="characters"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-slate-500">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Comparison Symbol</span>
          <input
            value={inputs.secondary}
            onChange={(event) => onInputChange("secondary", event.target.value.toUpperCase())}
            placeholder="e.g. MSFT"
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 shadow-inner shadow-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            maxLength={8}
            autoCapitalize="characters"
          />
        </label>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onCompare}
          disabled={loading}
          className="inline-flex items-center rounded-full bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Comparing…" : "Compare Scores"}
        </button>
        {activePair ? (
          <span className="text-xs uppercase tracking-wide text-slate-400">
            Active comparison: {activePair.primary} vs {activePair.secondary}
          </span>
        ) : null}
      </div>

      {error ? (
        <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {hasResults ? (
        <div className="mt-6 overflow-x-auto">
          {summary ? (
            <div className="mb-4 grid gap-3 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-700 sm:grid-cols-3">
              <div>
                <span className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {activePair?.primary} Final Score
                </span>
                <span className="text-base font-semibold text-slate-900">{formatPercent(summary.primaryScore)}</span>
              </div>
              <div>
                <span className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {activePair?.secondary} Final Score
                </span>
                <span className="text-base font-semibold text-slate-900">{formatPercent(summary.secondaryScore)}</span>
              </div>
              <div>
                <span className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Spread (Primary - Comparison)
                </span>
                <span className="text-base font-semibold text-slate-900">
                  {formatDifference(
                    summary.primaryScore !== null && summary.secondaryScore !== null
                      ? summary.primaryScore - summary.secondaryScore
                      : null,
                  )}
                </span>
              </div>
            </div>
          ) : null}

          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">Strategy</th>
                <th className="py-2 pr-4">{activePair?.primary ?? "Primary"}</th>
                <th className="py-2 pr-4">{activePair?.secondary ?? "Comparison"}</th>
                <th className="py-2 pr-4">Spread</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {strategyOrder.map((meta) => {
                const row = rows.find((item) => item.strategy === meta.name);
                const label = meta.label ?? meta.name;
                return (
                  <tr key={meta.name}>
                    <td className="py-2 pr-4 font-medium text-slate-700">{label}</td>
                    <td className="py-2 pr-4 text-slate-600">{formatPercent(row?.primaryScore ?? null)}</td>
                    <td className="py-2 pr-4 text-slate-600">{formatPercent(row?.secondaryScore ?? null)}</td>
                    <td className="py-2 pr-4 text-slate-700">{formatDifference(row?.difference ?? null)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export default SignalComparisonPanel;
