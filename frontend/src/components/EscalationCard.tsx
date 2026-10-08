import { AlertTriangle, Users, Clock, ExternalLink } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  routingTarget: string;
  escalationReason: string;
  priority: string;
  ticketId?: string | null;
  onViewQueue?: () => void;
}

const priorityConfig = {
  CRITICAL: { bg: "bg-red-500/10",    border: "border-red-500/20",    badge: "bg-red-500/15 text-red-400",    icon: "text-red-400"    },
  URGENT:   { bg: "bg-orange-500/10", border: "border-orange-500/20", badge: "bg-orange-500/15 text-orange-400", icon: "text-orange-400" },
  ROUTINE:  { bg: "bg-blue-500/10",   border: "border-blue-500/20",   badge: "bg-blue-500/15 text-blue-400",  icon: "text-blue-400"   },
};

export function EscalationCard({ routingTarget, escalationReason, priority, ticketId, onViewQueue }: Props) {
  const cfg = priorityConfig[priority as keyof typeof priorityConfig] || priorityConfig.ROUTINE;

  return (
    <div className={clsx("mt-3 rounded-lg border p-3", cfg.bg, cfg.border)}>
      <div className="flex items-start gap-2">
        <AlertTriangle className={clsx("mt-0.5 h-4 w-4 shrink-0", cfg.icon)} />
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-dark-text">Escalated for Human Review</span>
            <span className={clsx("rounded-full px-2 py-0.5 text-xs font-bold", cfg.badge)}>
              {priority}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-sm text-dark-text">
            <Users className="h-3.5 w-3.5 text-dark-muted" />
            <span className="font-medium">{routingTarget}</span>
          </div>

          <p className="text-xs text-dark-muted">{escalationReason}</p>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1 text-xs text-dark-muted">
              <Clock className="h-3 w-3" />
              {ticketId ? (
                <span>
                  Ticket <span className="font-mono font-semibold text-dark-text">{ticketId}</span> created
                </span>
              ) : (
                <span>Ticket created — team will respond per SLA</span>
              )}
            </div>

            {onViewQueue && (
              <button
                onClick={onViewQueue}
                className="flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium text-brand-400 hover:bg-dark-hover transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                View Queue
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
