import type { AggregatedSignal, StrategyAnalysis } from "../types";

interface ScenarioCalloutsProps {
  aggregatedSignals: AggregatedSignal[];
  strategies: StrategyAnalysis[];
}

const toneStyles: Record<"positive" | "neutral" | "warning", string> = {
  positive: "border-emerald-200 bg-emerald-50 text-emerald-700",
  neutral: "border-slate-200 bg-slate-50 text-slate-600",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
};

export function ScenarioCallouts({ aggregatedSignals, strategies }: ScenarioCalloutsProps) {
  const latestAggregated = aggregatedSignals.at(-1) ?? null;
  const danZanger = strategies.find((strategy) => strategy.name === "dan_zanger_cup_handle");
  const livermore = strategies.find((strategy) => strategy.name === "livermore_breakout");

  const callouts: Array<{ title: string; body: string; tone: "positive" | "neutral" | "warning" }> = [];

  if (latestAggregated) {
    const tone = latestAggregated.confidence >= 0.7 ? "positive" : latestAggregated.confidence >= 0.5 ? "neutral" : "warning";
    callouts.push({
      title: `Consensus ${latestAggregated.signal_type} signal`,
      body: `Confidence ${latestAggregated.confidence.toFixed(2)} from strategies: ${(latestAggregated.metadata.strategies || []).join(", ")}.`,
      tone,
    });
  }

  if (danZanger?.latest_metadata) {
    const handlePullback = danZanger.latest_metadata.handle_pullback as number | undefined;
    if (handlePullback && (handlePullback < 0.05 || handlePullback > 0.15)) {
      callouts.push({
        title: "Handle depth outside ideal band",
        body: "Cup-handle pullback usually performs best between 5-15%. Watch price stability before committing capital.",
        tone: "warning",
      });
    }
  }

  if (livermore?.latest_metadata) {
    const rangePct = livermore.latest_metadata.range_pct as number | undefined;
    if (rangePct && rangePct <= 0.12) {
      callouts.push({
        title: "Consolidation tightening",
        body: "Livermore setup is compressing nicely; keep an eye on volume dry-up followed by a surge.",
        tone: "positive",
      });
    }
  }

  if (callouts.length === 0) {
    callouts.push({
      title: "Monitoring",
      body: "No major alerts yet. Track signal updates or adjust filters for additional confirmation.",
      tone: "neutral",
    });
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {callouts.map((callout) => (
        <div
          key={callout.title}
          className={`rounded-2xl border px-5 py-4 text-sm shadow-sm ${toneStyles[callout.tone]}`}
        >
          <h3 className="text-sm font-semibold">{callout.title}</h3>
          <p className="mt-1 text-xs leading-relaxed">{callout.body}</p>
        </div>
      ))}
    </div>
  );
}
