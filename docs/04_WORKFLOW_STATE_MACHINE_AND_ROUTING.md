# 04. Guided Workflows & Routing Engine

## 1. The "Do It With Me" Guided Workflow Model

Hospital frontline staff do not just ask informational questions; they execute complex operational transactions under time pressure. If a chatbot simply drops a 20-page SOP PDF on a front-desk receptionist, operational friction increases.

The **Guided Workflow Engine** treats operational procedures as state-machine micro-flows driven by the Knowledge Graph:
1. **Identifies the Workflow**: Maps the user's intent to a specific `Workflow` node.
2. **Evaluates Missing Slots**: Determines which `Field` nodes are marked `is_required` and currently unfulfilled.
3. **Presents Progressive Input Fields**: Requests missing parameters 1 or 2 at a time (optimized for mobile screens).
4. **Validates Data Types**: Deterministically verifies dates, MRN formats, and insurer names against allowed vocabularies.
5. **Enforces Human-in-the-Loop Thresholds**: If an action involves an irreversible transaction (financial refund $> \$100$, account privilege escalation, medical record release), execution halts and routes for human supervisor sign-off.

---

## 2. Workflow State Machine Architecture

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> WorkflowIdentified: Intent: START_WORKFLOW
    WorkflowIdentified --> CheckPrerequisites: Fetch Required Fields
    
    state CheckPrerequisites {
        [*] --> EvaluateFields
        EvaluateFields --> PromptUser: Missing Fields Detected
        PromptUser --> ValidateInput: User Provides Values
        ValidateInput --> EvaluateFields: Validation Success
        ValidateInput --> PromptUser: Invalid Format / Range
    }

    CheckPrerequisites --> CheckApprovalGates: All Fields Present
    
    state CheckApprovalGates {
        [*] --> EvaluateLimits
        EvaluateLimits --> ReadyForExecution: Within Standard Limits
        EvaluateLimits --> SupervisorSignoff: Exceeds Limit / Sensitive
    }

    SupervisorSignoff --> EscalationDispatched: ROUTE to Supervisor Queue
    ReadyForExecution --> StepExecution: Auto-generate HIS Payload / Checklist
    StepExecution --> WorkflowCompleted: User Confirms Success
    StepExecution --> ExceptionEncountered: Rejection / Error / Delay
    ExceptionEncountered --> EscalationDispatched: Auto-route to Escalation Team
    EscalationDispatched --> [*]
    WorkflowCompleted --> [*]
```

---

## 3. Field Definition & Validation Specification

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import re

class FieldDataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DATE = "date"
    ENUM = "enum"
    CURRENCY = "currency"

class WorkflowField(BaseModel):
    field_id: str
    label: str
    data_type: FieldDataType
    is_required: bool = True
    is_sensitive: bool = False
    allowed_values: Optional[List[str]] = None
    validation_regex: Optional[str] = None

    def validate_value(self, value: Any) -> bool:
        if self.is_required and (value is None or str(value).strip() == ""):
            return False
        if self.allowed_values and value not in self.allowed_values:
            return False
        if self.validation_regex and not re.match(self.validation_regex, str(value)):
            return False
        return True
```

---

## 4. Golden Path Walkthrough: MRI Pre-Authorization

### Step 1: Initial Ingestion & Missing Slot Analysis
- **User Message**: *"Patient has an MRI scheduled tomorrow, insurer is Star Health, auth is pending. What should I do?"*
- **Role**: Front Office Executive.
- **Engine State**:
  - Matched Workflow: `WF-RAD-MRI-AUTH-01` (*Outpatient MRI Pre-Authorization*).
  - Required Fields: `Insurer` (Star Health - Captured), `Procedure Code` (MRI Brain/Spine - Missing), `Scheduled Date` (Tomorrow - Captured), `Portal Status` (Pending - Captured).
  - Outcome: `GUIDE`.
  - Assistant Output: *"For Star Health, outpatient MRI pre-authorization is mandatory under SOP-TPA-014. Please confirm the exact MRI procedure code or anatomical region (e.g., MRI Brain with Contrast)."*

