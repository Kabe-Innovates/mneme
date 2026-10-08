# Mneme — Healthcare Operations Assistant

> **Enterprise Neuro-Symbolic "Second Brain" for Hospital & Healthcare Operations**  
> **Standards Alignment:** NABH 5th Edition (CQI.1 & CQI.2), HIPAA Security & Privacy (45 CFR § 164.312 / 164.502), ISO 27799  
> **Core Tenet:** *LLM Reasons, Rules Decide.*

---

## ⚠️ Synthetic Data Only Declaration

> **All data in this system is strictly synthetic.**
> No real patient, member, provider, employee, production, or confidential client data is used at any stage. All hospital names, insurer entities, policy codes, and operational scenarios are fictional and generated purely for demonstration and evaluation purposes.

---

## 🏛️ Executive Overview

A hospital employee needing to authorize an MRI, correct a billing code, or request system access must navigate fragmented procedures across 15 operational personas and heterogeneous software silos (HIS, EMR, LIS, RIS, PACS, ERP). 

**Mneme** is not a chatbot; it is a **Deterministic Second Brain** that links procedures, forms, workflow systems, teams, and escalation paths into a navigable Knowledge Graph. It resolves every operational request into one of four deterministic outcomes:
1. **ANSWER**: Grounded, verifiable answers with exact source citations and confidence metrics.
2. **GUIDE**: Interactive state-machine workflows for routine operational tasks (e.g., MRI pre-authorization), prompting only for missing required fields without making assumptions.
3. **ROUTE**: Context-rich escalation tickets dispatched to the correct department queue with urgency ratings, tried steps, and reasons.
4. **REFUSE / ESCALATE SAFELY**: Immediate deterministic deflection of clinical advice requests, access violations, or prompt injections.

---

## 🤖 Cloud Backbone: AWS Bedrock

The system utilizes **AWS Bedrock** for enterprise-grade, HIPAA-eligible foundation model inference:

| Component | Model ID | Operational Function | Compliance Status |
| :--- | :--- | :--- | :--- |
| **Primary LLM** | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Structured intent extraction (Step 2) & Grounded answer generation (Step 6) | ✅ HIPAA-eligible under AWS BAA |
| **Fast Guard Model** | `anthropic.claude-3-haiku-20240307-v1:0` | Sub-200ms edge-case clinical disambiguation fallback (Step 1) | ✅ HIPAA-eligible, low latency |
| **Vector Embeddings** | `amazon.titan-embed-text-v2:0` | 1024-dimension dense vector indexing for hybrid retrieval (Step 3) | ✅ HIPAA-eligible, zero retention |

---

## 🔒 System Boundaries & Operational Scope

| System Can Do | System Cannot Do |
| :--- | :--- |
| ✅ Find current, approved procedures with source citations | ❌ **Provide medical advice, diagnosis, or drug dosing** |
| ✅ Guide routine multi-step operational workflows | ❌ Access confidential patient records or financial credentials |
| ✅ Incrementally collect missing required parameters | ❌ Authorize irreversible actions without supervisor approval |
| ✅ Route complex exceptions to correct human departments | ❌ Bypass role-based security controls under any framing |
| ✅ Explicitly communicate uncertainty & knowledge gaps | ❌ Generate answers from expired or unapproved SOPs |

---

## 🏗️ 3-Layer Architecture

```
┌───────────────────────────────────────────────────────────────┐
│  3. DECISION LAYER  — "what should I do with this?"           │
│     ANSWER · GUIDE · ROUTE · REFUSE   (+ Audit Trail)         │
├───────────────────────────────────────────────────────────────┤
│  2. KNOWLEDGE GRAPH — "how does everything connect?"          │
│     procedures · documents · forms · systems · teams · roles  │
├───────────────────────────────────────────────────────────────┤
│  1. SOURCE DATA  — "what do we know, and is it trusted?"      │
│     synthetic workbook (requests, articles, workflows,        │
│     routing rules, field definitions) with trust metadata     │
└───────────────────────────────────────────────────────────────┘
```

---

## 📚 SDLC Architectural Documentation

Complete engineering specifications are available in the [`docs/`](docs/) directory:

- [**01. Problem & Requirements Specification**](docs/01_PROBLEM_REQUIREMENTS_SPECIFICATION.md): Deep-dive into the 15 hospital operational roles, the 5 core operational questions (What, Where, What Next, Who, How), trust hierarchy, synthetic data declaration, and system self-disclosure.
- [**02. System Architecture & Engineering Design**](docs/02_SYSTEM_ARCHITECTURE_DESIGN.md): 3-Layer mental model, C4 container diagram, 7-step orchestrator pipeline, AWS Bedrock configuration, sentiment detection, uncertainty UX bands, and append-only audit trail.
- [**03. Knowledge Graph & Ontology Specification**](docs/03_KNOWLEDGE_GRAPH_AND_ONTOLOGY.md): Extended 12-node, 11-edge ontology, DAG sequential precedence (`precedes`), supernode degree capping, and change-impact backlink analysis.
- [**04. Guided Workflows & Routing Engine**](docs/04_WORKFLOW_STATE_MACHINE_AND_ROUTING.md): State-machine specifications, field definitions, MRI pre-authorization walkthrough (happy path + uncertainty gap), and Agent Dashboard specifications.
- [**05. Architectural Decisions & FAQs ("Why Not This?")**](docs/05_ARCHITECTURAL_DECISIONS_AND_FAQS.md): Detailed architectural defense in Q&A format covering Cloud vs. Edge, AWS Bedrock, GraphRAG vs. Vector RAG, Pre-Retrieval RBAC, and offline disaster recovery.
- [**06. Data Ingestion & Workbook Mapping**](docs/06_DATA_INGESTION_AND_WORKBOOK_MAPPING.md): Tabular workbook schema specifications for all 5 sheets, node/edge transformation pipeline, SQLite/Chroma ingestion logic, and contingency synthetic data generation.
- [**07. Data Lifecycle, Retention & Edge Cases**](docs/07_DATA_LIFECYCLE_RETENTION_AND_EDGE_CASES.md): 6-tier data lifecycle matrix, encounter-driven eviction (discharge edge case), mid-shift handovers, downtime procedure mode, and catalog of 15 enterprise operational edge cases.

---

## 🛡️ Healthcare Governance & Compliance

- **Pre-Retrieval RBAC**: Access boundaries enforced at the database query level (`WHERE role IN node.visible_to`) before vector matching or graph expansion to prevent unauthorized context leakage.
- **Controlled Document Triad (NABH CQI.1)**: Every procedure requires controlled ID, semantic version, effective date, review due date, and approved status.
- **Append-Only Audit Trail (HIPAA § 164.312)**: Every interaction writes to an immutable SQLite audit log with UUID tracking (with Merkle-chain hashing specified for production).
- **Deterministic Clinical Boundary**: 100% regex and rule-based deflection of clinical diagnostic and medication queries.
