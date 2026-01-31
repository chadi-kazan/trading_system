import { useState, useEffect } from "react";
import type { JSX } from "react";
import {
  refreshRussell,
  refreshFundamentals,
  refreshAll,
  getAdminStatus,
  type AdminRefreshResponse,
  type AdminStatusResponse,
} from "../api";

const STORAGE_KEY = "admin_api_key";

export function AdminPage(): JSX.Element {
  const [apiKey, setApiKey] = useState<string>("");
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [status, setStatus] = useState<AdminStatusResponse | null>(null);
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [feedback, setFeedback] = useState<Record<string, { type: "success" | "error"; message: string }>>({});

  // Load API key from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      setApiKey(stored);
      setIsAuthenticated(true);
      loadStatus(stored);
    }
  }, []);

  const loadStatus = async (key: string) => {
    try {
      const statusData = await getAdminStatus(key);
      setStatus(statusData);
    } catch (err) {
      console.error("Failed to load admin status:", err);
      setStatus(null);
    }
  };

  const handleLogin = async () => {
    if (!apiKey.trim()) {
      setFeedback({
        login: { type: "error", message: "Please enter an API key" },
      });
      return;
    }

    setLoading({ ...loading, login: true });
    setFeedback({});

    try {
      // Verify the API key by fetching status
      await getAdminStatus(apiKey);
      localStorage.setItem(STORAGE_KEY, apiKey);
      setIsAuthenticated(true);
      await loadStatus(apiKey);
      setFeedback({
        login: { type: "success", message: "Authentication successful" },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Invalid API key";
      setFeedback({
        login: { type: "error", message },
      });
    } finally {
      setLoading({ ...loading, login: false });
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setApiKey("");
    setIsAuthenticated(false);
    setStatus(null);
    setFeedback({});
  };

  const handleRefresh = async (action: string, fn: () => Promise<AdminRefreshResponse>) => {
    setLoading({ ...loading, [action]: true });
    setFeedback({ ...feedback, [action]: undefined });

    try {
      const result = await fn();
      setFeedback({
        ...feedback,
        [action]: { type: "success", message: result.message || "Operation completed successfully" },
      });
      await loadStatus(apiKey);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Operation failed";
      setFeedback({
        ...feedback,
        [action]: { type: "error", message },
      });
    } finally {
      setLoading({ ...loading, [action]: false });
    }
  };

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return "Never";
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="mx-auto flex min-h-screen max-w-md items-center justify-center px-4">
        <div className="w-full space-y-6 rounded-xl bg-white p-8 shadow-lg">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-900">Admin Panel</h1>
            <p className="mt-2 text-sm text-slate-600">Enter your admin API key to continue</p>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="api-key" className="block text-sm font-medium text-slate-700">
                API Key
              </label>
              <input
                id="api-key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                placeholder="Enter your admin API key"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>

            <button
              type="button"
              onClick={handleLogin}
              disabled={loading.login}
              className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading.login ? "Authenticating..." : "Authenticate"}
            </button>

            {feedback.login && (
              <div
                className={`rounded-md border px-4 py-3 text-sm ${
                  feedback.login.type === "success"
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                    : "border-rose-200 bg-rose-50 text-rose-700"
                }`}
              >
                {feedback.login.message}
              </div>
            )}
          </div>

          <div className="border-t border-slate-200 pt-4">
            <p className="text-xs text-slate-500">
              Need help? Check the <code className="rounded bg-slate-100 px-1 py-0.5">docs/ADMIN_API.md</code> file for
              API key setup instructions.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Admin Panel</h1>
          <p className="mt-1 text-sm text-slate-600">Manage data refresh operations</p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
        >
          Logout
        </button>
      </header>

      {/* Status Section */}
      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Data Status</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Russell 2000 Constituents</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">{formatDate(status?.russell_last_updated ?? null)}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Fundamentals Cache</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {formatDate(status?.fundamentals_last_updated ?? null)}
            </p>
          </div>
        </div>
      </section>

      {/* Refresh Operations */}
      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Refresh Operations</h2>
        <div className="space-y-4">
          {/* Refresh Russell */}
          <RefreshCard
            title="Refresh Russell 2000 Constituents"
            description="Downloads the latest Russell 2000 constituent list from official sources."
            actionLabel="Refresh Russell"
            onAction={() => handleRefresh("russell", () => refreshRussell(apiKey))}
            loading={loading.russell}
            feedback={feedback.russell}
          />

          {/* Refresh Fundamentals */}
          <RefreshCard
            title="Refresh Fundamentals"
            description="Fetches fundamental data (earnings, P/E, market cap) from Alpha Vantage for Russell 2000 and S&P 500 symbols."
            actionLabel="Refresh Fundamentals"
            onAction={() => handleRefresh("fundamentals", () => refreshFundamentals(apiKey, true, true))}
            loading={loading.fundamentals}
            feedback={feedback.fundamentals}
          />

          {/* Refresh All */}
          <RefreshCard
            title="Refresh All Data"
            description="Runs both Russell and Fundamentals refresh operations sequentially."
            actionLabel="Refresh All"
            onAction={() => handleRefresh("all", () => refreshAll(apiKey))}
            loading={loading.all}
            feedback={feedback.all}
            variant="primary"
          />
        </div>
      </section>

      {/* Help Section */}
      <section className="rounded-xl border border-blue-200 bg-blue-50 p-6">
        <h3 className="text-sm font-semibold text-blue-900">💡 Tips</h3>
        <ul className="mt-3 space-y-2 text-sm text-blue-800">
          <li>• Refresh operations may take several minutes depending on data volume</li>
          <li>• Russell refresh should be done weekly (constituents don't change often)</li>
          <li>
            • Fundamentals refresh is rate-limited by Alpha Vantage (5 calls/min on free tier)
          </li>
          <li>• Use the CLI for scheduled automation: <code className="rounded bg-blue-100 px-1">python main.py schedule-fundamentals</code></li>
        </ul>
      </section>
    </div>
  );
}

type RefreshCardProps = {
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
  loading?: boolean;
  feedback?: { type: "success" | "error"; message: string };
  variant?: "default" | "primary";
};

function RefreshCard({
  title,
  description,
  actionLabel,
  onAction,
  loading = false,
  feedback,
  variant = "default",
}: RefreshCardProps): JSX.Element {
  const buttonClass =
    variant === "primary"
      ? "bg-blue-600 text-white hover:bg-blue-700"
      : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50";

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3 className="font-semibold text-slate-900">{title}</h3>
          <p className="mt-1 text-sm text-slate-600">{description}</p>
        </div>
        <button
          type="button"
          onClick={onAction}
          disabled={loading}
          className={`shrink-0 rounded-md px-4 py-2 text-sm font-medium shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${buttonClass}`}
        >
          {loading ? "Running..." : actionLabel}
        </button>
      </div>
      {feedback && (
        <div
          className={`mt-3 rounded-md border px-3 py-2 text-sm ${
            feedback.type === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-rose-200 bg-rose-50 text-rose-700"
          }`}
        >
          {feedback.message}
        </div>
      )}
    </div>
  );
}

export default AdminPage;
