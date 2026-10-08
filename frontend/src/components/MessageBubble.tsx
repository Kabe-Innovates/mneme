import { clsx } from "clsx";
import { CheckCircle2, GitBranch, AlertTriangle, XCircle } from "lucide-react";
import type { Message, Outcome } from "../types";
import { SourceCitation } from "./SourceCitation";
import { WorkflowGuide } from "./WorkflowGuide";
import { EscalationCard } from "./EscalationCard";
import { ConfidenceBadge } from "./ConfidenceBadge";

const outcomeConfig: Record<
  Outcome,
  { label: string; bg: string; text: string; Icon: React.ComponentType<{ className?: string }> }
> = {
  ANSWER: { label: "Answered", bg: "bg-green-100", text: "text-green-700", Icon: CheckCircle2 },
  GUIDE: { label: "Guiding", bg: "bg-blue-100", text: "text-blue-700", Icon: GitBranch },
  ROUTE: { label: "Escalated", bg: "bg-orange-100", text: "text-orange-700", Icon: AlertTriangle },
  REFUSE: { label: "Declined", bg: "bg-red-100", text: "text-red-700", Icon: XCircle },
};

function OutcomeBadge({ outcome }: { outcome: Outcome }) {
  const { label, bg, text, Icon } = outcomeConfig[outcome];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
        bg,
        text
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}

function formatMessage(text: string) {
  // Very simple markdown-ish rendering: bold **text** and newlines
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br />");
}

interface Props {
  message: Message;
  sessionId: string;
}

export function MessageBubble({ message, sessionId }: Props) {
  const isUser = message.role === "user";
  const res = message.response;

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-2.5 text-sm text-white shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  const coverageKeys = ["WHAT", "WHERE", "NEXT", "WHO", "HOW"] as const;

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-white px-4 py-3 shadow-sm ring-1 ring-slate-100">

        {/* LLM offline banner */}
        {res?.banner && (
          <div className="mb-2 rounded bg-amber-50 border border-amber-200 px-2.5 py-1.5 text-xs text-amber-700 flex items-center gap-1.5">
            <span className="font-semibold">⚠</span> {res.banner}
          </div>
        )}

        {/* Header */}
        {res && (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <OutcomeBadge outcome={res.outcome} />
            {res.confidence > 0 && res.outcome !== "REFUSE" && (
              <ConfidenceBadge confidence={res.confidence} />
            )}
          </div>
        )}

        {/* 5-question coverage chips (ANSWER only) */}
        {res?.outcome === "ANSWER" && res.coverage && Object.keys(res.coverage).length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1">
            {coverageKeys.map((k) => {
              const val = res.coverage[k] ?? 0;
              return (
                <span
                  key={k}
                  className={`rounded-full px-1.5 py-0.5 text-xs font-semibold ${
                    val ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-400"
                  }`}
                  title={`${k}: ${val ? "covered" : "not covered"}`}
                >
                  {k}
                </span>
              );
            })}
          </div>
        )}

        {/* Message text */}
        <p
          className="text-sm leading-relaxed text-slate-700"
          dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
        />

        {/* Outcome-specific components */}
        {res?.outcome === "GUIDE" && res.workflow && (
          <WorkflowGuide workflow={res.workflow} sessionId={sessionId} />
        )}

        {res?.outcome === "ROUTE" && res.routing_target && (
          <EscalationCard
            routingTarget={res.routing_target}
            escalationReason={res.escalation_reason || "Human review required"}
            priority={res.priority || "ROUTINE"}
          />
        )}

        {res?.outcome === "ANSWER" && (res.sources.length > 0 || res.graph_context?.length > 0) && (
          <SourceCitation sources={res.sources} graphContext={res.graph_context} />
        )}

        {/* Timestamp */}
        <p className="mt-2 text-right text-xs text-slate-300">
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}
