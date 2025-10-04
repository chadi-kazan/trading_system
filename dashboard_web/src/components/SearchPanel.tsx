import { useState } from "react";
import type { SymbolSearchResult } from "../types";

interface SearchPanelProps {
  onSearch: (query: string) => Promise<void>;
  results: SymbolSearchResult[];
  onSelectSymbol: (symbol: SymbolSearchResult) => void;
  loading: boolean;
  lastQuery: string;
}

export function SearchPanel({ onSearch, results, onSelectSymbol, loading, lastQuery }: SearchPanelProps) {
  const [input, setInput] = useState(lastQuery);

  return (
    <div className="panel">
      <h2>Symbol Search</h2>
      <p>Search any ticker; results will include Alpha Vantage matches plus local universe fallbacks.</p>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          if (!input.trim()) return;
          await onSearch(input.trim());
        }}
      >
        <label htmlFor="symbol-input" style={{ display: "block", fontWeight: 600, marginBottom: "0.5rem" }}>
          Symbol or Keyword
        </label>
        <input
          id="symbol-input"
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="e.g. PLUG, software"
          style={{
            width: "100%",
            padding: "0.6rem 0.75rem",
            borderRadius: "8px",
            border: "1px solid #d1d5db",
            fontSize: "1rem",
          }}
        />
        <div className="refresh-row">
          <button type="submit" className="primary" disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      <h3 style={{ marginTop: "1.5rem", marginBottom: "0.5rem" }}>Matches</h3>
      <ul className="results-list">
        {results.length === 0 && <li style={{ color: "#6b7280" }}>No matches yet</li>}
        {results.map((item) => (
          <li key={`${item.symbol}-${item.region}`} onClick={() => onSelectSymbol(item)}>
            <div style={{ fontWeight: 600 }}>{item.symbol}</div>
            <div style={{ fontSize: "0.85rem", color: "#6b7280" }}>
              {item.name || "Unnamed"} · {item.region} {item.currency ? `· ${item.currency}` : ""}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
