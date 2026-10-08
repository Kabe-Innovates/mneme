import { AlertTriangle, Users, Clock } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  routingTarget: string;
  escalationReason: string;
  priority: string;
}

const priorityConfig = {
  CRITICAL: { bg: "bg-red-50", border: "border-red-200", badge: "bg-red-100 text-red-700", icon: "text-red-500" },
  URGENT: { bg: "bg-orange-50", border: "border-orange-200", badge: "bg-orange-100 text-orange-700", icon: "text-orange-500" },
  ROUTINE: { bg: "bg-blue-50", border: "border-blue-200", badge: "bg-blue-100 text-blue-700", icon: "text-blue-500" },
};

export function EscalationCard({ routingTarget, escalationReason, priority }: Props) {
  const cfg = priorityConfig[priority as keyof typeof priorityConfig] || priorityConfig.ROUTINE;

  return (
    <div className={clsx("mt-3 rounded-lg border p-3", cfg.bg, cfg.border)}>
      <div className="flex items-start gap-2">
        <AlertTriangle className={clsx("mt-0.5 h-4 w-4 shrink-0", cfg.icon)} />
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-semibold text-slate-800">Escalated for Human Review</span>
            <span className={clsx("rounded-full px-2 py-0.5 text-xs font-bold", cfg.badge)}>
              {priority}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-sm text-slate-700">
            <Users className="h-3.5 w-3.5 text-slate-400" />
            <span className="font-medium">{routingTarget}</span>
          </div>

          <p className="text-xs text-slate-600">{escalationReason}</p>

          <div className="flex items-center gap-1 text-xs text-slate-500">
            <Clock className="h-3 w-3" />
            <span>Ticket created — team will respond per SLA</span>
          </div>
        </div>
      </div>
    </div>
  );
}
