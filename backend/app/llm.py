"""
Mneme LLM Layer — AWS Bedrock Claude with Circuit Breaker
=========================================================
Provides intent classification and grounded answer generation.
Includes self-healing circuit breaker (from Divathiru's pattern):
  - After 5 consecutive failures, opens for 30 seconds
  - Automatically falls back to template mode while open
  - Half-open retry after cooldown, resets on success
"""

import json
import os
import time
import boto3
from typing import Optional

_bedrock = None


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Self-healing LLM circuit breaker with three states: CLOSED, OPEN, HALF_OPEN."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._consecutive_failures = 0
        self._opened_at: float = 0.0
        self._state = "CLOSED"

    @property
    def state(self) -> str:
        if self._state == "OPEN":
            if time.time() - self._opened_at >= self.recovery_timeout:
                self._state = "HALF_OPEN"
        return self._state

    def is_open(self) -> bool:
        return self.state == "OPEN"

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._state = "CLOSED"

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._state = "OPEN"
            self._opened_at = time.time()
            print(f"[LLM] Circuit breaker OPEN — {self._consecutive_failures} consecutive failures")


# Module-level circuit breaker instance
_circuit_breaker = CircuitBreaker()


def get_circuit_breaker_status() -> dict:
    """Return circuit breaker state for health/status endpoints."""
    return {
        "state": _circuit_breaker.state,
        "consecutive_failures": _circuit_breaker._consecutive_failures,
    }


# ---------------------------------------------------------------------------
# Bedrock Client
# ---------------------------------------------------------------------------

def _get_client():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )
    return _bedrock


def _model_id() -> str:
    return os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5-20250929-v1:0")


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

CLASSIFIER_SYSTEM = """You are a healthcare operations intent classifier for a hospital assistant named Mneme.
Given a user's query and their role, output ONLY valid JSON with this exact structure:
{
  "intent": "knowledge_question|workflow_request|routing_needed|unclear",
  "issue_type": "billing_correction|insurance_auth|medical_records|it_access|bed_allocation|equipment_downtime|insurance_claim|discharge_process|radiology_scheduling|lab_guidelines|visitor_policy|patient_complaint|financial_waiver|his_downtime|patient_transfer|general_operational|unclear",
  "entities": {
    "department": "string or null",
    "workflow_keyword": "string or null",
    "amount": "number or null",
    "urgency": "routine|urgent|critical"
  },
  "confidence": 0.0
}
Rules:
- intent=knowledge_question: user wants to know policy/procedure information
- intent=workflow_request: user wants step-by-step guidance to complete a task
- intent=routing_needed: request requires human team intervention
- intent=unclear: ambiguous, cannot determine intent
- confidence: 0.0-1.0, your certainty about the classification
- NEVER classify clinical/medical advice questions (prescriptions, diagnosis, treatment) — those are handled before reaching you
- Do not include any text outside the JSON object."""

GENERATOR_SYSTEM = """You are Mneme, a healthcare operations assistant for hospital staff. Your role is to provide grounded, accurate operational guidance.

STRICT RULES:
1. Answer ONLY using the provided context documents. Do not invent policies or procedures.
2. Cite every factual claim using [SOURCE_ID] format inline. Example: "Submit Form TPA-REQ-02 [SOP-TPA-014]."
3. If the context partially answers the question, state what you know and note any gaps: "Based on available documentation, [answer]. However, [specific gap] is not covered and should be verified with [team]."
4. NEVER provide medical, clinical, pharmaceutical, or diagnostic advice.
5. NEVER make up procedures, policies, or document references not in the context.
6. Express uncertainty clearly when context is incomplete.
7. Keep answers concise and action-oriented for frontline hospital staff.
8. Acknowledge the user's role when relevant to what they can access or do."""


# ---------------------------------------------------------------------------
# Core LLM Call with Circuit Breaker
# ---------------------------------------------------------------------------

