import { format } from "date-fns";
import type { AggregatedSignal } from "../types";

interface AggregatedSignalsProps {
  signals: AggregatedSignal[];
}

export function AggregatedSignals({ signals }: AggregatedSignalsProps) {
  if (signals.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
        <h2 className="text-base font-semibold text-slate-900">Aggregated Signals</h2>
        <p className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center text-sm text-slate-500">
          No aggregated signals yet. Trigger strategy alignment to see consensus entries.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <h2 className="text-base font-semibold text-slate-900">Aggregated Signals</h2>
      <ul className="mt-4 space-y-3">
        {signals.map((signal, index) => (
          <li
            key={`${signal.date}-${index}`}
            className="flex flex-col gap-1 rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3 text-sm text-slate-700"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold uppercase tracking-wide text-slate-800">
                {signal.signal_type}
              </span>
              <span className="text-xs font-medium text-slate-500">
                {format(new Date(signal.date), "PPpp")}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Confidence</span>
              <span className="font-semibold text-slate-700">{signal.confidence.toFixed(2)}</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
