import type { AssistantResponse } from "./types";

const API_BASE = "http://localhost:8000";

export async function sendMessage(
  query: string,
  role: string,
  sessionId: string
): Promise<AssistantResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, role, session_id: sessionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error: ${res.status}`);
  }
  return res.json();
}

export async function getRoles(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/roles`);
  const data = await res.json();
  return data.roles;
}

export async function getAuditLog(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/audit/${sessionId}`);
  return res.json();
}

export async function submitWorkflowField(
  sessionId: string,
  workflowId: string,
  fieldName: string,
  fieldValue: string
) {
  const res = await fetch(`${API_BASE}/api/workflow/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      workflow_id: workflowId,
      field_name: fieldName,
      field_value: fieldValue,
    }),
  });
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
  return res.json();
}

export async function getTickets() {
  const res = await fetch(`${API_BASE}/api/tickets`);
  return res.json();
}

export async function resolveTicket(ticketId: string, notes: string = "") {
  const res = await fetch(
    `${API_BASE}/api/tickets/${ticketId}/resolve?notes=${encodeURIComponent(notes)}`,
    { method: "POST" }
  );
  return res.json();
}

export async function toggleLlm(enabled: boolean) {
  const res = await fetch(`${API_BASE}/api/system/llm-toggle?enabled=${enabled}`, {
    method: "POST",
  });
  return res.json();
}
