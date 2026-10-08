import { useState } from "react";
import { Activity, Shield, Brain, MessageSquare, ClipboardList, AlertTriangle, Zap, ZapOff } from "lucide-react";
import { clsx } from "clsx";
import { RoleSelector } from "./components/RoleSelector";
import { ChatWindow } from "./components/ChatWindow";
import { SupervisorDashboard } from "./components/SupervisorDashboard";
import { toggleLlm } from "./api";

const SESSION_ID = crypto.randomUUID();

const STATS = [
  { label: "Outcomes", value: "4", desc: "ANSWER · GUIDE · ROUTE · REFUSE", icon: Brain },
  { label: "Compliance", value: "HIPAA", desc: "AWS Bedrock · NABH 5th", icon: Shield },
  { label: "Documents", value: "27", desc: "Articles + Workflows indexed", icon: ClipboardList },
  { label: "Roles", value: "15", desc: "Hospital operational roles", icon: Activity },
];

type Tab = "chat" | "supervisor";

export default function App() {
  const [role, setRole] = useState("Front Office");
  const [tab, setTab] = useState<Tab>("chat");
  const [llmOn, setLlmOn] = useState(true);

  const handleLlmToggle = async () => {
    const next = !llmOn;
    setLlmOn(next);
    await toggleLlm(next).catch(() => setLlmOn(llmOn));
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white shadow-sm">
        {/* Logo */}
        <div className="border-b border-slate-100 px-4 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-800">Mneme</h1>
              <p className="text-xs text-slate-400">Healthcare Operations AI</p>
            </div>
          </div>
        </div>

        {/* Role selector */}
        <div className="border-b border-slate-100 py-3">
          <RoleSelector role={role} onChange={setRole} />
        </div>

        {/* Nav tabs */}
        <div className="border-b border-slate-100 p-2 space-y-1">
          <button
            onClick={() => setTab("chat")}
            className={clsx(
              "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors",
              tab === "chat"
                ? "bg-blue-50 text-blue-700"
                : "text-slate-500 hover:bg-slate-50 hover:text-slate-700"
            )}
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Operations Assistant
          </button>
          <button
            onClick={() => setTab("supervisor")}
            className={clsx(
              "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors",
              tab === "supervisor"
                ? "bg-orange-50 text-orange-700"
                : "text-slate-500 hover:bg-slate-50 hover:text-slate-700"
            )}
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            Supervisor Queue
          </button>
        </div>

        {/* Stats */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          <p className="px-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            System Status
          </p>
          {STATS.map(({ label, value, desc, icon: Icon }) => (
            <div
              key={label}
              className="flex items-center gap-2.5 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2"
            >
              <Icon className="h-4 w-4 shrink-0 text-blue-500" />
              <div className="min-w-0">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-sm font-bold text-slate-800">{value}</span>
                  <span className="text-xs text-slate-500">{label}</span>
                </div>
                <p className="truncate text-xs text-slate-400">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-100 px-4 py-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Shield className="h-3 w-3" />
            <span>Powered by AWS Bedrock</span>
          </div>
          <p className="mt-0.5 text-xs text-slate-300">Claude 3.5 Sonnet · Titan Embed V2</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {tab === "chat" ? (
          <>
            <header className="flex items-center justify-between border-b border-slate-100 bg-white px-6 py-3 shadow-sm">
              <div className="flex items-center gap-3">
                <MessageSquare className="h-5 w-5 text-blue-500" />
                <div>
                  <h2 className="text-sm font-semibold text-slate-800">Operations Assistant</h2>
                  <p className="text-xs text-slate-400">
                    Session · Role: <span className="font-medium text-slate-600">{role}</span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleLlmToggle}
                  title={llmOn ? "Click to disable LLM (demo template mode)" : "Click to re-enable LLM"}
                  className={clsx(
                    "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
                    llmOn
                      ? "bg-green-100 text-green-700 hover:bg-green-200"
                      : "bg-amber-100 text-amber-700 hover:bg-amber-200"
                  )}
                >
                  {llmOn ? <Zap className="h-3 w-3" /> : <ZapOff className="h-3 w-3" />}
                  {llmOn ? "LLM Live" : "Template Mode"}
                </button>
                <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-600">
                  HIPAA Compliant
                </span>
              </div>
            </header>
            <div className="flex-1 overflow-hidden">
              <ChatWindow role={role} sessionId={SESSION_ID} />
            </div>
          </>
        ) : (
          <SupervisorDashboard />
        )}
      </main>
    </div>
  );
}
