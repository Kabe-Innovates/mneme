<div align="center">

# Mneme <sub>(ம்னீமி)</sub>

**/nee-mee/** · *noun* · Greek

### Deterministic Second Brain for Hospital Operations

Turn fragmented hospital procedures into grounded, verifiable answers,
interactive workflows, and context-rich escalations — so staff find
what they need before patients feel the delay.

<sub>Built for the **BTC "Build to Care" Healthcare Hackathon**</sub>

</div>

> *"LLM Reasons, Rules Decide."* — The system's core tenet. Every response
> traces back to approved SOPs, never to model imagination.

---

## Overview

Hospital staff across 15 operational roles navigate fragmented procedures,
forms, and software silos daily. Mneme links all of it — procedures, teams,
systems, escalation paths — into a navigable Knowledge Graph backed by
AWS Bedrock, and resolves every request into one of four deterministic outcomes:

| Outcome | What Happens |
|---|---|
| **ANSWER** | Grounded response with exact SOP citations and confidence score |
| **GUIDE** | Interactive step-by-step workflow, prompting only for missing fields |
| **ROUTE** | Escalation ticket to the correct department with priority and context |
| **REFUSE** | Immediate deflection of clinical, injection, or out-of-scope requests |

All data in this system is **strictly synthetic**. No real patient, provider,
or confidential data is used at any stage.

---

## Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │            React + Vite Frontend            │
                         │  Chat · Workflows · Operations Hub (5 tabs) │
                         └──────────────────┬──────────────────────────┘
                                            │ JWT + Bearer
                         ┌──────────────────▼──────────────────────────┐
                         │           FastAPI Backend (v2.0)            │
                         │  Rate Limiter · CORS · Auth Middleware      │
                         └──────┬────────┬────────┬────────┬──────────┘
                                │        │        │        │
                    ┌───────────▼──┐  ┌──▼─────┐  │  ┌─────▼─────────┐
                    │  3-Layer     │  │ Pure   │  │  │  HMAC-Chained │
                    │  Guard       │  │decide()│  │  │  Audit Trail  │
                    │  System      │  │ Engine │  │  │  (SHA-256)    │
                    └──────────────┘  └────────┘  │  └───────────────┘
                                                  │
              ┌───────────────────────────────────┼───────────────────┐
              │                                   │                   │
     ┌────────▼────────┐               ┌─────────▼──────┐   ┌───────▼───────┐
     │   ChromaDB       │               │  NetworkX       │   │ AWS Bedrock   │
     │   Vector Store   │               │  Knowledge      │   │ Claude 3.5    │
     │   (Titan embed)  │               │  Graph          │   │ Sonnet        │
     └─────────────────┘               └────────────────┘   └───────────────┘
```

---

## Security Model

| Layer | Mechanism |
|---|---|
| **Input Guard** | 25 clinical patterns, 15 injection patterns, Unicode confusable normalization, PII vault extraction |
| **Retrieval Guard** | Scans retrieved KB documents for indirect prompt injection |
| **Output Guard** | Verifies no extracted PII leaks into generated responses |
| **Authentication** | JWT (HS256) with 8-hour shift-based expiry, 16 synthetic hospital roles |
| **Audit Trail** | HMAC-SHA256 chained log — tamper on any entry breaks the chain |
| **Rate Limiting** | 30 req/min chat, 10 req/min login via slowapi |
| **Circuit Breaker** | Self-healing LLM degradation (5 failures / 30s recovery) with template fallback |
| **Decision Engine** | Pure deterministic `decide()` — no I/O, no LLM, 100% testable (65 tests) |

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons |
| **Backend** | Python 3.12, FastAPI, PyJWT, slowapi, SQLite |
| **AI / ML** | AWS Bedrock (Claude 3.5 Sonnet, Titan Embeddings v2) |
| **Retrieval** | ChromaDB (vector), NetworkX (knowledge graph with trust scoring) |
| **Infrastructure** | Docker Compose, nginx |

---

## Quick Start

### Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your AWS + JWT keys
uvicorn app.main:app --reload # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

### Docker

```bash
docker compose up --build
# API → http://localhost:8000  |  UI → http://localhost:80
```

### Run Tests

```bash
cd backend
python -m pytest tests/ -v    # 65 tests, ~0.1s
```

Demo credentials: `front_office` / `mneme2024`

---

## Operations Hub

The supervisor dashboard exposes five tabs:

- **Escalation Queue** — Live tickets with priority, SLA tracking, and resolution notes
- **Knowledge Vault** — Versioned SOP index with draft/approved status and ingestion log
- **Audit Trail** — HMAC chain verification with integrity badge and violation details
- **Knowledge Gaps** — Queries the system couldn't answer, surfaced for KB improvement
- **Demo Scenarios** — One-click injection of realistic hospital events (Code Blue, MRI failure, billing dispute)

---

## Repository Structure

```
.
├── frontend/                  # React + Vite UI
│   ├── src/components/        # Chat, workflows, dashboard, login
│   ├── src/api.ts             # JWT-authenticated API layer
│   └── src/types.ts           # Shared TypeScript interfaces
├── backend/
│   ├── app/                   # FastAPI application
│   │   ├── orchestrator.py    # 5-step pipeline (Guard → Classify → Decide → Generate → Verify)
│   │   ├── decide.py          # Pure deterministic decision engine
│   │   ├── guards.py          # 3-layer guard system with PII vault
│   │   ├── audit.py           # HMAC-chained audit trail
│   │   ├── auth.py            # JWT authentication
│   │   ├── llm.py             # Bedrock client with circuit breaker
│   │   ├── knowledge_graph.py # NetworkX graph with trust scoring
│   │   ├── vector_store.py    # ChromaDB hybrid retrieval
│   │   └── scenarios.py       # Demo scenario injection
│   ├── data/                  # 48 articles, 15 workflows, 23 routing rules
│   ├── knowledge_vault/       # Versioned SOP store (63 documents)
│   └── tests/                 # 65 deterministic tests
├── docs/                      # 7 SDLC architecture documents
├── docker-compose.yml
└── Dockerfile.backend / Dockerfile.frontend
```

---

## Compliance Alignment

| Standard | Implementation |
|---|---|
| **HIPAA § 164.312** | HMAC-chained audit, in-memory token storage (no localStorage), PII vault redaction |
| **HIPAA § 164.502** | Pre-retrieval RBAC, role-scoped vector queries, no PHI in logs |
| **NABH CQI.1** | Controlled document triad (ID, version, effective date) on all SOPs |
| **ISO 27799** | Fail-closed guards, rate limiting, circuit breaker, JWT expiry |

---

## Team
- Ranen Joseph Solomon
- Thirumurugan K
- Jaiyantan S
- Kabelan G K

---

## License

Released under the [MIT License](LICENSE).
