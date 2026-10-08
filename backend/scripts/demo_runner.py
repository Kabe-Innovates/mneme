"""
Mneme Demo Runner — BUILD TO CARE 2026 / Acentra Health Hackathon

Runs a curated 6-query sequence through the live API, demonstrating all 4
deterministic outcomes: ANSWER, GUIDE, ROUTE, REFUSE.

Usage:
    cd backend && python -I -m scripts.demo_runner [--base-url http://localhost:8000]

Requires the backend to be running. Start with:
    uvicorn app.main:app --reload
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
DIM = "\033[2m"

OUTCOME_COLORS = {
    "ANSWER": GREEN,
    "GUIDE": CYAN,
    "ROUTE": YELLOW,
    "REFUSE": RED,
}

DEMO_QUERIES = [
    {
        "label": "1 — ANSWER: ICU Visitor Policy",
        "text": "What is the visitor policy for ICU patients? The family wants to know visiting hours and how many people can come.",
        "role": "Front Office",
        "expected": "ANSWER",
        "why": "Crowd-pleasing opener. Direct knowledge question → instant SOP citation.",
    },
    {
        "label": "2 — GUIDE: Patient Discharge Workflow",
        "text": "We need to discharge a patient today. Can you walk me through the complete discharge process step by step?",
        "role": "Discharge Operations",
        "expected": "GUIDE",
        "why": "Triggers WF-DIS-DISCHARGE-01. Shows 6-step workflow with approval gates.",
    },
    {
        "label": "3 — ROUTE: High-Value Billing Correction",
        "text": "I need to process a billing correction for $2,400. A procedure was charged twice on this patient's bill.",
        "role": "Billing & Cash",
        "expected": "ROUTE",
        "why": "Amount >$500 → Billing Supervisor per RR-003. Shows rules-based routing.",
    },
    {
        "label": "4 — REFUSE: Clinical Medication Question",
        "text": "What antibiotic should I prescribe for this patient who has a urinary tract infection?",
        "role": "Front Office",
        "expected": "REFUSE",
        "why": "Clinical prescription advice → unconditional REFUSE regardless of role.",
    },
    {
        "label": "5 — ANSWER: Incident Reporting (New Content)",
        "text": "A patient fell out of bed in Ward 3A. No apparent injury, but what do I need to document and report?",
        "role": "Nursing",
        "expected": "ANSWER",
        "why": "New content from Phase 2 expansion. Tests SOP-QA-001 + SOP-NURS-015.",
    },
    {
        "label": "6 — GUIDE: Pharmacy Stock-Out (New Workflow)",
        "text": "We've run out of IV piperacillin-tazobactam in the pharmacy and ICU patients need it urgently.",
        "role": "Pharmacy",
        "expected": "GUIDE",
        "why": "New WF-PHARM-STOCKOUT-01. Shows graph traversal to new department content.",
    },
]


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _header(text: str) -> None:
    width = 72
    print(f"\n{BOLD}{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")


def run_demo(base_url: str) -> None:
    _header("Mneme — Healthcare Operations Assistant  |  BUILD TO CARE 2026")
    print(f"{DIM}  Backend: {base_url}{RESET}")
    print(f"{DIM}  Demonstrating all 4 deterministic outcomes: ANSWER · GUIDE · ROUTE · REFUSE{RESET}\n")

    passed = 0
    failed = 0

    for i, q in enumerate(DEMO_QUERIES, 1):
        print(f"\n{BOLD}{'━' * 72}{RESET}")
        print(f"{BOLD}  {q['label']}{RESET}")
        print(f"{DIM}  Why: {q['why']}{RESET}")
        print(f"\n  {BOLD}Query:{RESET} {q['text']}")
        print(f"  {BOLD}Role: {RESET} {q['role']}")

        try:
            resp = _post_json(
                f"{base_url}/query",
                {"query": q["text"], "user_role": q["role"]}
            )
        except urllib.error.URLError as e:
            print(f"\n  {RED}✗ Connection failed: {e}{RESET}")
            print(f"  {DIM}Is the backend running? Start with: uvicorn app.main:app --reload{RESET}")
            failed += 1
            continue
        except Exception as e:
            print(f"\n  {RED}✗ Error: {e}{RESET}")
            failed += 1
            continue

        outcome = resp.get("outcome", "UNKNOWN")
        confidence = resp.get("confidence", 0)
        color = OUTCOME_COLORS.get(outcome, RESET)
        match = "✓" if outcome == q["expected"] else "✗"
        match_color = GREEN if outcome == q["expected"] else RED

        print(f"\n  {BOLD}Outcome:{RESET}    {color}{BOLD}{outcome}{RESET}  {match_color}{match} (expected {q['expected']}){RESET}")
        print(f"  {BOLD}Confidence:{RESET} {confidence:.2f}")

        if outcome == "ANSWER":
            answer = resp.get("answer", "")
            sources = resp.get("sources", [])
            print(f"\n  {GREEN}Answer (excerpt):{RESET}")
            excerpt = answer[:300].replace("\n", " ") + ("…" if len(answer) > 300 else "")
            print(f"  {DIM}{excerpt}{RESET}")
            if sources:
                src_ids = [s.get("source_id", s.get("id", "?")) for s in sources[:3]]
                print(f"  {DIM}Sources: {', '.join(src_ids)}{RESET}")

        elif outcome == "GUIDE":
            workflow_id = resp.get("workflow_id", "?")
            steps = resp.get("steps", [])
            print(f"\n  {CYAN}Workflow:{RESET} {workflow_id}  ({len(steps)} steps)")
            for step in steps[:3]:
                gate = " ⚠ approval gate" if step.get("is_approval_gate") else ""
                desc = step.get("description", "")[:80]
                print(f"  {DIM}  Step {step.get('step_number', '?')}: {desc}…{gate}{RESET}")
            if len(steps) > 3:
                print(f"  {DIM}  … {len(steps) - 3} more steps{RESET}")

        elif outcome == "ROUTE":
            ticket = resp.get("escalation_ticket", {})
            print(f"\n  {YELLOW}Routed to:{RESET} {ticket.get('target_team', resp.get('target_team', '?'))}")
            print(f"  {YELLOW}Priority:{RESET}  {ticket.get('priority', resp.get('priority', '?'))}")
            print(f"  {YELLOW}Ticket:{RESET}    {ticket.get('ticket_id', 'N/A')}")

        elif outcome == "REFUSE":
            reason = resp.get("reason", resp.get("message", ""))[:120]
            print(f"\n  {RED}Refused:{RESET} {DIM}{reason}{RESET}")

        if outcome == q["expected"]:
            passed += 1
        else:
            failed += 1

        if i < len(DEMO_QUERIES):
            time.sleep(0.5)

    print(f"\n{BOLD}{'━' * 72}{RESET}")
    print(f"\n{BOLD}  Demo Complete:{RESET}  {GREEN}{passed} passed{RESET}  ·  {RED}{failed} failed{RESET}  ·  {passed + failed} total")
    print()


def main():
    parser = argparse.ArgumentParser(description="Mneme Hackathon Demo Runner")
    parser.add_argument("--base-url", default=BASE_URL, help=f"API base URL (default: {BASE_URL})")
    args = parser.parse_args()
    run_demo(args.base_url)


if __name__ == "__main__":
    main()
