# Acentra Health — AI-Powered Healthcare Operations Assistant
### BUILD TO CARE 2026 Hackathon | Problem Statement 1

> **An Enterprise Neuro-Symbolic "Second Brain" Copilot for Healthcare Back-Office Administration**  
> Designed for Medicaid MMIS, CMS Compliance, Prior Authorizations, and Claims Exception Adjudication.

---

## 🏛️ Executive Architecture Summary

Healthcare operational workflows (claims processing, prior authorizations, Medicaid intake) cannot tolerate the hallucinations, boundary fuzziness, or stateless nature of vanilla RAG. Acentra Health's core platforms (`evoBrix X™`, `Atrezzo™`) demand deterministic rule execution, row-level policy provenance, and strict compliance boundaries.

Instead of a generic chatbot, this project implements a **Neuro-Symbolic Second Brain**:
- **Symbolic Rules Engine:** Guarantees 100% deterministic schema validation, policy matrix lookups, missing field detection, and Role-Based Access Control (RBAC).
- **Neural Semantic Co-Processor:** Powers natural language understanding, operator intent parsing, sentiment/urgency prioritization, and supervisor escalation summaries.
- **Tri-Layer Memory:** Working Memory (active form state machine), Procedural Memory (SOP workbooks & routing matrices), and Episodic Memory (audit ledger & escalation history).

---

## 📚 Architectural Documentation

All detailed specifications are organized under the [`docs/`](docs/) directory:

1. [**01. Problem Analysis & Domain Context**](docs/01-problem-analysis.md): Target personas, core objectives, and strict operational boundaries (no clinical advice, no unauthorized mutations).
2. [**02. Second Brain vs. Traditional RAG**](docs/02-second-brain-vs-rag.md): Deep-dive into why vector RAG fails in healthcare operations and how the Second Brain's neuro-symbolic memory model solves it.
3. [**03. System Architecture & Dataflow**](docs/03-system-architecture.md): End-to-end component breakdown, Mermaid dataflow diagrams, RBAC layers, and audit provenance.
4. [**04. Synthetic Workbooks Specification**](docs/04-synthetic-workbooks-spec.md): Schema definitions for Virginia/Maryland Medicaid prior auth, claims adjudication matrices, and SOP knowledge bases.
5. [**05. Technical Implementation Roadmap**](docs/05-implementation-roadmap.md): 5-phase execution plan for the 24-36 hour hackathon.
