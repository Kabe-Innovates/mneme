# Technical Implementation Roadmap

## 1. Architectural Philosophy: The Neuro-Symbolic "Second Brain"
To win at Acentra Health's AI CoE evaluation:
- We **do not** build another toy chatbot or vanilla RAG wrapper.
- We build an **Enterprise Healthcare Operations Copilot** that combines:
  1. **Neural LLM Reasoning:** For natural language understanding, sentiment/urgency analysis, and contextual summary generation.
  2. **Symbolic Deterministic Engine:** For schema validation, matrix lookup, missing field detection, RBAC access control, and zero-hallucination citation enforcement.

---

## 2. Phased Execution Plan (Hackathon Timeline)

### Phase 1: Knowledge Substrate & Synthetic Workbooks (Data Layer)
- [x] Operational specification for Prior Auth matrices, Claims Adjudication matrices, and Field Schemas (`docs/04-synthetic-workbooks-spec.md`).
- [ ] Create synthetic data files in `data/`:
  - `data/matrices/prior_auth_matrix.csv`
  - `data/matrices/claims_adjudication_matrix.csv`
  - `data/schemas/form_field_schemas.json`
  - `data/sops/*.md` (SOPs with explicit headers, section IDs, and clearance metadata).
- [ ] Implement Fast In-Memory Second Brain Substrate (Indexing documents, sections, and matrix rows with metadata-aware retrieval and RBAC clearance tags).

### Phase 2: Core Neuro-Symbolic Engine & Guardrails (Logic Layer)
- [ ] **Guardrails Interceptor:**
  - Clinical query detector (regex + semantic zero-shot classifier) $\to$ Hard block with clinical handoff.
  - State mutation blocker (flags any write/finalize action without supervisor signature).
  - RBAC barrier (blocks cross-role document leakage).
- [ ] **Stepwise Form State Machine & Missing Field Evaluator:**
  - Ingests partial form parameters.
  - Evaluates against target schema deterministically.
  - Generates clear, precise prompts for missing values (e.g., *"Missing required fields: Servicing NPI, Primary ICD-10"*).
- [ ] **Confidence Calibrator & Urgency/Sentiment Scorer:**
  - Calibrated score: Symbolic match (0.6) + Semantic relevance (0.4) - penalty for missing required parameters.
  - Urgency classification (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and sentiment detection.

### Phase 3: Human-in-the-Loop (HITL) & Immutable Audit Trail (Governance Layer)
- [ ] **Automated Escalation Context Pack Generator:**
  - Structured handoff JSON & formatted markdown when confidence $< 0.80$, clinical questions arise, or high-dollar thresholds are breached.
- [ ] **Supervisor Triage Queue:**
  - Holds escalated tickets awaiting manual review or override.
- [ ] **Immutable Audit Ledger:**
  - JSONL / cryptographic hash-linked audit log recording timestamp, actor role, query, citations, decisions, confidence, and overrides.

### Phase 4: Operational Copilot Interface & Full Integration (App Layer)
- [ ] Lightweight, blazing-fast backend (FastAPI / Python 3.12).
- [ ] Interactive Operator Dashboard:
  - Role switcher (`Front Desk`, `Claims Processor`, `Care Manager`, `Supervisor`).
  - Active Copilot chat with stepwise interactive form fields.
  - Real-time row-level source citation inspector.
  - Live Supervisor Escalation Queue.
  - Audit Trail inspection tab.

### Phase 5: Demo Verification & Judge Walkthrough
- [ ] Scenario A: Front Desk intake for surgical prior-auth (stepwise missing field collection $\to$ validation $\to$ row-level citation).
- [ ] Scenario B: Claims Processor reviewing `CO-16` / `CO-29` denial with timely filing matrix rule.
- [ ] Scenario C: Guardrail intercept on a clinical diagnosis prompt (*"What dosage of lisinopril should the patient take?"* $\to$ immediate clinical deflection).
- [ ] Scenario D: High-dollar exception escalation ($30,000 biologic) $\to$ automated supervisor context pack $\to$ supervisor sign-off.
