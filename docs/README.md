# Healthcare Operations Assistant — Engineering Documentation Index

> **Classification:** Hospital Operations & Governance Architecture  
> **Accreditation & Compliance Target:** NABH 5th Edition (CQI.1 & CQI.2), HIPAA Security & Privacy (45 CFR § 164.312 / 164.502), ISO 27799  
> **Paradigm:** Deterministic Knowledge Graph (GraphRAG) + Finite State Machine + Grounded In-Context Synthesis

---

## 📚 Documentation Suite (SDLC Structure)

This directory provides the complete System Development Life Cycle (SDLC) architectural documentation for the Healthcare Operations Assistant.

| Document | Purpose & Scope |
| :--- | :--- |
| **[01. Problem & Requirements Specification](file:///home/kabe/Competions/BTC/docs/01_PROBLEM_REQUIREMENTS_SPECIFICATION.md)** | Root-cause analysis of hospital operational fragmentation, the 15 hospital operational roles, the 5 core operational questions (What, Where, What Next, Who, How), trust hierarchy, and the 4 deterministic outcomes. |
| **[02. System Architecture & Engineering Design](file:///home/kabe/Competions/BTC/docs/02_SYSTEM_ARCHITECTURE_DESIGN.md)** | 3-Layer mental model, C4 architecture diagrams, the 7-step deterministic/probabilistic orchestrator pipeline, programmatic Pydantic gateways, and cryptographic trust envelopes. |
| **[03. Knowledge Graph & Ontology Specification](file:///home/kabe/Competions/BTC/docs/03_KNOWLEDGE_GRAPH_AND_ONTOLOGY.md)** | Formal graph schema (nodes, typed edges, attributes), DAG sequential precedence (`precedes`), cycle mitigation, supernode degree capping, and change-impact backlink traversals. |
| **[04. Guided Workflows & Routing Engine](file:///home/kabe/Competions/BTC/docs/04_WORKFLOW_STATE_MACHINE_AND_ROUTING.md)** | State-machine specifications for routine operations, field definition schemas, validation rules, golden-path MRI pre-authorization walkthrough, and escalation ticket lifecycle. |
| **[05. Architectural Decisions & FAQs ("Why Not This?")](file:///home/kabe/Competions/BTC/docs/05_ARCHITECTURAL_DECISIONS_AND_FAQS.md)** | Comprehensive architectural defense in Q&A format: Why GraphRAG vs Vector RAG, why local vs cloud, why pre-retrieval RBAC, why deterministic guards, cloud migration blueprints, and edge cases. |

---

## 🏛️ Core Architectural Tenet

$$\text{Architecture Tenet: } \mathbf{\text{LLM Reasons, Rules Decide.}}$$

In hospital operations, **probabilistic generative models must never be granted autonomous authority** to determine policy, evaluate authorization, route sensitive incidents, or approve irreversible transactions. The LLM is restricted to semantic understanding and grounded text generation; all governance, access boundaries, state transitions, and audit trails are enforced by **deterministic, mathematically verifiable code**.
