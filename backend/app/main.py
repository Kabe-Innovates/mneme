from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

from app.models import ChatRequest, OrchestratorResponse, HOSPITAL_ROLES, WorkflowFieldSubmit, WorkflowFieldResponse
from app import orchestrator, audit, data_loader, router as routing_module, workflow_engine

app = FastAPI(title="Mneme — Healthcare Operations Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    audit.init_db()
    routing_module.load_routing_rules()
    workflow_engine.load_workflows()
    data_loader.ingest_all()
    print("[Mneme] Startup complete")


@app.post("/api/chat", response_model=OrchestratorResponse)
async def chat(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if len(request.query) > 2000:
        raise HTTPException(status_code=400, detail="Query too long (max 2000 characters)")
    return orchestrator.process_query(request.query, request.role, request.session_id)


@app.get("/api/roles")
async def get_roles():
    return {"roles": HOSPITAL_ROLES}


@app.get("/api/audit/{session_id}")
async def get_session_audit(session_id: str):
    entries = audit.get_session_log(session_id)
    return {"session_id": session_id, "entries": entries}


@app.get("/api/audit")
async def get_recent_audit():
    entries = audit.get_recent_log(limit=50)
    return {"entries": entries}


@app.post("/api/workflow/submit", response_model=WorkflowFieldResponse)
async def workflow_submit(request: WorkflowFieldSubmit):
    result = workflow_engine.submit_field(
        request.session_id, request.workflow_id, request.field_name, request.field_value
    )
    return WorkflowFieldResponse(**result)


@app.get("/api/tickets")
async def get_tickets():
    tickets = audit.get_open_tickets(limit=50)
    return {"tickets": tickets}


@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, notes: str = ""):
    success = audit.resolve_ticket(ticket_id, notes)
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"success": True}


@app.get("/api/graph/stats")
async def graph_stats():
    from app import knowledge_graph
    stats = knowledge_graph.get_stats()
    stats["loaded"] = knowledge_graph.is_loaded()
    return stats


@app.post("/api/system/llm-toggle")
async def llm_toggle(enabled: bool = True):
    from app import llm as llm_module
    llm_module.set_llm_available(enabled)
    return {"llm_available": enabled}


@app.get("/api/health")
async def health():
    from app.vector_store import collection_count
    from app import knowledge_graph
    graph_s = knowledge_graph.get_stats()
    return {
        "status": "ok",
        "service": "Mneme Healthcare Operations Assistant",
        "documents_indexed": collection_count(),
        "knowledge_graph": {
            "loaded": knowledge_graph.is_loaded(),
            "nodes": graph_s["total_nodes"],
            "edges": graph_s["total_edges"],
        },
    }
