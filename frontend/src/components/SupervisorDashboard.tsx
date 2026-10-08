import { useState, useEffect, useCallback } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw, ChevronDown, ChevronUp, Clock } from "lucide-react";
import { clsx } from "clsx";
import type { EscalationTicket } from "../types";
import { getTickets, resolveTicket } from "../api";

const PRIORITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
  URGENT: "bg-orange-100 text-orange-700 border-orange-200",
  ROUTINE: "bg-blue-100 text-blue-700 border-blue-200",
};

const STATUS_STYLES: Record<string, string> = {
  OPEN: "bg-amber-100 text-amber-700",
  RESOLVED: "bg-green-100 text-green-700",
};

function TicketRow({ ticket, onResolve }: { ticket: EscalationTicket; onResolve: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [notes, setNotes] = useState("");

  const ts = new Date(ticket.timestamp);
  const elapsed = Math.round((Date.now() - ts.getTime()) / 60000);
  const timeLabel = elapsed < 60
    ? `${elapsed}m ago`
    : `${Math.round(elapsed / 60)}h ago`;

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
      "rounded-lg border bg-white shadow-sm",
      ticket.status === "RESOLVED" ? "border-slate-100 opacity-70" : "border-slate-200"
    )}>
      <div className="flex items-start gap-3 p-3">
        {/* Priority badge */}
        <span className={clsx(
          "mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-xs font-bold",
          PRIORITY_STYLES[ticket.priority] || PRIORITY_STYLES.ROUTINE
        )}>
          {ticket.priority}
        </span>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-semibold text-slate-500">{ticket.ticket_id}</span>
            <span className={clsx("rounded px-1.5 py-0.5 text-xs font-medium", STATUS_STYLES[ticket.status])}>
              {ticket.status}
            </span>
            <span className="flex items-center gap-0.5 text-xs text-slate-400">
              <Clock className="h-3 w-3" />{timeLabel}
            </span>
          </div>
          <p className="mt-1 text-sm font-medium text-slate-700 truncate">{ticket.target_team}</p>
          <p className="text-xs text-slate-500 truncate">{ticket.summary}</p>
          <p className="mt-0.5 text-xs text-slate-400">
            Initiated by: <span className="font-medium">{ticket.initiator_role}</span>
          </p>
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 text-slate-400 hover:text-slate-600"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-slate-100 px-3 pb-3 pt-2 space-y-2">
          {ticket.escalation_reason && (
            <div className="rounded bg-slate-50 p-2 text-xs text-slate-600">
              <span className="font-semibold">Reason: </span>{ticket.escalation_reason}
            </div>
          )}

          {ticket.resolution_notes && (
            <div className="rounded bg-green-50 p-2 text-xs text-green-700">
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
                className="flex-1 rounded border border-slate-200 px-2 py-1.5 text-xs focus:border-blue-400 focus:outline-none"
              />
              <button
                onClick={handleResolve}
                disabled={resolving}
                className="flex items-center gap-1 rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
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

export function SupervisorDashboard() {
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

  useEffect(() => { load(); }, [load]);

  const handleResolve = (ticketId: string) => {
    setTickets((prev) =>
      prev.map((t) => t.ticket_id === ticketId ? { ...t, status: "RESOLVED" as const } : t)
    );
  };

  const visible = tickets.filter((t) => filter === "ALL" || t.status === filter);
  const openCount = tickets.filter((t) => t.status === "OPEN").length;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-slate-100 bg-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-orange-500" />
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Supervisor Escalation Queue</h2>
            <p className="text-xs text-slate-400">
              {openCount} open ticket{openCount !== 1 ? "s" : ""} · {tickets.length} total
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs">
            {(["ALL", "OPEN", "RESOLVED"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx(
                  "rounded-md px-2.5 py-1 font-medium transition-colors",
                  filter === f ? "bg-white shadow-sm text-slate-700" : "text-slate-400 hover:text-slate-600"
                )}
              >
                {f}
              </button>
            ))}
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
          >
            <RefreshCw className={clsx("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {/* Ticket list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {visible.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <CheckCircle2 className="mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm font-medium">
              {filter === "OPEN" ? "No open tickets" : "No tickets yet"}
            </p>
            <p className="text-xs mt-1">
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
  );
}
