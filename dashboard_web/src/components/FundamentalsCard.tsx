import { Tooltip, InfoIcon } from "./Tooltip";
import { formatDisplayDate } from "../utils/date";
import type { FundamentalSnapshot } from "../types";

function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${Math.round(value * 100)}%`;
}

function resolveInterpretation(text: string | null | undefined): string {
  if (!text) return "No recent data.";
  return text;
}

type FundamentalsCardProps = {
  fundamentals?: FundamentalSnapshot | null;
};

export function FundamentalsCard({ fundamentals }: FundamentalsCardProps) {
  const metrics = fundamentals?.metrics ?? [];

  if (!fundamentals || metrics.length === 0) {
    return (
      <article className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm shadow-slate-200/60">
        <h3 className="text-base font-semibold text-slate-900">Fundamentals</h3>
        <p className="mt-2 text-xs">No fundamentals available for this symbol yet.</p>
      </article>
    );
  }

  const updatedAt = fundamentals.updated_at ? formatDisplayDate(new Date(fundamentals.updated_at)) : null;

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/60">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Fundamentals</h3>
          {fundamentals.notes ? <p className="mt-1 text-xs text-slate-500">{fundamentals.notes}</p> : null}
        </div>
        <div className="text-right">
          <span className="text-xs uppercase tracking-wide text-slate-400">Composite score</span>
          <p className="text-xl font-semibold text-slate-900">{formatScore(fundamentals.score ?? null)}</p>
          {updatedAt ? <p className="text-[11px] text-slate-400">Updated {updatedAt}</p> : null}
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {metrics.map((metric) => {
          const tooltipContent = (
            <div className="space-y-1 text-left">
              <p className="text-xs font-semibold text-slate-100">{metric.label}</p>
              {metric.ideal ? <p className="text-[11px] text-slate-300">Ideal: {metric.ideal}</p> : null}
              <p className="text-[11px] text-slate-300">{resolveInterpretation(metric.interpretation)}</p>
            </div>
          );

          return (
            <div
              key={metric.key}
              className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50/50 px-3 py-2"
            >
              <div className="flex items-center gap-1 text-xs font-medium text-slate-500">
                <span className="uppercase tracking-wide text-slate-400">{metric.label}</span>
                <Tooltip content={tooltipContent}>
                  <button
                    type="button"
                    className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-400 transition hover:text-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400/40"
                    aria-label={`More information about ${metric.label}`}
                  >
                    <InfoIcon />
                  </button>
                </Tooltip>
              </div>
              <span className="text-sm font-semibold text-slate-800">{metric.display ?? "—"}</span>
            </div>
          );
        })}
      </div>
    </article>
  );
}

