import { useState } from "react";
import { Layers, MessageSquare, LayoutDashboard, Settings, Zap, ZapOff, Shield, LogOut } from "lucide-react";
import { clsx } from "clsx";
import { ChatWindow } from "./components/ChatWindow";
import { SupervisorDashboard } from "./components/SupervisorDashboard";
import { LoginScreen } from "./components/LoginScreen";
import { toggleLlm } from "./api";

const SESSION_ID = crypto.randomUUID();

type View = "chat" | "ops-hub";

interface User {
  name: string;
  role: string;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [view, setView] = useState<View>("chat");
  const [llmOn, setLlmOn] = useState(true);
  const [profileOpen, setProfileOpen] = useState(false);

  if (!user) {
    return <LoginScreen onLogin={(name, role) => setUser({ name, role })} />;
  }

  const handleLlmToggle = async () => {
    const next = !llmOn;
    setLlmOn(next);
    await toggleLlm(next).catch(() => setLlmOn(llmOn));
  };

  const initial = user.name.charAt(0).toUpperCase();

  return (
    <div className="flex h-screen overflow-hidden bg-dark-bg font-sans">
      {/* Nav Rail */}
      <aside className="flex w-16 shrink-0 flex-col items-center border-r border-dark-border bg-dark-surface py-4">
        {/* Brand icon */}
        <div className="mb-6 flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-md shadow-brand-500/20">
          <Layers className="h-5 w-5 text-white" />
        </div>

        {/* Nav items */}
        <div className="flex flex-1 flex-col items-center gap-2">
          <button
            onClick={() => setView("chat")}
            title="Operations Assistant"
            className={clsx(
              "flex h-10 w-10 items-center justify-center rounded-xl transition-colors",
              view === "chat"
                ? "bg-dark-hover text-brand-400"
                : "text-dark-muted hover:bg-dark-hover hover:text-dark-text"
            )}
          >
            <MessageSquare className="h-5 w-5" />
          </button>
          <button
            onClick={() => setView("ops-hub")}
            title="Operations Hub"
            className={clsx(
              "flex h-10 w-10 items-center justify-center rounded-xl transition-colors",
              view === "ops-hub"
                ? "bg-dark-hover text-orange-400"
                : "text-dark-muted hover:bg-dark-hover hover:text-dark-text"
            )}
          >
            <LayoutDashboard className="h-5 w-5" />
          </button>
        </div>

        {/* Bottom items */}
        <div className="mt-auto flex flex-col items-center gap-3">
          <button
            title="Settings"
            className="flex h-10 w-10 items-center justify-center rounded-xl text-dark-muted hover:bg-dark-hover hover:text-dark-text transition-colors"
          >
            <Settings className="h-5 w-5" />
          </button>
          <button
            onClick={() => setProfileOpen(!profileOpen)}
            title={user.name}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-700 text-sm font-semibold text-white hover:bg-brand-600 transition-colors"
          >
            {initial}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {view === "chat" ? (
          <ChatWindow
            username={user.name}
            role={user.role}
            sessionId={SESSION_ID}
            onViewQueue={() => setView("ops-hub")}
          />
        ) : (
          <SupervisorDashboard />
        )}
      </main>

      {/* Profile panel */}
      {profileOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setProfileOpen(false)} />
          <div className="fixed bottom-4 left-16 z-50 w-72 space-y-3 rounded-xl bg-dark-surface p-4 shadow-2xl ring-1 ring-dark-border">
            {/* User info */}
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-700 text-sm font-semibold text-white">
                {initial}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-dark-text">{user.name}</p>
                <p className="truncate text-xs text-dark-muted">{user.role}</p>
              </div>
            </div>

            <div className="border-t border-dark-border" />

            {/* LLM toggle */}
            <button
              onClick={handleLlmToggle}
              className={clsx(
                "flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                llmOn
                  ? "border-green-800 bg-green-900/40 text-green-400 hover:bg-green-900/60"
                  : "border-amber-800 bg-amber-900/40 text-amber-400 hover:bg-amber-900/60"
              )}
            >
              {llmOn ? <Zap className="h-3.5 w-3.5" /> : <ZapOff className="h-3.5 w-3.5" />}
              {llmOn ? "LLM Live — click to use template mode" : "Template Mode — click to enable LLM"}
            </button>

            {/* HIPAA badge */}
            <div className="flex items-center gap-2 rounded-lg border border-brand-500/20 bg-brand-500/10 px-3 py-2">
              <Shield className="h-3.5 w-3.5 text-brand-400" />
              <span className="text-xs font-medium text-brand-400">HIPAA Compliant Session</span>
            </div>

            <div className="border-t border-dark-border" />

            {/* Sign out */}
            <button
              onClick={() => {
                setProfileOpen(false);
                setUser(null);
              }}
              className="flex w-full items-center gap-2 px-1 py-1 text-xs text-dark-muted hover:text-red-400 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
