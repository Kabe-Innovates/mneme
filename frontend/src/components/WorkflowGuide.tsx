import { CheckCircle2, Circle, ChevronRight, AlertCircle } from "lucide-react";
import { clsx } from "clsx";
import type { WorkflowInfo } from "../types";

interface Props {
  workflow: WorkflowInfo;
}

export function WorkflowGuide({ workflow }: Props) {
  return (
    <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50 p-3">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
            Step-by-Step Workflow
          </p>
          <h3 className="text-sm font-bold text-slate-800">{workflow.workflow_name}</h3>
          <p className="text-xs text-slate-500">
            {workflow.department} · Managed by {workflow.owner_team}
          </p>
        </div>
        <span className="shrink-0 rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
          {workflow.steps.length} steps
        </span>
      </div>

      {/* Steps */}
      <ol className="space-y-2">
        {workflow.steps.map((step) => {
          const isCurrent = step.step_number === workflow.current_step;
          const isDone = step.step_number < workflow.current_step;

          return (
            <li
              key={step.step_number}
              className={clsx(
                "flex gap-2.5 rounded-md p-2",
                isCurrent && "bg-white shadow-sm ring-1 ring-blue-200",
                isDone && "opacity-60"
              )}
            >
              <div className="shrink-0 pt-0.5">
                {isDone ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : isCurrent ? (
                  <ChevronRight className="h-4 w-4 text-blue-600" />
                ) : (
                  <Circle className="h-4 w-4 text-slate-300" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-slate-500">
                    Step {step.step_number}
                  </span>
                  {step.is_approval_gate && (
                    <span className="rounded bg-orange-100 px-1.5 py-0.5 text-xs font-medium text-orange-700">
                      Approval Required
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-700">{step.description}</p>
                {step.system_used && (
                  <p className="mt-0.5 text-xs text-slate-500">
                    System: <span className="font-medium">{step.system_used}</span>
                  </p>
                )}
                {step.required_fields.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {step.required_fields.map((f) => (
                      <span
                        key={f}
                        className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-600"
                      >
                        {f}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {/* Missing fields */}
      {workflow.missing_fields.length > 0 && (
        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-2">
          <div className="flex items-center gap-1.5 mb-1">
            <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
            <span className="text-xs font-semibold text-amber-700">Required Information</span>
          </div>
          <div className="space-y-1">
            {workflow.missing_fields.map((f) => (
              <div key={f.field_name} className="text-xs text-slate-700">
                <span className="font-medium">{f.label}</span>
                {f.allowed_values && (
                  <span className="text-slate-500"> ({f.allowed_values.join(", ")})</span>
                )}
                {f.is_sensitive && (
                  <span className="ml-1 text-orange-600">🔒</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Escalation info */}
      {workflow.escalation_team && (
        <p className="mt-2 text-xs text-slate-500">
          Escalation support: <span className="font-medium">{workflow.escalation_team}</span>
        </p>
      )}
    </div>
  );
}
