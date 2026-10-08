import json
import os
from typing import Optional

_workflows: dict[str, dict] = {}
_field_defs: dict[str, dict] = {}
_sessions: dict[str, dict] = {}  # In-memory session store

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Maps workflow keywords to workflow IDs for fuzzy matching
WORKFLOW_KEYWORDS: dict[str, str] = {
    "mri": "WF-TPA-MRI-AUTH-01",
    "pre-auth": "WF-TPA-MRI-AUTH-01",
    "pre auth": "WF-TPA-MRI-AUTH-01",
    "authorization": "WF-TPA-MRI-AUTH-01",
    "authorisation": "WF-TPA-MRI-AUTH-01",
    "discharge": "WF-DIS-DISCHARGE-01",
    "billing correction": "WF-BILL-CORRECTION-01",
    "billing_correction": "WF-BILL-CORRECTION-01",
    "bed allocation": "WF-FRONT-BED-ALLOC-01",
    "bed alloc": "WF-FRONT-BED-ALLOC-01",
    "medical records": "WF-MR-RECORDS-REL-01",
    "records release": "WF-MR-RECORDS-REL-01",
    "it access": "WF-IT-ACCESS-01",
    "access provisioning": "WF-IT-ACCESS-01",
    "insurance claim": "WF-TPA-CLAIM-01",
    "claim submission": "WF-TPA-CLAIM-01",
    "equipment downtime": "WF-BIO-DOWNTIME-01",
    "downtime report": "WF-BIO-DOWNTIME-01",
}


def load_workflows():
    global _workflows, _field_defs
    wf_path = os.path.join(DATA_DIR, "workflows.json")
    fd_path = os.path.join(DATA_DIR, "field_definitions.json")

    with open(wf_path) as f:
        wf_list = json.load(f)
        _workflows = {w["workflow_id"]: w for w in wf_list}

    with open(fd_path) as f:
        fd_list = json.load(f)
        _field_defs = {fd["field_name"]: fd for fd in fd_list}

    print(f"[WorkflowEngine] Loaded {len(_workflows)} workflows, {len(_field_defs)} field definitions")


def find_workflow_for_intent(intent: dict) -> Optional[dict]:
    keyword = (intent.get("entities", {}).get("workflow_keyword") or "").lower()
    issue_type = (intent.get("issue_type") or "").lower().replace("_", " ")

    # Match by keyword from entities
    for kw, wf_id in WORKFLOW_KEYWORDS.items():
        if kw in keyword:
            return _workflows.get(wf_id)

    # Match by issue_type
    for kw, wf_id in WORKFLOW_KEYWORDS.items():
        if kw in issue_type:
            return _workflows.get(wf_id)

    return None


def start_workflow(workflow_id: str, session_id: str) -> dict:
    workflow = _workflows.get(workflow_id)
    if not workflow:
        return {}

    _sessions[session_id] = {
        "workflow_id": workflow_id,
        "current_step": 1,
        "collected_fields": {},
    }

    step = workflow["steps"][0] if workflow.get("steps") else {}
    missing = _get_missing_fields(step.get("required_fields", []), {})

    return {
        "workflow_id": workflow_id,
        "workflow_name": workflow["workflow_name"],
        "department": workflow["department"],
        "owner_team": workflow["owner_team"],
        "escalation_team": workflow.get("escalation_team", ""),
        "current_step": 1,
        "steps": workflow.get("steps", []),
        "missing_fields": missing,
    }


def _get_missing_fields(required_field_names: list[str], collected: dict) -> list[dict]:
    missing = []
    for fname in required_field_names:
        if fname not in collected:
            fd = _field_defs.get(fname, {})
            missing.append({
                "field_name": fname,
                "label": fd.get("label", fname.replace("_", " ").title()),
                "field_type": fd.get("field_type", "string"),
                "allowed_values": fd.get("allowed_values"),
                "is_required": fd.get("is_required", True),
                "is_sensitive": fd.get("is_sensitive", False),
                "validation_regex": fd.get("validation_regex"),
            })
    return missing


def get_workflow_for_response(workflow: dict, session_id: str) -> dict:
    return {
        "workflow_id": workflow["workflow_id"],
        "workflow_name": workflow["workflow_name"],
        "department": workflow["department"],
        "owner_team": workflow["owner_team"],
        "escalation_team": workflow.get("escalation_team", ""),
        "current_step": 1,
        "steps": workflow.get("steps", []),
        "missing_fields": [],
    }


def submit_field(session_id: str, workflow_id: str, field_name: str, field_value: str) -> dict:
    """Validate and save a field value, then advance step if all required fields are collected."""
    session = _sessions.get(session_id)
    if not session or session.get("workflow_id") != workflow_id:
        # Auto-create session if not found (user arrived via GUIDE without explicit start)
        _sessions[session_id] = {
            "workflow_id": workflow_id,
            "current_step": 1,
            "collected_fields": {},
        }
        session = _sessions[session_id]

    fd = _field_defs.get(field_name, {})

    # Validate allowed_values
    allowed = fd.get("allowed_values")
    if allowed and field_value not in allowed:
        return {"success": False, "error": f"'{field_value}' is not allowed. Options: {', '.join(allowed)}"}

    # Validate regex
    import re as _re
    regex = fd.get("validation_regex")
    if regex and not _re.match(regex, field_value):
        return {"success": False, "error": f"Value doesn't match expected format for {fd.get('label', field_name)}"}

    session["collected_fields"][field_name] = field_value

    workflow = _workflows.get(workflow_id, {})
    steps = sorted(workflow.get("steps", []), key=lambda s: s["step_number"])
    current_step_num = session["current_step"]

    current_step = next((s for s in steps if s["step_number"] == current_step_num), None)
    if not current_step:
        return {"success": True, "current_step": current_step_num, "step_advanced": False, "approval_gate_reached": False, "missing_fields": []}

    missing = _get_missing_fields(current_step.get("required_fields", []), session["collected_fields"])
    step_advanced = False
    approval_gate_reached = False

    if not missing:
        # All fields for current step collected — advance to next
        next_steps = [s for s in steps if s["step_number"] > current_step_num]
        if next_steps:
            next_step = next_steps[0]
            session["current_step"] = next_step["step_number"]
            step_advanced = True
            approval_gate_reached = next_step.get("is_approval_gate", False)
            missing = _get_missing_fields(next_step.get("required_fields", []), session["collected_fields"])
        else:
            step_advanced = True  # Workflow complete

    return {
        "success": True,
        "current_step": session["current_step"],
        "step_advanced": step_advanced,
        "approval_gate_reached": approval_gate_reached,
        "missing_fields": missing,
    }


def get_session_step(session_id: str) -> int:
    session = _sessions.get(session_id)
    return session["current_step"] if session else 1
