from pydantic import BaseModel, Field
from typing import Optional
import uuid


# ---------------------------------------------------------------------------
# Authentication Models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: str
    name: str
    role: str


# ---------------------------------------------------------------------------
# Hospital Roles
# ---------------------------------------------------------------------------

HOSPITAL_ROLES = [
    "Front Office",
    "Admission Desk",
    "Discharge Operations",
    "Billing & Cash Operations",
    "Insurance & TPA",
    "Medical Records",
    "Case Management",
    "Quality & Accreditation",
    "Operations Management",
    "IT & HIS Support",
    "Facility & Maintenance",
    "Biomedical Engineering",
    "Pharmacy",
    "Laboratory",
    "Radiology Operations",
]


class ChatRequest(BaseModel):
    query: str
    role: str = "Front Office"
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class Source(BaseModel):
    source_id: str
    title: str
    department: str
    relevance: float


class WorkflowStep(BaseModel):
    step_number: int
    description: str
    required_fields: list[str] = []
    system_used: str = ""
    is_approval_gate: bool = False


class WorkflowInfo(BaseModel):
    workflow_id: str
    workflow_name: str
    department: str
    owner_team: str
    escalation_team: str
    current_step: int = 1
    steps: list[WorkflowStep] = []
    missing_fields: list[dict] = []


class GraphNode(BaseModel):
    node_id: str
    node_type: str
    title: str
    detail: str = ""


class WorkflowFieldSubmit(BaseModel):
    session_id: str
    workflow_id: str
    field_name: str
    field_value: str


class WorkflowFieldResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    current_step: int = 1
    step_advanced: bool = False
    approval_gate_reached: bool = False
    missing_fields: list[dict] = []


class OrchestratorResponse(BaseModel):
    outcome: str  # ANSWER | GUIDE | ROUTE | REFUSE
    message: str
    confidence: float = 0.0
    sources: list[Source] = []
    workflow: Optional[WorkflowInfo] = None
    routing_target: Optional[str] = None
    escalation_reason: Optional[str] = None
    priority: Optional[str] = None
    session_id: str = ""
    graph_context: list[GraphNode] = []  # connected subgraph entities
    confidence_band: str = "medium"  # high | medium | low
    coverage: dict[str, int] = {}   # {"WHAT":1,"WHERE":1,"NEXT":1,"WHO":1,"HOW":0}
    llm_mode: str = "llm"           # "llm" | "template"
    banner: Optional[str] = None    # shown in UI when LLM is offline
    ticket_id: Optional[str] = None # populated for ROUTE outcomes