def invoke_claude(system: str, user_message: str, max_tokens: int = 1024) -> str:
    """Call Bedrock Claude with circuit breaker protection."""
    if _circuit_breaker.is_open():
        raise ConnectionError("Circuit breaker is OPEN — LLM temporarily unavailable")

    client = _get_client()
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    })
    try:
        response = client.invoke_model(
            modelId=_model_id(),
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        _circuit_breaker.record_success()
        return result["content"][0]["text"]
    except Exception as e:
        _circuit_breaker.record_failure()
        raise


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------

def classify_intent(query: str, role: str) -> dict:
    user_msg = f"Role: {role}\nQuery: {query}"
    try:
        raw = invoke_claude(CLASSIFIER_SYSTEM, user_msg, max_tokens=512)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception as e:
        print(f"[LLM] classify_intent error: {e}")
    return {
        "intent": "unclear",
        "issue_type": "unclear",
        "entities": {"department": None, "workflow_keyword": None, "amount": None, "urgency": "routine"},
        "confidence": 0.0,
    }


# ---------------------------------------------------------------------------
# Template Fallback (used when circuit breaker is open or LLM fails)
# ---------------------------------------------------------------------------

def _template_answer(context_docs: list[dict]) -> dict:
    """Serve verified SOP excerpts directly when the LLM is unavailable."""
    if not context_docs:
        return {
            "text": "No relevant documentation found. Please contact the appropriate team for assistance.",
            "citations": [],
            "mode": "template",
            "banner": "LLM offline — showing verified SOP excerpts only.",
        }
    article_docs = [d for d in context_docs if d.get("node_type") == "article" or d.get("source_id", "").startswith("SOP")]
    docs_to_show = article_docs[:2] or context_docs[:2]
    parts = []
    citations = []
    for doc in docs_to_show:
        sid = doc["source_id"]
        title = doc["title"]
        content = doc["content"][:600].strip()
        parts.append(f"**{title}** [{sid}]\n{content}")
        citations.append({"source_id": sid, "title": title, "department": doc.get("department", "")})
    text = "\n\n".join(parts)
    if len(context_docs[0]["content"]) > 600:
        text += "\n\n*(Excerpt — refer to the full document for complete details.)*"
    return {
        "text": text,
        "citations": citations,
        "mode": "template",
        "banner": "LLM offline — showing verified SOP excerpts only.",
    }


# ---------------------------------------------------------------------------
# Answer Generation
# ---------------------------------------------------------------------------

def generate_answer(query: str, context_docs: list[dict], role: str,
                    conversation_history: Optional[list[dict]] = None) -> dict:
    if not context_docs:
        return {
            "text": "I don't have sufficient information in the approved knowledge base to answer this question. Please contact the relevant department or refer to the latest SOPs.",
            "citations": [],
            "mode": "llm",
        }

    if _circuit_breaker.is_open():
        return _template_answer(context_docs)

    context_str = "\n\n---\n\n".join(
        f"[{doc['source_id']}] {doc['title']}\n{doc['content']}"
        for doc in context_docs
    )

    # Build user message with optional conversation history
    history_str = ""
    if conversation_history:
        history_lines = []
        for turn in conversation_history[-5:]:  # Last 5 turns max
            history_lines.append(f"User: {turn.get('query', '')}")
            history_lines.append(f"Assistant: {turn.get('summary', '')}")
        history_str = f"\nConversation History:\n" + "\n".join(history_lines) + "\n"

    user_msg = f"""Role: {role}
Query: {query}
{history_str}
Context Documents:
{context_str}

Provide a helpful, grounded answer with inline citations."""

    try:
        text = invoke_claude(GENERATOR_SYSTEM, user_msg, max_tokens=1024)
        import re
        cited = list(set(re.findall(r"\[([A-Z][A-Z0-9\-]+)\]", text)))
        citations = [
            {"source_id": doc["source_id"], "title": doc["title"], "department": doc.get("department", "")}
            for doc in context_docs
            if doc["source_id"] in cited
        ]
        return {"text": text, "citations": citations, "mode": "llm"}
    except Exception as e:
        print(f"[LLM] generate_answer error: {e} — falling back to template mode")
        return _template_answer(context_docs)


# ---------------------------------------------------------------------------
# Legacy compatibility
# ---------------------------------------------------------------------------

def llm_available() -> bool:
    """Returns True if the LLM circuit breaker is not open."""
    return not _circuit_breaker.is_open()


def set_llm_available(state: bool) -> None:
    """Legacy toggle — maps to circuit breaker state."""
    if state:
        _circuit_breaker.record_success()  # Force-close the breaker
    else:
        # Force-open the breaker by exceeding failure threshold
        for _ in range(_circuit_breaker.failure_threshold):
            _circuit_breaker.record_failure()
    print(f"[LLM] Mode switched to {'LLM' if state else 'TEMPLATE'}")
