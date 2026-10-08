import { useState } from "react";
import { Activity, Shield, Brain, MessageSquare, ClipboardList } from "lucide-react";
import { RoleSelector } from "./components/RoleSelector";
import { ChatWindow } from "./components/ChatWindow";

const SESSION_ID = crypto.randomUUID();

const STATS = [
  { label: "Outcomes", value: "4", desc: "ANSWER · GUIDE · ROUTE · REFUSE", icon: Brain },
  { label: "Compliance", value: "HIPAA", desc: "AWS Bedrock · NABH 5th", icon: Shield },
  { label: "Documents", value: "28", desc: "Articles + Workflows indexed", icon: ClipboardList },
  { label: "Roles", value: "15", desc: "Hospital operational roles", icon: Activity },
];

export default function App() {
  const [role, setRole] = useState("Front Office");

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
        {/* Header */}
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
            <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
              Live
            </span>
            <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-600">
              HIPAA Compliant
            </span>
          </div>
        </header>

        {/* Chat */}
        <div className="flex-1 overflow-hidden">
          <ChatWindow role={role} sessionId={SESSION_ID} />
        </div>
      </main>
    </div>
  );
}