### Step 2: Slot Fulfillment & Next Action
- **User Message**: *"Procedure is MRI Lumbar Spine without contrast."*
- **Engine State**:
  - All mandatory slots fulfilled.
  - Verified Status: `Portal Status = Pending`.
  - Next Action from Graph (`Step 4: Pending Status Protocol`):
    - Verify submission timestamp on TPA Portal.
    - If submitted $< 4$ hours ago: SLA window is active; monitor portal every 60 minutes.
    - If submitted $> 4$ hours ago: Escalate to Star Health Priority Desk (Phone: Ext 4022).

### Step 3: Rejection Branch & Escalation Handoff
- **User Message**: *"Portal status just changed to 'Rejected due to insufficient clinical justification'."*
- **Engine State**:
  - Trigger Condition: Rejection encountered.
  - Policy Rule: `Insurer Rejection` $\implies$ State `ROUTE` to `Insurance/TPA Desk`.
  - Action: Generate Escalation Ticket `#TKT-8492`.
  - Assistant Output: *"Pre-authorization was rejected by Star Health due to clinical documentation. I have created escalation ticket #TKT-8492 and routed it to the In-House TPA Desk with high priority. A pre-authorization executive has been notified to attach clinical notes."*

### Step 4: Uncertainty Path (Knowledge Gap Scenario)
- **User Message**: *"What is the pre-authorization process for PQR Insurance? They are a new insurer we just signed up."*
- **Engine State**:
  - Hybrid search finds no `Article` or `Workflow` node matching "PQR Insurance".
  - Knowledge Graph has zero insurer-specific routing rules or pre-auth thresholds for PQR.
  - Calculated Verification Score: $S_{\text{total}} = 0.28$ (falls below $0.50$ Low-Confidence threshold).
  - Outcome: `ROUTE`.
  - Assistant Output: *"I don't have approved hospital documentation for PQR Insurance's pre-authorization requirements yet. Since this may be a newly empanelled insurer, I am routing your request to the Insurance/TPA Desk (Ticket #TKT-8495) so an executive can clarify and update our knowledge base. In the meantime, you can review the general pre-authorization checklist in SOP-TPA-014."*
  - **Confidence Badge**: 🔴 Low (0.28) — Insufficient Approved Data.
  - **Auto-Generated Ticket**: Includes reason `"MISSING_APPROVED_KNOWLEDGE"`, missing entity `"PQR Insurance"`, and suggested owner `"Insurance / TPA Desk"`.

---

## 5. Support Routing Engine & Escalation Tickets

### 5.1 Deterministic Routing Matrix

| Trigger Category | Specific Condition | Target Department | Escalation Urgency | Max Response SLA |
| :--- | :--- | :--- | :--- | :--- |
| **Cashless Rejection** | TPA portal query / rejection | Insurance / TPA Desk | URGENT | 30 minutes |
| **Billing Dispute** | Adjustment $> \$200$ | Billing Supervisor | ROUTINE | 2 hours |
| **Discharge Hold** | Pharmacy / Lab clearance block | Nursing In-Charge | URGENT | 15 minutes |
| **HIS Account Provisioning** | Admin role or VIP chart access | IT / HIS Security Lead | ROUTINE | 4 hours |
| **Biomedical Fault** | Modality downtime (MRI / CT / Cath) | Biomedical Engineering | CRITICAL | 10 minutes |
| **Facility Emergency** | Fluid spill / electrical fault | Facility & Safety Desk | CRITICAL | 5 minutes |
| **Knowledge Insufficiency** | $S_{\text{total}} < 0.50$ (No approved SOP) | Department Operations Head | ROUTINE | 24 hours |

### 5.2 Dynamic Urgency Calculation
Urgency is deterministically evaluated using context attributes:
```python
def calculate_urgency(query: str, session: Session) -> str:
    high_urgency_triggers = [
        "patient waiting", "counter crowd", "surgery scheduled",
        "stat", "icu transfer", "discharge delayed", "code"
    ]
    if any(trigger in query.lower() for trigger in high_urgency_triggers):
        return "URGENT"
    if session.has_modality_downtime or session.has_clinical_rejection:
        return "URGENT"
    return "ROUTINE"
```

