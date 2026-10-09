import { useState } from "react";
import { Layers, AlertCircle } from "lucide-react";
import { login } from "../api";

interface Props {
  onLogin: (name: string, role: string) => void;
}

export function LoginScreen({ onLogin }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = username.trim();
    if (!trimmed || !password) return;

    setLoading(true);
    setError("");

    try {
      const data = await login(trimmed, password);
      onLogin(data.name, data.role);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-dark-bg font-sans">
      <div className="w-full max-w-sm">
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl bg-dark-surface ring-1 ring-dark-border/60 shadow-2xl p-8 space-y-6"
        >
          {/* Logo */}
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-lg shadow-brand-500/20">
              <Layers className="h-7 w-7 text-white" />
            </div>
            <div className="text-center">
              <h1 className="font-display text-3xl font-bold text-dark-text tracking-tight">Mneme</h1>
              <p className="font-sans text-[11px] uppercase tracking-[0.22em] text-dark-muted font-medium mt-1">Healthcare Operations Copilot</p>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {error}
            </div>
          )}

          {/* Fields */}
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-dark-muted mb-1.5 uppercase tracking-wider text-[11px]">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. front_office"
                autoFocus
                className="w-full rounded-lg border border-dark-border bg-dark-bg px-3 py-2.5 text-sm text-dark-text placeholder-dark-muted/60 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-dark-muted mb-1.5 uppercase tracking-wider text-[11px]">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full rounded-lg border border-dark-border bg-dark-bg px-3 py-2.5 text-sm text-dark-text placeholder-dark-muted/60 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={!username.trim() || !password || loading}
            className="font-display w-full rounded-lg bg-brand-600 py-2.5 text-xs uppercase tracking-widest font-bold text-white hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md shadow-brand-600/20"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>

          {/* Demo credentials hint */}
          <p className="text-center text-xs text-dark-muted/60">
            Demo: <span className="font-mono text-dark-muted">front_office</span> / <span className="font-mono text-dark-muted">mneme2024</span>
          </p>
        </form>
      </div>
    </div>
  );
}
