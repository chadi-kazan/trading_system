import { useState } from "react";
import type { JSX } from "react";
import { useAuth } from "../hooks/useAuth";

export function LoginPage(): JSX.Element {
  const { login } = useAuth();
  const [accessKey, setAccessKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!accessKey.trim()) {
      setError("Please enter an access key");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Verify the access key by making a test request
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/strategies`, {
        headers: {
          "X-App-Access-Key": accessKey,
        },
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          throw new Error("Invalid access key");
        } else if (response.status === 503) {
          throw new Error("Application is not configured for authentication");
        } else {
          throw new Error("Unable to verify access key");
        }
      }

      // Access key is valid
      login(accessKey);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 px-4">
      <div className="w-full max-w-md space-y-8 rounded-2xl bg-white p-10 shadow-2xl">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900">Welcome</h1>
          <h2 className="mt-2 text-xl font-semibold text-slate-700">Small-Cap Growth Toolkit</h2>
          <p className="mt-3 text-sm text-slate-600">
            Enter your access key to continue
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div>
            <label htmlFor="access-key" className="block text-sm font-medium text-slate-700">
              Access Key
            </label>
            <input
              id="access-key"
              type="password"
              value={accessKey}
              onChange={(e) => {
                setAccessKey(e.target.value);
                setError(null);
              }}
              placeholder="Enter your access key"
              className="mt-2 w-full rounded-lg border border-slate-300 px-4 py-3 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              disabled={isLoading}
            />
          </div>

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-3 font-semibold text-white shadow-lg transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? "Authenticating..." : "Sign In"}
          </button>
        </form>

        <div className="border-t border-slate-200 pt-6">
          <p className="text-center text-xs text-slate-500">
            Need an access key? Contact your administrator.
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
