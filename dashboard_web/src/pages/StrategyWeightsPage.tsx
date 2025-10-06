import { useStrategyMetrics } from "../hooks/useStrategyMetrics";
import { formatDisplayDate } from "../utils/date";

const NUMBER_FORMAT = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

function formatPercent(value?: number | null): string {
  if (value === undefined || value === null) {
    return "-";
  }
  return `${NUMBER_FORMAT.format(value * 100)}%`;
}

function formatDecimal(value?: number | null, fractionDigits = 2): string {
  if (value === undefined || value === null) {
    return "-";
  }
  return value.toFixed(fractionDigits);
}

export function StrategyWeightsPage() {
  const { metrics, loading, error, refresh } = useStrategyMetrics();

  return (
    <div className="mx-auto w-full max-w-6xl space-y-8 px-4 pb-20 pt-10">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">Strategy Health Dashboard</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            Rolling reliability metrics by strategy and market regime. Weights update as new trades are processed, so use this
            view to understand which playbooks are driving the blended "final score" today.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refresh()}
          disabled={loading}
          className="inline-flex items-center rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Refreshing..." : "Refresh data"}
        </button>
      </header>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-4 text-sm text-rose-700 shadow-sm">
          {error}
        </div>
      )}

      {metrics.length === 0 && !loading ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500 shadow-sm">
          No strategy metrics have been recorded yet. Once the analytics job publishes weights, this page will populate automatically.
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {metrics.map((entry) => (
            <article key={`${entry.strategy.id}-${entry.regime.slug}`} className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">{entry.strategy.label}</h2>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Regime: {entry.regime.name}</p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-500">Reliability weight</span>
                  <p className="text-2xl font-semibold text-slate-900">{formatPercent(entry.reliability_weight)}</p>
                </div>
              </div>

              <dl className="grid grid-cols-2 gap-3 text-sm text-slate-600">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Sample size</dt>
                  <dd className="font-semibold text-slate-900">{entry.sample_size}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Win rate</dt>
                  <dd className="font-semibold text-slate-900">{formatPercent(entry.win_rate)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Avg. excess return</dt>
                  <dd className="font-semibold text-slate-900">{formatDecimal(entry.avg_excess_return)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Volatility</dt>
                  <dd className="font-semibold text-slate-900">{formatDecimal(entry.volatility)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Max drawdown</dt>
                  <dd className="font-semibold text-slate-900">{formatDecimal(entry.max_drawdown)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Correlation penalty</dt>
                  <dd className="font-semibold text-slate-900">{formatPercent(entry.correlation_penalty)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Regime fit</dt>
                  <dd className="font-semibold text-slate-900">{formatPercent(entry.regime_fit)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Decay lambda</dt>
                  <dd className="font-semibold text-slate-900">{formatDecimal(entry.decay_lambda)}</dd>
                </div>
              </dl>

              <div className="rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3 text-xs text-slate-500">
                <p className="font-medium text-slate-700">Last sampled</p>
                <p>{formatDisplayDate(entry.last_sampled_at)}</p>
                <p className="mt-1 text-[11px] text-slate-400">Updated {formatDisplayDate(entry.updated_at)}</p>
              </div>

              {entry.history.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Recent observations</p>
                  <ul className="space-y-1 text-xs text-slate-500">
                    {entry.history.slice(0, 5).map((point) => (
                      <li key={point.observed_at} className="flex items-center justify-between rounded-lg bg-white/60 px-3 py-2 shadow-inner shadow-slate-200/40">
                        <span className="font-medium text-slate-700">{formatDisplayDate(point.observed_at)}</span>
                        <span>Weight {formatPercent(point.reliability_weight)}</span>
                      </li>
                    ))}
                  </ul>
                  {entry.history.length > 5 && (
                    <p className="text-[11px] text-slate-400">Showing 5 of {entry.history.length} records.</p>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
