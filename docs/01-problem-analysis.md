# Problem Analysis & Domain Context

## 1. Hackathon & Enterprise Context
- **Host:** Acentra Health (Merger of CNSI & Kepro) | BUILD TO CARE 2026 Hackathon
- **Domain Focus:** Government healthcare IT, state Medicaid Management Information Systems (MMIS, e.g., `evoBrix X™`), utilization review and care management (`Atrezzo™`), CMS/HHS compliance.
- **Challenge:** Operational bottlenecks in back-office healthcare administration (intake coordination, claims exception handling, prior authorizations, care management routing).

---

## 2. Problem Statement Breakdown

### Target Personas
| Role | Primary Responsibilities | Common Pain Points |
| :--- | :--- | :--- |
| **Intake Coordinator (Front Desk / Registration)** | Patient registration, insurance eligibility verification, basic prior authorization submission. | Incomplete intake forms, missing clinical attachments, confusion over state-specific Medicaid submission guidelines. |
| **Claims Processor** | Claims adjudication, billing discrepancy review, denial code triage. | Complex matrix rules (e.g., CPT/HCPCS modifiers, timely filing limits), high denial rates from missing fields. |
| **Care Manager** | Utilization review, high-risk patient routing, chronic care coordination. | SOP ambiguity, misrouting clinical requests to non-clinical staff, slow turnaround times. |
| **Operations Supervisor** | Human-in-the-loop escalation handling, denial overrides, quality assurance. | Lack of summarized ticket context during handoffs, manual digging across fragmented SOP workbooks. |

---

## 3. Strict Scope & Guardrails (The Operational Boundary)

```
       [ IN SCOPE: Healthcare Operations ]         |    [ STRICT OUT OF SCOPE: Clinical ]
===================================================|==========================================
 - Procedure/SOP clarification                     | - Medical diagnoses & symptom triage
 - Deterministic field validation & schema prompts  | - Prescriptions, dosage changes, therapies
 - Policy matrix lookup (CPT, State, Auth limits)   | - Medical necessity clinical determinations
 - RBAC & clearance-based document access          | - Direct claims payout without supervisor
 - Automated context packs for human escalations   | - Black-box automated denial/override
```

### Non-Negotiable Guardrails:
1. **Zero Clinical Advice:** Strictly detect and intercept any clinical/diagnostic prompts, immediately redirecting to human clinical staff.
2. **Zero State Mutation Autopilot:** The copilot guides and validates, but administrative state changes (e.g., final claim payout, manual policy denial override) require authenticated human sign-off.
3. **Deterministic Source Grounding:** Every statement and field prompt must cite down to the exact SOP Document, Section, or Policy Matrix Row ID. If the reference workbook lacks the answer, the copilot must explicitly output *Uncertainty Flagged* rather than inferring.
4. **Strict RBAC:** Operational files are partitioned by clearance level (e.g., Front Desk Clerk cannot query Executive Claims Denial Overrides).
