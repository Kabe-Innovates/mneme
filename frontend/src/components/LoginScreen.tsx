import { useState } from "react";
import { Layers } from "lucide-react";
import { ROLES } from "../constants";

interface Props {
  onLogin: (name: string, role: string) => void;
}

export function LoginScreen({ onLogin }: Props) {
  const [name, setName] = useState("");
  const [role, setRole] = useState<string>(ROLES[0]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    onLogin(trimmed, role);
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

          {/* Fields */}
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-dark-muted mb-1.5 uppercase tracking-wider text-[11px]">
                Your Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your name"
                autoFocus
                className="w-full rounded-lg border border-dark-border bg-dark-bg px-3 py-2.5 text-sm text-dark-text placeholder-dark-muted/60 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-dark-muted mb-1.5 uppercase tracking-wider text-[11px]">
                Department / Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-lg border border-dark-border bg-dark-bg px-3 py-2.5 text-sm text-dark-text focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 font-medium"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={!name.trim()}
            className="font-display w-full rounded-lg bg-brand-600 py-2.5 text-xs uppercase tracking-widest font-bold text-white hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md shadow-brand-600/20"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
