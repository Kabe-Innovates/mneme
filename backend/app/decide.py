"""
Pure deterministic decision engine — no I/O, no LLM calls.

Takes pre-computed signals and returns a Decision. Branch order:
  1. Guard unsafe       → REFUSE
  2. Low confidence     → ROUTE (gap)
  3. Clinical rule      → REFUSE
  4. Mandatory escalation → ROUTE
  5. Approval gate      → ROUTE
  6. Workflow match      → GUIDE
  7. No evidence        → ROUTE (gap)
  8. Retrieval unsafe   → ROUTE
  9. Low trust score    → ROUTE (gap)
  10. Default           → ANSWER
"""

from dataclasses import dataclass
from typing import Optional


LOW_CONFIDENCE_THRESHOLD = 0.40
LOW_TRUST_THRESHOLD = 0.50


@dataclass(frozen=True)
class DecisionContext:
    guard_safe: bool
    guard_reason: str
    llm_confidence: float
    intent: str
    issue_type: str
    route: Optional[dict]
    has_workflow: bool
    has_vector_hits: bool
    retrieval_safe: bool
    retrieval_reason: str
    composite_confidence: float


@dataclass(frozen=True)
class Decision:
    outcome: str
    reason: str
    is_gap: bool
    priority: str
    routing_target: Optional[str]


def _route_target(route: Optional[dict], fallback: str = "Operations Help Desk") -> str:
    if route:
        return route.get("target_team", fallback)
    return fallback


def decide(ctx: DecisionContext) -> Decision:
    if not ctx.guard_safe:
        return Decision(
            outcome="REFUSE",
            reason=ctx.guard_reason,
            is_gap=False,
            priority="",
            routing_target=None,
        )

    if ctx.llm_confidence < LOW_CONFIDENCE_THRESHOLD or ctx.intent == "unclear":
        return Decision(
            outcome="ROUTE",
            reason="Low classification confidence — human review required",
            is_gap=True,
            priority="ROUTINE",
            routing_target=_route_target(ctx.route),
        )

    if ctx.route and ctx.route.get("target_team") == "REFUSE_CLINICAL":
        return Decision(
            outcome="REFUSE",
            reason=(
                "This type of request requires clinical judgment and cannot be "
                "handled by Mneme. Please consult a qualified medical professional."
            ),
            is_gap=False,
            priority="",
            routing_target=None,
        )

    if ctx.intent == "routing_needed" and ctx.route:
        return Decision(
            outcome="ROUTE",
            reason=ctx.route.get(
                "reason",
                f"Issue type '{ctx.issue_type}' requires human handling",
            ),
            is_gap=False,
            priority=ctx.route.get("priority", "ROUTINE"),
            routing_target=ctx.route.get("target_team"),
        )

    if ctx.route and ctx.route.get("priority") in ("URGENT", "CRITICAL"):
        return Decision(
            outcome="ROUTE",
            reason=ctx.route.get(
                "reason",
                f"Issue type '{ctx.issue_type}' requires supervisory approval",
            ),
            is_gap=False,
            priority=ctx.route.get("priority", "URGENT"),
            routing_target=ctx.route.get("target_team"),
        )

    if ctx.intent == "workflow_request" and ctx.has_workflow:
        return Decision(
            outcome="GUIDE",
            reason="Workflow guidance available",
            is_gap=False,
            priority="",
            routing_target=None,
        )

    if not ctx.has_vector_hits:
        return Decision(
            outcome="ROUTE",
            reason="Query not covered in available knowledge base",
            is_gap=True,
            priority="ROUTINE",
            routing_target=_route_target(ctx.route),
        )

    if not ctx.retrieval_safe:
        return Decision(
            outcome="ROUTE",
            reason=f"Retrieval guard: {ctx.retrieval_reason}",
            is_gap=False,
            priority="URGENT",
            routing_target="Operations Help Desk",
        )

    if ctx.composite_confidence < LOW_TRUST_THRESHOLD:
        return Decision(
            outcome="ROUTE",
            reason=f"Low trust score ({ctx.composite_confidence:.0%}) — knowledge gap",
            is_gap=True,
            priority="ROUTINE",
            routing_target=_route_target(ctx.route),
        )

    return Decision(
        outcome="ANSWER",
        reason="",
        is_gap=False,
        priority="",
        routing_target=None,
    )