### 5.3 Escalation Ticket Payload
```json
{
  "ticket_id": "TKT-2026-8492",
  "created_at": "2026-10-08T13:20:00Z",
  "initiator": {
    "user_id": "EMP-4019",
    "role": "Front Office Executive",
    "counter": "Counter-03"
  },
  "assigned_team": "Insurance / TPA Desk",
  "urgency": "URGENT",
  "reason": "INSURER_REJECTION",
  "summary": "Star Health rejected pre-authorization for MRI Lumbar Spine due to missing clinical justification.",
  "tried_steps": [
    "Verified mandatory cashless admission documents under SOP-TPA-014",
    "Checked portal status (Status: REJECTED)",
    "Identified missing clinical progress notes"
  ],
  "evidence_cited": ["SOP-TPA-014", "FORM-TPA-REQ-02", "SYS-TPA-PORTAL"],
  "status": "OPEN",
  "audit_ref": "c5f6a8e0-47b2-4d1a-96e8-23fbc0432190"
}
```

---

## 6. Agent Dashboard Specification

The Support Agent & Admin Dashboard provides operational supervisors with full visibility into the triage queue, escalated tickets, knowledge health, and compliance logs.

### 6.1 Escalation Queue View (Primary Triage Screen)
Displays active tickets prioritized by the deterministic urgency scoring engine:

| Display Column | Data Source | Interaction & Behavior |
| :--- | :--- | :--- |
| **Urgency Badge** | `ticket.urgency` | 🔴 `CRITICAL` / 🟡 `URGENT` / 🔵 `ROUTINE` (Default sort: Descending) |
| **Ticket ID** | `ticket.ticket_id` | Click to open Slide-Over Detail Drawer |
| **Summary** | `ticket.summary` | High-level situation synopsis (auto-synthesized by Step 2) |
| **Assigned Department**| `ticket.assigned_team` | Filter dropdown: *TPA Desk, Billing, IT, Nursing, Biomedical* |
| **Initiator Role** | `ticket.initiator.role` | Staff persona seeking assistance (e.g., *Front Desk*) |
| **Time in Queue** | `ticket.created_at` | Color warning when approaching SLA threshold (e.g., $> 20$ min) |
| **Status** | `ticket.status` | State pills: `OPEN`, `IN_PROGRESS`, `RESOLVED` |

**Quick Action Buttons**:
- `Claim Ticket`: Assigns ticket to current logged-in agent and transitions status to `IN_PROGRESS`.
- `Reassign`: Opens team picker to dispatch ticket to another department with a handoff note.
- `Quick Resolve`: Closes ticket with resolution category and note.

### 6.2 Ticket Detail Drawer (Slide-Over Panel)
When an agent clicks an escalation ticket, an inspection drawer expands showing:
1. **Context Summary**: Structured synopsis of what the employee asked and what the assistant already attempted.
2. **Tried Steps**: Chronological list of steps executed before escalation occurred.
3. **Evidence Cited**: Direct clickable badges to the governing SOPs and forms (`SOP-TPA-014`, `FORM-TPA-REQ-02`).
4. **Escalation Justification**: Deterministic rule trigger that caused the handoff (e.g., `INSURER_REJECTION`, `THRESHOLD_EXCEEDED`, `LOW_CONFIDENCE`).
5. **Redacted Chat Transcript**: Full multi-turn conversation between employee and assistant with PII masked.
6. **Agent Resolution Box**: Form allowing the human agent to enter the official resolution note and select whether this incident requires a Knowledge Base update.

### 6.3 Knowledge Graph Explorer View
Interactive force-directed graph (Cytoscape / 2D Canvas) displaying hospital operational topology:
- **Visual Node Clustering**: Grouped by type (Articles = Blue, Workflows = Teal, Forms = Yellow, Systems = Purple, Teams = Orange).
- **Interactive Multi-Hop Inspection**: Click any node (e.g., `WF-RAD-MRI-AUTH-01`) to highlight all connected forms, systems, and owning teams.
- **Change Impact Mode**: Select a node to compute backlinks and immediately highlight all downstream workflows and steps that depend on it.

### 6.4 Compliance Audit Trail Viewer
Searchable table querying the immutable `audit_log` records:
- **Filters**: By User Role, Decision Outcome (`ANSWER`, `GUIDE`, `ROUTE`, `REFUSE`), Confidence Band, Date Range.
- **Audit Detail Modal**: Inspect exact prompt payload, sanitized query, retrieved node IDs, and confidence score vector.
- **Export Utility**: One-click CSV/JSON export for hospital accreditation (NABH / ISO 27799) reviews.

