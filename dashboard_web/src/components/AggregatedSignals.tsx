import { format } from "date-fns";
import type { AggregatedSignal } from "../types";

interface AggregatedSignalsProps {
  signals: AggregatedSignal[];
}

export function AggregatedSignals({ signals }: AggregatedSignalsProps) {
  if (signals.length === 0) {
    return (
      <div className="panel">
        <h2>Aggregated Signals</h2>
        <p style={{ color: "#6b7280" }}>No aggregated signals yet.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Aggregated Signals</h2>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {signals.map((signal, index) => (
          <li key={`${signal.date}-${index}`} style={{ padding: "0.6rem 0", borderBottom: "1px solid #e5e7eb" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600 }}>{signal.signal_type}</span>
              <span style={{ color: "#6b7280" }}>{format(new Date(signal.date), "PPpp")}</span>
            </div>
            <div style={{ fontSize: "0.9rem", color: "#4b5563" }}>Confidence: {signal.confidence.toFixed(2)}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
