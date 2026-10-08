import json
import os
import boto3
from typing import Optional

_bedrock = None


def _get_client():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )
    return _bedrock


MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

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


def invoke_claude(system: str, user_message: str, max_tokens: int = 1024) -> str:
    client = _get_client()
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    })
    response = client.invoke_model(
        modelId=MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def classify_intent(query: str, role: str) -> dict:
    user_msg = f"Role: {role}\nQuery: {query}"
    try:
        raw = invoke_claude(CLASSIFIER_SYSTEM, user_msg, max_tokens=512)
        # Extract JSON even if model adds surrounding text
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


def generate_answer(query: str, context_docs: list[dict], role: str) -> dict:
    if not context_docs:
        return {
            "text": "I don't have sufficient information in the approved knowledge base to answer this question. Please contact the relevant department or refer to the latest SOPs.",
            "citations": [],
        }

    context_str = "\n\n---\n\n".join(
        f"[{doc['source_id']}] {doc['title']}\n{doc['content']}"
        for doc in context_docs
    )
    user_msg = f"""Role: {role}
Query: {query}

Context Documents:
{context_str}

Provide a helpful, grounded answer with inline citations."""

    try:
        text = invoke_claude(GENERATOR_SYSTEM, user_msg, max_tokens=1024)
        # Extract cited source IDs
        import re
        cited = list(set(re.findall(r"\[([A-Z][A-Z0-9\-]+)\]", text)))
        citations = [
            {"source_id": doc["source_id"], "title": doc["title"], "department": doc.get("department", "")}
            for doc in context_docs
            if doc["source_id"] in cited
        ]
        return {"text": text, "citations": citations}
    except Exception as e:
        print(f"[LLM] generate_answer error: {e}")
        return {"text": "Unable to generate response. Please try again.", "citations": []}
