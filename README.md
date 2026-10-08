# Mneme — Healthcare Operations Assistant

> **Enterprise Neuro-Symbolic "Second Brain" for Hospital & Healthcare Operations**  
> **Standards Alignment:** NABH 5th Edition (CQI.1 & CQI.2), HIPAA Security & Privacy (45 CFR § 164.312 / 164.502), ISO 27799  
> **Core Tenet:** *LLM Reasons, Rules Decide.*

---

## 🏛️ Executive Overview

A hospital employee needing to authorize an MRI, correct a billing code, or request system access must navigate fragmented procedures across 15 operational personas and heterogeneous software silos (HIS, EMR, LIS, RIS, PACS, ERP). 

**Mneme** is not a chatbot; it is a **Deterministic Second Brain** that links procedures, forms, workflow systems, teams, and escalation paths into a navigable Knowledge Graph. It resolves every operational request into one of four deterministic outcomes:
1. **ANSWER**: Grounded, verifiable answers with exact source citations and confidence metrics.
2. **GUIDE**: Interactive state-machine workflows for routine operational tasks (e.g., MRI pre-authorization), prompting only for missing required fields.
3. **ROUTE**: Context-rich escalation tickets dispatched to the correct department queue with urgency ratings and tried steps.
4. **REFUSE / ESCALATE SAFELY**: Immediate deterministic deflection of clinical advice requests, access violations, or prompt injections.

---

## 🏗️ 3-Layer Architecture

```
┌───────────────────────────────────────────────────────────────┐
│  3. DECISION LAYER  — "what should I do with this?"           │
│     ANSWER · GUIDE · ROUTE · REFUSE   (+ Merkle Audit Trail)  │
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

- [**01. Problem & Requirements Specification**](docs/01_PROBLEM_REQUIREMENTS_SPECIFICATION.md): Deep-dive into the 15 hospital operational roles, the 5 core operational questions (What, Where, What Next, Who, How), trust hierarchy, and the 4 target outcomes.
- [**02. System Architecture & Engineering Design**](docs/02_SYSTEM_ARCHITECTURE_DESIGN.md): 3-Layer mental model, C4 container diagram, 7-step orchestrator pipeline, programmatic Pydantic data contracts, and mathematical verification scoring ($S_{\text{total}}$).
- [**03. Knowledge Graph & Ontology Specification**](docs/03_KNOWLEDGE_GRAPH_AND_ONTOLOGY.md): Extended 12-node, 11-edge ontology, DAG sequential precedence (`precedes`), supernode degree capping, and change-impact backlink analysis.
- [**04. Guided Workflows & Routing Engine**](docs/04_WORKFLOW_STATE_MACHINE_AND_ROUTING.md): State-machine specifications for routine operations, field definition schemas, validation rules, golden-path MRI pre-authorization walkthrough, and escalation ticket lifecycle.
- [**05. Architectural Decisions & FAQs ("Why Not This?")**](docs/05_ARCHITECTURAL_DECISIONS_AND_FAQS.md): Detailed architectural defense in Q&A format covering Cloud vs. Edge, GraphRAG vs. Vector RAG, Pre-Retrieval RBAC, Merkle audit chains, and offline disaster recovery.

---

## 🔒 Healthcare Governance & Compliance

- **Pre-Retrieval RBAC**: Access boundaries enforced at the database query level (`WHERE role IN node.visible_to`) before vector matching or graph expansion to prevent unauthorized context leakage.
- **Controlled Document Triad (NABH CQI.1)**: Every procedure requires controlled ID, semantic version, effective date, review due date, and approved status.
- **Tamper-Evident Audit Trail (HIPAA § 164.312)**: Every interaction writes to an append-only log signed with an HMAC-SHA256 Merkle chain.
- **Deterministic Clinical Boundary**: 100% regex and rule-based deflection of clinical diagnostic and medication queries.
