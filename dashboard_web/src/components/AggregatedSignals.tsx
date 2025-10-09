import type { AggregatedSignal } from "../types";
import { formatDisplayDate } from "../utils/date";
import { Tooltip, InfoIcon } from "./Tooltip";


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
          const confidencePercent = Math.round(signal.confidence * 100);
          const confidenceTone = signal.confidence >= 0.7 ? "text-emerald-600" : signal.confidence >= 0.5 ? "text-slate-600" : "text-amber-600";
          const metadataEntries = Object.entries(signal.metadata ?? {}).filter(([key]) => key !== "strategies");
          const formatMetaValue = (value: unknown): string => {
            if (value === null || value === undefined) return "—";
            if (Array.isArray(value)) {
              return value
                .map((item) => (typeof item === "string" ? item.replace(/_/g, " ") : String(item)))
                .join(", ");
            }
            if (value instanceof Date) return formatDisplayDate(value);
            if (typeof value === "object") return JSON.stringify(value);
            return String(value);
          };
          const tooltipContent = (
            <div className="space-y-3">
              <div>
                <p className="text-sm font-semibold text-slate-100">{signal.signal_type}</p>
                <p className="mt-1 text-xs text-slate-300">Generated {formattedDate}</p>
              </div>
              <p className="text-xs text-slate-300">
                <span className="font-semibold text-slate-100">Confidence:</span> {confidencePercent}%
              </p>
              {strategies ? (
                <p className="text-xs text-slate-300">
                  <span className="font-semibold text-slate-100">Strategies:</span> {strategies}
                </p>
              ) : null}
              {metadataEntries.length > 0 ? (
                <ul className="space-y-1 text-xs text-slate-300">
                  {metadataEntries.map(([key, value]) => (
                    <li key={key}>
                      <span className="font-semibold text-slate-100">{key.replace(/_/g, " ")}:</span>{" "}
                      {formatMetaValue(value)}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          );

          return (
            <li
              key={`${signal.date}-${index}`}
              className="flex flex-col gap-2 rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3 text-sm text-slate-700"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold uppercase tracking-wide text-slate-800">
                    {signal.signal_type}
                  </span>
                  <Tooltip content={tooltipContent}>
                    <button
                      type="button"
                      aria-label={`Aggregated signal details for ${signal.signal_type}`}
                      className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
                    >
                      <InfoIcon />
                    </button>
                  </Tooltip>
                </div>
                <span className="text-xs font-medium text-slate-500">{formattedDate}</span>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Confidence</span>
                <span className={`font-semibold ${confidenceTone}`}>{confidencePercent}%</span>
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
