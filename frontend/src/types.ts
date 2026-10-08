export type Outcome = "ANSWER" | "GUIDE" | "ROUTE" | "REFUSE";

export interface Source {
  source_id: string;
  title: string;
  department: string;
  relevance: number;
}

export interface WorkflowStep {
  step_number: number;
  description: string;
  required_fields: string[];
  system_used: string;
  is_approval_gate: boolean;
}

export interface WorkflowInfo {
  workflow_id: string;
  workflow_name: string;
  department: string;
  owner_team: string;
  escalation_team: string;
  current_step: number;
  steps: WorkflowStep[];
  missing_fields: MissingField[];
}

export interface MissingField {
  field_name: string;
  label: string;
  field_type: string;
  allowed_values: string[] | null;
  is_required: boolean;
  is_sensitive: boolean;
  validation_regex: string | null;
}

export interface AssistantResponse {
  outcome: Outcome;
  message: string;
  confidence: number;
  sources: Source[];
  workflow: WorkflowInfo | null;
  routing_target: string | null;
  escalation_reason: string | null;
  priority: string | null;
  session_id: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: AssistantResponse;
  timestamp: Date;
}
