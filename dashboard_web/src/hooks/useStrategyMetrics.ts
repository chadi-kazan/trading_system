import { useCallback, useEffect, useState } from "react";

import { fetchStrategyMetrics } from "../api";
import type { StrategyMetricSummary } from "../types";

export function useStrategyMetrics(includeHistory = true) {
  const [metrics, setMetrics] = useState<StrategyMetricSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStrategyMetrics(includeHistory);
      setMetrics(data);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to load strategy metrics");
    } finally {
      setLoading(false);
    }
  }, [includeHistory]);

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [refresh]);

  return {
    metrics,
    loading,
    error,
    refresh,
  };
}
