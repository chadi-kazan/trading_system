import type { AggregatedSignal } from "../types";
import { formatDisplayDate } from "../utils/date";

interface AggregatedSignalsProps {
  signals: AggregatedSignal[];
}

function renderStrategyList(metadata: Record<string, unknown>): string | null {
  const strategies = Array.isArray(metadata?.strategies) ? metadata.strategies : [];
  if (!strategies.length) return null;
  return strategies
    .map((name: unknown) => (typeof name === "string" ? name.replace(/_/g, " ") : ""))
    .filter(Boolean)
    .join(", ");
}

export function AggregatedSignals({ signals }: AggregatedSignalsProps) {
  if (signals.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
        <h2 className="text-base font-semibold text-slate-900">Aggregated Signals</h2>
        <p className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center text-sm text-slate-500">
          No aggregated signals yet. When multiple strategies align, consensus entries will surface here with confidence scores.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <h2 className="text-base font-semibold text-slate-900">Aggregated Signals</h2>
      <ul className="mt-4 space-y-3">
        {signals.map((signal, index) => {
          const formattedDate = formatDisplayDate(signal.date);
          const strategies = renderStrategyList(signal.metadata);
          const confidenceTone = signal.confidence >= 0.7 ? "text-emerald-600" : signal.confidence >= 0.5 ? "text-slate-600" : "text-amber-600";

          return (
            <li
              key={`${signal.date}-${index}`}
              className="flex flex-col gap-2 rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3 text-sm text-slate-700"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold uppercase tracking-wide text-slate-800">
                  {signal.signal_type}
                </span>
                <span className="text-xs font-medium text-slate-500">{formattedDate}</span>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Confidence</span>
                <span className={`font-semibold ${confidenceTone}`}>{signal.confidence.toFixed(2)}</span>
              </div>
              {strategies && (
                <div className="text-xs text-slate-500">
                  Strategies: <span className="font-medium text-slate-600">{strategies}</span>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
