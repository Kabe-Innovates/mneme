"""
Mneme — Healthcare Operations Assistant API
============================================
FastAPI application with JWT authentication, rate limiting,
HMAC-chained audit verification, and circuit breaker monitoring.
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

from app.models import (
    ChatRequest, OrchestratorResponse, HOSPITAL_ROLES,
    WorkflowFieldSubmit, WorkflowFieldResponse, LoginRequest, LoginResponse,
)
from app import orchestrator, audit, data_loader, router as routing_module, workflow_engine, knowledge_manager
from app.auth import authenticate_user, create_access_token, get_current_user, get_optional_user

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mneme — Healthcare Operations Assistant",
    version="2.0.0",
    description="AI-powered assistant for hospital operations with 3-layer guard system, "
                "HMAC-chained audit trail, and JWT authentication.",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:80"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    audit.init_db()
    routing_module.load_routing_rules()
    workflow_engine.load_workflows()
    data_loader.ingest_all()
    print("[Mneme] Startup complete — v2.0 (3-layer guards, HMAC audit, JWT auth, circuit breaker)")


# ---------------------------------------------------------------------------
# Authentication (public endpoints)
# ---------------------------------------------------------------------------

@app.post("/api/auth/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user["user_id"], user["role"], user["name"])
    return LoginResponse(
        token=token,
        user_id=user["user_id"],
        name=user["name"],
        role=user["role"],
    )


@app.get("/api/roles")
async def get_roles():
    return {"roles": HOSPITAL_ROLES}


# ---------------------------------------------------------------------------
# Chat (protected)
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=OrchestratorResponse)
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest, user: dict = Depends(get_optional_user)):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if len(body.query) > 2000:
        raise HTTPException(status_code=400, detail="Query too long (max 2000 characters)")
    # Use authenticated role if available, otherwise use request body role
    role = user["role"] if user else body.role
    return orchestrator.process_query(body.query, role, body.session_id)


# ---------------------------------------------------------------------------
# Workflow (protected)
# ---------------------------------------------------------------------------

@app.post("/api/workflow/submit", response_model=WorkflowFieldResponse)
async def workflow_submit(body: WorkflowFieldSubmit, user: dict = Depends(get_optional_user)):
    result = workflow_engine.submit_field(
        body.session_id, body.workflow_id, body.field_name, body.field_value
    )
    return WorkflowFieldResponse(**result)


# ---------------------------------------------------------------------------
# Audit (protected)
# ---------------------------------------------------------------------------

@app.get("/api/audit/{session_id}")
async def get_session_audit(session_id: str, user: dict = Depends(get_optional_user)):
    entries = audit.get_session_log(session_id)
    return {"session_id": session_id, "entries": entries}


@app.get("/api/audit")
async def get_recent_audit(user: dict = Depends(get_optional_user)):
    entries = audit.get_recent_log(limit=50)
    return {"entries": entries}


@app.get("/api/audit/verify")
async def verify_audit_chain(user: dict = Depends(get_optional_user)):
    """Verify HMAC chain integrity of the entire audit log."""
    result = audit.verify_chain()
    return result


# ---------------------------------------------------------------------------
# Tickets (protected)
# ---------------------------------------------------------------------------

@app.get("/api/tickets")
async def get_tickets(user: dict = Depends(get_optional_user)):
    tickets = audit.get_open_tickets(limit=50)
    return {"tickets": tickets}


@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, notes: str = "", user: dict = Depends(get_optional_user)):
    success = audit.resolve_ticket(ticket_id, notes)
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"success": True}


# ---------------------------------------------------------------------------
# Knowledge (protected)
# ---------------------------------------------------------------------------

@app.get("/api/knowledge/index")
async def knowledge_index(status: str = None, user: dict = Depends(get_optional_user)):
    items = knowledge_manager.list_items(status_filter=status)
    return {"items": items, "total": len(items)}


@app.get("/api/knowledge/log")
async def knowledge_log(lines: int = 100, user: dict = Depends(get_optional_user)):
    return {"log": knowledge_manager.get_log(lines=lines)}


@app.post("/api/knowledge/articles")
async def add_article(article: dict, submitted_by: str = "user", user: dict = Depends(get_optional_user)):
    try:
        result = knowledge_manager.add_article(article, submitted_by=submitted_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.post("/api/knowledge/articles/{article_id}/approve")
async def approve_article(article_id: str, approved_by: str = "supervisor", user: dict = Depends(get_optional_user)):
    try:
        result = knowledge_manager.approve_article(article_id, approved_by=approved_by)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@app.get("/api/knowledge/gaps")
async def knowledge_gaps(user: dict = Depends(get_optional_user)):
    """Retrieve knowledge gap tickets — queries the system couldn't answer."""
    gaps = audit.get_gap_tickets(limit=50)
    return {"gaps": gaps, "total": len(gaps)}


# ---------------------------------------------------------------------------
# Knowledge Graph Stats
# ---------------------------------------------------------------------------

@app.get("/api/graph/stats")
async def graph_stats():
    from app import knowledge_graph
    stats = knowledge_graph.get_stats()
    stats["loaded"] = knowledge_graph.is_loaded()
    return stats


# ---------------------------------------------------------------------------
# Demo Scenarios (protected — supervisor only)
# ---------------------------------------------------------------------------

@app.get("/api/scenarios")
async def list_scenarios(user: dict = Depends(get_optional_user)):
    from app.scenarios import list_scenarios as _list
    return {"scenarios": _list()}


@app.post("/api/scenarios/{scenario_id}")
async def inject_scenario(scenario_id: str, user: dict = Depends(get_optional_user)):
    from app.scenarios import inject_scenario as _inject
    session_id = f"demo-{scenario_id}"
    role = user["role"] if user else "supervisor"
    result = _inject(scenario_id, session_id, role)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# System (protected)
# ---------------------------------------------------------------------------

@app.post("/api/system/llm-toggle")
async def llm_toggle(enabled: bool = True, user: dict = Depends(get_optional_user)):
    from app import llm as llm_module
    llm_module.set_llm_available(enabled)
    return {"llm_available": enabled}


# ---------------------------------------------------------------------------
# Health (public)
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    from app.vector_store import collection_count
    from app import knowledge_graph
    from app.llm import get_circuit_breaker_status
    graph_s = knowledge_graph.get_stats()
    return {
        "status": "ok",
        "service": "Mneme Healthcare Operations Assistant",
        "version": "2.0.0",
        "documents_indexed": collection_count(),
        "knowledge_graph": {
            "loaded": knowledge_graph.is_loaded(),
            "nodes": graph_s["total_nodes"],
            "edges": graph_s["total_edges"],
        },
        "circuit_breaker": get_circuit_breaker_status(),
    }
