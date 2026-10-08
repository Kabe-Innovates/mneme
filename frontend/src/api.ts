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
