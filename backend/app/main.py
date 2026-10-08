from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

from app.models import ChatRequest, OrchestratorResponse, HOSPITAL_ROLES
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


@app.get("/api/health")
async def health():
    from app.vector_store import collection_count
    return {
        "status": "ok",
        "service": "Mneme Healthcare Operations Assistant",
        "documents_indexed": collection_count(),
    }
