import { XCircle, Stethoscope, PhoneCall, BookOpen, ArrowRight } from "lucide-react";

const ACTIONS = [
  {
    Icon: Stethoscope,
    title: "Clinical decision",
    desc: "Consult the on-duty physician or charge nurse",
  },
  {
    Icon: PhoneCall,
    title: "Emergency or patient safety",
    desc: "Follow your facility's emergency response protocol immediately",
  },
  {
    Icon: BookOpen,
    title: "Policy clarification",
    desc: "Check the hospital intranet or contact your department head",
  },
  {
    Icon: ArrowRight,
    title: "Need operational help instead?",
    desc: "Rephrase your question about a process, workflow, or policy",
  },
];

export function RefuseGuidance() {
  return (
    <div className="mt-3 space-y-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3 font-sans">
      <div className="font-display flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-red-400">
        <XCircle className="h-3.5 w-3.5" />
        Outside operational scope — suggested next steps
      </div>
      <ul className="space-y-1.5">
        {ACTIONS.map(({ Icon, title, desc }) => (
          <li key={title} className="flex items-start gap-2">
            <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" />
            <div>
              <span className="text-xs font-semibold text-dark-text">{title}: </span>
              <span className="text-xs text-dark-muted">{desc}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
