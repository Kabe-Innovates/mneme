import { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle, CheckCircle2, RefreshCw, ChevronDown, ChevronUp,
  Clock, Database, Inbox, BookOpen, FileText, ListOrdered, BadgeCheck, FilePen,
} from "lucide-react";
import { clsx } from "clsx";
import type { EscalationTicket, KnowledgeItem } from "../types";
import { getTickets, resolveTicket, getKnowledgeIndex, getIngestionLog, approveKnowledgeArticle } from "../api";

const PRIORITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-red-500/15 text-red-400 border-red-500/20",
  URGENT:   "bg-orange-500/15 text-orange-400 border-orange-500/20",
  ROUTINE:  "bg-blue-500/15 text-blue-400 border-blue-500/20",
};

const STATUS_STYLES: Record<string, string> = {
  OPEN:     "bg-amber-500/15 text-amber-400",
  RESOLVED: "bg-green-500/15 text-green-400",
};

// ---------------------------------------------------------------------------
// Ticket row
// ---------------------------------------------------------------------------

function TicketRow({ ticket, onResolve }: { ticket: EscalationTicket; onResolve: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [notes, setNotes] = useState("");

  const ts = new Date(ticket.timestamp);
  const elapsed = Math.round((Date.now() - ts.getTime()) / 60000);
  const timeLabel = elapsed < 60 ? `${elapsed}m ago` : `${Math.round(elapsed / 60)}h ago`;

  const handleResolve = async () => {
    setResolving(true);
    try {
      await resolveTicket(ticket.ticket_id, notes);
      onResolve(ticket.ticket_id);
    } finally {
      setResolving(false);
    }
  };

  return (
    <div className={clsx(
      "rounded-lg border bg-dark-surface transition-shadow",
      ticket.status === "RESOLVED" ? "border-dark-border opacity-60" : "border-dark-border hover:shadow-lg hover:shadow-white/5"
    )}>
      <div className="flex items-start gap-3 p-3">
        <span className={clsx(
          "mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-xs font-bold",
          PRIORITY_STYLES[ticket.priority] || PRIORITY_STYLES.ROUTINE
        )}>
          {ticket.priority}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-semibold text-dark-muted">{ticket.ticket_id}</span>
            <span className={clsx("rounded px-1.5 py-0.5 text-xs font-medium", STATUS_STYLES[ticket.status])}>
              {ticket.status}
            </span>
            <span className="flex items-center gap-0.5 text-xs text-dark-muted">
              <Clock className="h-3 w-3" />{timeLabel}
            </span>
          </div>
          <p className="mt-1 truncate text-sm font-medium text-dark-text">{ticket.target_team}</p>
          <p className="truncate text-xs text-dark-muted">{ticket.summary}</p>
          <p className="mt-0.5 text-xs text-dark-muted">
            Initiated by: <span className="font-medium text-dark-text">{ticket.initiator_role}</span>
          </p>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 text-dark-muted hover:text-dark-text"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {expanded && (
        <div className="space-y-2 border-t border-dark-border px-3 pb-3 pt-2">
          {ticket.escalation_reason && (
            <div className="rounded bg-dark-hover p-2 text-xs text-dark-muted">
              <span className="font-semibold text-dark-text">Reason: </span>{ticket.escalation_reason}
            </div>
          )}

          {ticket.resolution_notes && (
            <div className="rounded bg-green-500/10 p-2 text-xs text-green-400">
              <span className="font-semibold">Resolution: </span>{ticket.resolution_notes}
            </div>
          )}

          {ticket.status === "OPEN" && (
            <div className="flex gap-2">
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add resolution notes (optional)…"
                className="flex-1 rounded border border-dark-border bg-dark-bg px-2 py-1.5 text-xs text-dark-text placeholder-dark-muted focus:border-brand-500 focus:outline-none"
              />
              <button
                onClick={handleResolve}
                disabled={resolving}
                className="flex items-center gap-1 rounded bg-green-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-600 disabled:opacity-50"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                {resolving ? "…" : "Resolve"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Knowledge Vault panel
// ---------------------------------------------------------------------------

function KnowledgeVault() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [view, setView] = useState<"index" | "log">("index");
  const [statusFilter, setStatusFilter] = useState<"" | "approved" | "draft">("");
  const [loading, setLoading] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);

  const loadIndex = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getKnowledgeIndex(statusFilter || undefined);
      setItems(data.items || []);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const loadLog = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getIngestionLog(100);
      setLog(data.log || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (view === "index") loadIndex();
    else loadLog();
  }, [view, loadIndex, loadLog]);

  const handleApprove = async (id: string) => {
    setApprovingId(id);
    try {
      await approveKnowledgeArticle(id);
      setItems((prev) =>
        prev.map((it) =>
          it.id === id ? { ...it, status: "approved" as const, indexed_at: new Date().toISOString() } : it
        )
      );
    } finally {
      setApprovingId(null);
    }
  };

  const draftCount = items.filter((i) => i.status === "draft").length;

  return (
    <div className="flex h-full flex-col">
      {/* Sub-header */}
      <div className="flex items-center justify-between border-b border-dark-border bg-dark-surface px-6 py-3">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-brand-400" />
          <div>
            <h2 className="font-display text-sm font-semibold tracking-tight text-dark-text">Living Knowledge Vault</h2>
            <p className="font-sans text-xs text-dark-muted">
              {items.length} items · {draftCount} pending approval
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Index / Log switcher */}
          <div className="flex rounded-lg border border-dark-border bg-dark-bg p-0.5 text-xs">
            <button
              onClick={() => setView("index")}
              className={clsx(
                "flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-colors",
                view === "index" ? "bg-dark-hover text-dark-text shadow-sm" : "text-dark-muted hover:text-dark-text"
              )}
            >
              <FileText className="h-3 w-3" /> Index
            </button>
            <button
              onClick={() => setView("log")}
              className={clsx(
                "flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-colors",
                view === "log" ? "bg-dark-hover text-dark-text shadow-sm" : "text-dark-muted hover:text-dark-text"
              )}
            >
              <ListOrdered className="h-3 w-3" /> Log
            </button>
          </div>

          {view === "index" && (
            <div className="flex rounded-lg border border-dark-border bg-dark-bg p-0.5 text-xs">
              {([["", "ALL"], ["approved", "Approved"], ["draft", "Draft"]] as const).map(([val, label]) => (
                <button
                  key={val}
                  onClick={() => setStatusFilter(val)}
                  className={clsx(
                    "rounded-md px-2 py-1 font-medium transition-colors",
                    statusFilter === val ? "bg-dark-hover text-dark-text shadow-sm" : "text-dark-muted hover:text-dark-text"
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          )}

          <button
            onClick={() => (view === "index" ? loadIndex() : loadLog())}
            disabled={loading}
            className="flex items-center gap-1 rounded-lg border border-dark-border bg-dark-bg px-2.5 py-1.5 text-xs text-dark-muted hover:bg-dark-hover"
          >
            <RefreshCw className={clsx("h-3.5 w-3.5", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
        {view === "log" ? (
          <div className="rounded-lg border border-dark-border bg-dark-bg p-3">
            {log.length === 0 ? (
              <p className="text-xs text-dark-muted">No log entries yet.</p>
            ) : (
              <ul className="space-y-0.5">
                {log.map((line, i) => (
                  <li key={i} className="font-mono text-xs leading-5 text-dark-muted">{line}</li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-dark-muted font-sans">
                <Inbox className="mb-3 h-10 w-10 text-dark-border" />
                <p className="font-display text-sm font-semibold text-dark-muted">No items found</p>
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  className={clsx(
                    "flex items-start gap-3 rounded-lg border bg-dark-surface px-3 py-2.5 transition-shadow hover:shadow-lg hover:shadow-white/5",
                    item.status === "draft" ? "border-amber-500/20" : "border-dark-border"
                  )}
                >
                  <span className={clsx(
                    "mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-xs font-semibold",
                    item.type === "article" ? "bg-brand-500/15 text-brand-400" : "bg-purple-500/15 text-purple-400"
                  )}>
                    {item.type}
                  </span>

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-dark-muted">{item.id}</span>
                      <span className={clsx(
                        "rounded px-1.5 py-0.5 text-xs font-medium",
                        item.status === "approved" ? "bg-green-500/15 text-green-400" : "bg-amber-500/15 text-amber-400"
                      )}>
                        {item.status}
                      </span>
                      <span className="text-xs text-dark-muted">{item.version}</span>
                    </div>
                    <p className="mt-0.5 truncate text-sm font-medium text-dark-text">{item.title || item.id}</p>
                    <p className="text-xs text-dark-muted">
                      {item.department} · hash <span className="font-mono">{item.content_hash}</span>
                      {item.indexed_at && ` · indexed ${new Date(item.indexed_at).toLocaleDateString()}`}
                    </p>
                  </div>

                  {item.status === "draft" && item.type === "article" && (
                    <button
                      onClick={() => handleApprove(item.id)}
                      disabled={approvingId === item.id}
                      className="flex shrink-0 items-center gap-1 rounded bg-brand-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                    >
                      {approvingId === item.id ? (
                        <RefreshCw className="h-3 w-3 animate-spin" />
                      ) : (
                        <BadgeCheck className="h-3 w-3" />
                      )}
                      Approve
                    </button>
                  )}
                  {item.status === "draft" && item.type === "workflow" && (
                    <span className="flex shrink-0 items-center gap-1 rounded bg-dark-hover px-2.5 py-1.5 text-xs text-dark-muted">
                      <FilePen className="h-3 w-3" /> Draft
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Operations Hub with inner tabs
// ---------------------------------------------------------------------------

type InnerTab = "escalations" | "knowledge";

export function SupervisorDashboard() {
  const [innerTab, setInnerTab] = useState<InnerTab>("escalations");
  const [tickets, setTickets] = useState<EscalationTicket[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<"ALL" | "OPEN" | "RESOLVED">("ALL");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTickets();
      setTickets(data.tickets || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (innerTab !== "escalations") return;
    load();
    const timer = setInterval(load, 30_000);
    return () => clearInterval(timer);
  }, [innerTab, load]);

  const handleResolve = (ticketId: string) => {
    setTickets((prev) =>
      prev.map((t) => (t.ticket_id === ticketId ? { ...t, status: "RESOLVED" as const } : t))
    );
  };

  const visible = tickets.filter((t) => filter === "ALL" || t.status === filter);
  const openCount = tickets.filter((t) => t.status === "OPEN").length;

  return (
    <div className="flex h-full flex-col bg-dark-bg">
      {/* Top nav */}
      <div className="flex items-end gap-1 border-b border-dark-border bg-dark-surface px-4 pt-3">
        <button
          onClick={() => setInnerTab("escalations")}
          className={clsx(
            "flex items-center gap-1.5 rounded-t-lg border-b-2 px-3 py-2 text-xs font-medium transition-colors",
            innerTab === "escalations"
              ? "border-orange-500 bg-orange-500/10 text-orange-400"
              : "border-transparent text-dark-muted hover:text-dark-text"
          )}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          Escalation Queue
          {openCount > 0 && (
            <span className="rounded-full bg-orange-500 px-1.5 py-0.5 text-xs font-bold leading-none text-white">
              {openCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setInnerTab("knowledge")}
          className={clsx(
            "flex items-center gap-1.5 rounded-t-lg border-b-2 px-3 py-2 text-xs font-medium transition-colors font-sans",
            innerTab === "knowledge"
              ? "border-brand-500 bg-brand-500/10 text-brand-400"
              : "border-transparent text-dark-muted hover:text-dark-text"
          )}
        >
          <BookOpen className="h-3.5 w-3.5" />
          Knowledge Vault
        </button>
      </div>

      {/* Inner tab content */}
      <div className="flex-1 overflow-hidden font-sans">
        {innerTab === "knowledge" ? (
          <KnowledgeVault />
        ) : (
          <div className="flex h-full flex-col">
            {/* Escalations header */}
            <div className="flex items-center justify-between border-b border-dark-border bg-dark-surface px-6 py-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-orange-400" />
                <div>
                  <h2 className="font-display text-sm font-semibold tracking-tight text-dark-text">Operations Hub</h2>
                  <p className="font-sans text-xs text-dark-muted">
                    {openCount} open ticket{openCount !== 1 ? "s" : ""} · {tickets.length} total
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex rounded-lg border border-dark-border bg-dark-bg p-0.5 text-xs">
                  {(["ALL", "OPEN", "RESOLVED"] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={clsx(
                        "rounded-md px-2.5 py-1 font-medium transition-colors",
                        filter === f ? "bg-dark-hover text-dark-text shadow-sm" : "text-dark-muted hover:text-dark-text"
                      )}
                    >
                      {f}
                    </button>
                  ))}
                </div>
                <button
                  onClick={load}
                  disabled={loading}
                  className="flex items-center gap-1 rounded-lg border border-dark-border bg-dark-bg px-2.5 py-1.5 text-xs text-dark-muted hover:bg-dark-hover"
                >
                  <RefreshCw className={clsx("h-3.5 w-3.5", loading && "animate-spin")} />
                  Refresh
                </button>
              </div>
            </div>

            {/* Ticket list */}
            <div className="flex-1 overflow-y-auto space-y-3 p-4 scrollbar-thin">
              {visible.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-dark-muted">
                  <CheckCircle2 className="mb-3 h-10 w-10 text-dark-border" />
                  <p className="text-sm font-medium">
                    {filter === "OPEN" ? "No open tickets" : "No tickets yet"}
                  </p>
                  <p className="mt-1 text-xs">
                    Escalations from the chat assistant will appear here
                  </p>
                </div>
              ) : (
                visible.map((ticket) => (
                  <TicketRow key={ticket.ticket_id} ticket={ticket} onResolve={handleResolve} />
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
