import type { AssistantResponse } from "./types";

const API_BASE = "http://localhost:8000";

// ---------------------------------------------------------------------------
// JWT Token Management (in-memory only — HIPAA: no localStorage)
// ---------------------------------------------------------------------------

let _token: string | null = null;

export function setToken(token: string | null) {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }
  return headers;
}

async function handleResponse(res: Response) {
  if (res.status === 401) {
    _token = null;
    window.dispatchEvent(new CustomEvent("mneme:logout"));
    throw new Error("Session expired — please log in again");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

export async function login(
  username: string,
  password: string
): Promise<{ token: string; user_id: string; name: string; role: string }> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  _token = data.token;
  return data;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export async function sendMessage(
  query: string,
  role: string,
  sessionId: string
): Promise<AssistantResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query, role, session_id: sessionId }),
  });
  return handleResponse(res);
}

// ---------------------------------------------------------------------------
// Roles
// ---------------------------------------------------------------------------

export async function getRoles(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/roles`);
  const data = await res.json();
  return data.roles;
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export async function getAuditLog(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/audit/${sessionId}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function verifyAuditChain() {
  const res = await fetch(`${API_BASE}/api/audit/verify`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ---------------------------------------------------------------------------
// Workflow
// ---------------------------------------------------------------------------

export async function submitWorkflowField(
  sessionId: string,
  workflowId: string,
  fieldName: string,
  fieldValue: string
) {
  const res = await fetch(`${API_BASE}/api/workflow/submit`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      session_id: sessionId,
      workflow_id: workflowId,
      field_name: fieldName,
      field_value: fieldValue,
    }),
  });
  return handleResponse(res);
}

// ---------------------------------------------------------------------------
// Tickets
// ---------------------------------------------------------------------------

export async function getTickets() {
  const res = await fetch(`${API_BASE}/api/tickets`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function resolveTicket(ticketId: string, notes: string = "") {
  const res = await fetch(
    `${API_BASE}/api/tickets/${ticketId}/resolve?notes=${encodeURIComponent(notes)}`,
    { method: "POST", headers: authHeaders() }
  );
  return handleResponse(res);
}

// ---------------------------------------------------------------------------
// Knowledge
// ---------------------------------------------------------------------------

export async function getKnowledgeIndex(status?: string) {
  const url = status
    ? `${API_BASE}/api/knowledge/index?status=${status}`
    : `${API_BASE}/api/knowledge/index`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleResponse(res);
}

export async function getIngestionLog(lines = 100) {
  const res = await fetch(`${API_BASE}/api/knowledge/log?lines=${lines}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function approveKnowledgeArticle(articleId: string) {
  const res = await fetch(
    `${API_BASE}/api/knowledge/articles/${articleId}/approve`,
    { method: "POST", headers: authHeaders() }
  );
  return handleResponse(res);
}

export async function getKnowledgeGaps() {
  const res = await fetch(`${API_BASE}/api/knowledge/gaps`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ---------------------------------------------------------------------------
// Demo Scenarios
// ---------------------------------------------------------------------------

export async function getScenarios() {
  const res = await fetch(`${API_BASE}/api/scenarios`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function injectScenario(scenarioId: string) {
  const res = await fetch(`${API_BASE}/api/scenarios/${scenarioId}`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export async function toggleLlm(enabled: boolean) {
  const res = await fetch(`${API_BASE}/api/system/llm-toggle?enabled=${enabled}`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleResponse(res);
}
