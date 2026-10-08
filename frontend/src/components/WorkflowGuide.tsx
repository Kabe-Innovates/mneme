import { useState } from "react";
import { CheckCircle2, Circle, ChevronRight, AlertCircle, Lock, ChevronDown, ChevronUp } from "lucide-react";
import { clsx } from "clsx";
import type { WorkflowInfo, MissingField } from "../types";
import { submitWorkflowField } from "../api";

interface Props {
  workflow: WorkflowInfo;
  sessionId: string;
}

function FieldInput({
  field,
  onSubmit,
}: {
  field: MissingField;
  onSubmit: (name: string, value: string) => Promise<void>;
}) {
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const handleSubmit = async () => {
    if (!value.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await onSubmit(field.field_name, value.trim());
      setDone(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-600">
        <CheckCircle2 className="h-3.5 w-3.5" />
        <span className="font-medium">{field.label}</span>
        <span className="text-slate-400">— saved</span>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <label className="flex items-center gap-1 text-xs font-medium text-slate-700">
        {field.label}
        {field.is_required && <span className="text-red-500">*</span>}
        {field.is_sensitive && <Lock className="h-3 w-3 text-orange-500" />}
      </label>

      <div className="flex gap-2">
        {field.allowed_values && field.allowed_values.length > 0 ? (
          <select
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="flex-1 rounded border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 focus:border-blue-400 focus:outline-none"
          >
            <option value="">Select…</option>
            {field.allowed_values.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        ) : (
          <input
            type={field.field_type === "currency" || field.field_type === "integer" ? "number" : "text"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={field.validation_regex ? `Format: ${field.validation_regex}` : `Enter ${field.label.toLowerCase()}`}
            className="flex-1 rounded border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 placeholder-slate-300 focus:border-blue-400 focus:outline-none"
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
        )}
        <button
          onClick={handleSubmit}
          disabled={submitting || !value}
          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-40"
        >
          {submitting ? "…" : "Save"}
        </button>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}

export function WorkflowGuide({ workflow, sessionId }: Props) {
  const [currentStep, setCurrentStep] = useState(workflow.current_step);
  const [missingFields, setMissingFields] = useState(workflow.missing_fields);
  const [approvalReached, setApprovalReached] = useState(false);
  const [showFields, setShowFields] = useState(true);

  const handleFieldSubmit = async (fieldName: string, fieldValue: string) => {
    const result = await submitWorkflowField(sessionId, workflow.workflow_id, fieldName, fieldValue);
    if (!result.success) throw new Error(result.error || "Validation failed");
    setMissingFields(result.missing_fields);
    if (result.step_advanced) {
      setCurrentStep(result.current_step);
      setApprovalReached(result.approval_gate_reached);
    }
  };

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

      {/* Approval gate banner */}
      {approvalReached && (
        <div className="mb-3 rounded-md border border-orange-200 bg-orange-50 p-2 text-xs text-orange-700">
          <strong>Approval gate reached.</strong> This step requires supervisor sign-off before proceeding.
          An escalation ticket has been created.
        </div>
      )}

      {/* Steps */}
      <ol className="space-y-2">
        {workflow.steps.map((step) => {
          const isCurrent = step.step_number === currentStep;
          const isDone = step.step_number < currentStep;

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

      {/* Interactive missing fields form */}
      {missingFields.length > 0 && (
        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3">
          <button
            onClick={() => setShowFields(!showFields)}
            className="flex w-full items-center justify-between gap-1.5 mb-1"
          >
            <div className="flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
              <span className="text-xs font-semibold text-amber-700">
                Required Information ({missingFields.length} field{missingFields.length !== 1 ? "s" : ""})
              </span>
            </div>
            {showFields ? (
              <ChevronUp className="h-3.5 w-3.5 text-amber-500" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-amber-500" />
            )}
          </button>
          {showFields && (
            <div className="mt-2 space-y-3">
              {missingFields.map((f) => (
                <FieldInput key={f.field_name} field={f} onSubmit={handleFieldSubmit} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* All fields done */}
      {missingFields.length === 0 && currentStep > 1 && !approvalReached && (
        <div className="mt-3 rounded-md border border-green-200 bg-green-50 p-2 text-xs text-green-700">
          <CheckCircle2 className="mr-1.5 inline h-3.5 w-3.5" />
          All required fields collected. Proceed to the next step in the system.
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
