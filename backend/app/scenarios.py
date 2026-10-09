"""
Demo Scenario Injection
=======================
Pre-built hospital scenarios that inject realistic escalation tickets
and audit log entries for live demos. Each scenario simulates a
real-world operational event.

Adopted from Jaiyantan's scenario injection concept.
"""

from app import audit

SCENARIOS = {
    "code_blue": {
        "name": "Code Blue — ICU Emergency",
        "description": "Critical cardiac arrest event in ICU Bay 4. Triggers clinical boundary enforcement and emergency escalation.",
        "tickets": [
            {
                "target_team": "ICU Nursing Supervisor",
                "priority": "CRITICAL",
                "summary": "Code Blue activated in ICU Bay 4 — Patient MRN-[REDACTED] cardiac arrest. Crash cart deployed, attending physician paged.",
                "escalation_reason": "Clinical emergency — requires immediate medical staff response. Mneme cannot provide clinical guidance.",
                "is_gap": False,
            },
            {
                "target_team": "Biomedical Engineering",
                "priority": "URGENT",
                "summary": "Post-Code Blue equipment check required: defibrillator unit ICU-DEF-03, ventilator ICU-VENT-07.",
                "escalation_reason": "Equipment verification after emergency use per SOP-BIOMED-005.",
                "is_gap": False,
            },
        ],
    },
    "equipment_failure": {
        "name": "MRI Scanner Down",
        "description": "MRI Scanner #2 offline. Triggers biomedical engineering escalation and appointment rescheduling workflow.",
        "tickets": [
            {
                "target_team": "Biomedical Engineering",
                "priority": "URGENT",
                "summary": "MRI Scanner #2 (Siemens MAGNETOM Vida) reporting error code E-4401: gradient coil overtemperature. Machine taken offline.",
                "escalation_reason": "Critical imaging equipment failure — 12 scheduled scans affected today.",
                "is_gap": False,
            },
            {
                "target_team": "Radiology Front Desk",
                "priority": "URGENT",
                "summary": "Reschedule 12 MRI appointments from Scanner #2. Redistribute to Scanner #1 and #3 where possible.",
                "escalation_reason": "Patient appointment impact from equipment downtime.",
                "is_gap": False,
            },
            {
                "target_team": "IT Help Desk",
                "priority": "ROUTINE",
                "summary": "Update PACS integration status for MRI Scanner #2 — mark offline in scheduling system.",
                "escalation_reason": "System status sync required to prevent new bookings.",
                "is_gap": False,
            },
        ],
    },
    "billing_dispute": {
        "name": "High-Value Billing Dispute",
        "description": "Patient disputes $8,500 surgery charge. Triggers supervisor approval gate and billing correction workflow.",
        "tickets": [
            {
                "target_team": "Billing Supervisor",
                "priority": "URGENT",
                "summary": "Billing correction request: Patient [REDACTED] disputes charge of $8,500 for procedure CPT-27447 (Total knee replacement). Insurance EOB shows approved amount of $6,200.",
                "escalation_reason": "Amount exceeds $500 threshold — requires supervisor approval per SOP-BILL-022.",
                "is_gap": False,
            },
            {
                "target_team": "Insurance Verification",
                "priority": "ROUTINE",
                "summary": "Verify insurance coverage details for policy [REDACTED]. EOB discrepancy of $2,300 between billed and approved amounts.",
                "escalation_reason": "Insurance verification needed before billing adjustment.",
                "is_gap": False,
            },
        ],
    },
    "knowledge_gap": {
        "name": "Knowledge Gap Burst",
        "description": "Simulates queries the system couldn't answer, demonstrating the knowledge gap capture feature.",
        "tickets": [
            {
                "target_team": "Operations Help Desk",
                "priority": "ROUTINE",
                "summary": "What is the procedure for handling radioactive waste from nuclear medicine?",
                "escalation_reason": "Low trust score (32%) — knowledge gap or conflicting sources",
                "is_gap": True,
            },
            {
                "target_team": "Operations Help Desk",
                "priority": "ROUTINE",
                "summary": "How do I submit a workers compensation claim for a needle stick injury?",
                "escalation_reason": "Query not covered in available knowledge base",
                "is_gap": True,
            },
            {
                "target_team": "Pharmacy",
                "priority": "ROUTINE",
                "summary": "What is the policy for dispensing controlled substances to outpatients?",
                "escalation_reason": "Low classification confidence — human review required",
                "is_gap": True,
            },
        ],
    },
}


def list_scenarios() -> list[dict]:
    return [
        {"id": sid, "name": s["name"], "description": s["description"], "ticket_count": len(s["tickets"])}
        for sid, s in SCENARIOS.items()
    ]


def inject_scenario(scenario_id: str, session_id: str, role: str = "supervisor") -> dict:
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return {"success": False, "error": f"Unknown scenario: {scenario_id}"}

    created_tickets = []
    for t in scenario["tickets"]:
        ticket_id = audit.create_ticket(
            session_id=session_id,
            initiator_role=role,
            target_team=t["target_team"],
            priority=t["priority"],
            summary=t["summary"],
            escalation_reason=t["escalation_reason"],
            is_gap=t.get("is_gap", False),
        )
        created_tickets.append(ticket_id)

    return {
        "success": True,
        "scenario": scenario["name"],
        "tickets_created": len(created_tickets),
        "ticket_ids": created_tickets,
    }
