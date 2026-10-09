"""
Tests for the pure deterministic decide() function.
Every branch in the decision tree gets at least one test case.
"""

import pytest
from app.decide import decide, DecisionContext, Decision


def _ctx(**overrides) -> DecisionContext:
    """Build a DecisionContext with safe defaults (would produce ANSWER)."""
    defaults = dict(
        guard_safe=True,
        guard_reason="",
        llm_confidence=0.92,
        intent="information_request",
        issue_type="billing_inquiry",
        route=None,
        has_workflow=False,
        has_vector_hits=True,
        retrieval_safe=True,
        retrieval_reason="",
        composite_confidence=0.88,
    )
    defaults.update(overrides)
    return DecisionContext(**defaults)


class TestGuardRefuse:
    def test_unsafe_input_returns_refuse(self):
        d = decide(_ctx(guard_safe=False, guard_reason="Clinical query detected"))
        assert d.outcome == "REFUSE"
        assert "Clinical" in d.reason

    def test_unsafe_input_takes_priority_over_everything(self):
        d = decide(_ctx(
            guard_safe=False,
            guard_reason="Prompt injection",
            llm_confidence=0.99,
            intent="workflow_request",
            has_workflow=True,
        ))
        assert d.outcome == "REFUSE"


class TestLowConfidenceRoute:
    def test_very_low_confidence_routes(self):
        d = decide(_ctx(llm_confidence=0.2))
        assert d.outcome == "ROUTE"
        assert d.is_gap is True
        assert "confidence" in d.reason.lower()

    def test_threshold_boundary_routes(self):
        d = decide(_ctx(llm_confidence=0.39))
        assert d.outcome == "ROUTE"
        assert d.is_gap is True

    def test_at_threshold_proceeds(self):
        d = decide(_ctx(llm_confidence=0.40))
        assert d.outcome != "ROUTE" or "confidence" not in d.reason.lower()

    def test_unclear_intent_routes(self):
        d = decide(_ctx(intent="unclear", llm_confidence=0.8))
        assert d.outcome == "ROUTE"
        assert d.is_gap is True

    def test_uses_route_target_if_available(self):
        d = decide(_ctx(
            llm_confidence=0.1,
            route={"target_team": "Billing Dept", "priority": "ROUTINE"},
        ))
        assert d.routing_target == "Billing Dept"

    def test_falls_back_to_help_desk(self):
        d = decide(_ctx(llm_confidence=0.1, route=None))
        assert d.routing_target == "Operations Help Desk"


class TestClinicalRefuse:
    def test_clinical_route_returns_refuse(self):
        d = decide(_ctx(route={"target_team": "REFUSE_CLINICAL"}))
        assert d.outcome == "REFUSE"
        assert "clinical" in d.reason.lower()
        assert d.is_gap is False


class TestMandatoryEscalation:
    def test_routing_needed_with_route(self):
        d = decide(_ctx(
            intent="routing_needed",
            route={"target_team": "IT Security", "priority": "URGENT", "reason": "Security incident"},
        ))
        assert d.outcome == "ROUTE"
        assert d.routing_target == "IT Security"
        assert d.priority == "URGENT"
        assert d.is_gap is False

    def test_routing_needed_without_route_proceeds(self):
        d = decide(_ctx(intent="routing_needed", route=None))
        assert d.outcome == "ANSWER"


class TestApprovalGate:
    def test_urgent_priority_routes(self):
        d = decide(_ctx(
            route={"target_team": "Billing Supervisor", "priority": "URGENT", "reason": "Amount > $500"},
        ))
        assert d.outcome == "ROUTE"
        assert d.priority == "URGENT"
        assert d.routing_target == "Billing Supervisor"

    def test_critical_priority_routes(self):
        d = decide(_ctx(
            route={"target_team": "Admin", "priority": "CRITICAL", "reason": "Emergency"},
        ))
        assert d.outcome == "ROUTE"
        assert d.priority == "CRITICAL"

    def test_routine_priority_does_not_gate(self):
        d = decide(_ctx(
            route={"target_team": "Help Desk", "priority": "ROUTINE"},
        ))
        assert d.outcome == "ANSWER"


class TestWorkflowGuide:
    def test_workflow_request_with_match(self):
        d = decide(_ctx(intent="workflow_request", has_workflow=True))
        assert d.outcome == "GUIDE"
        assert d.is_gap is False

    def test_workflow_request_without_match_proceeds(self):
        d = decide(_ctx(intent="workflow_request", has_workflow=False))
        assert d.outcome == "ANSWER"


class TestNoEvidence:
    def test_no_vector_hits_routes_with_gap(self):
        d = decide(_ctx(has_vector_hits=False))
        assert d.outcome == "ROUTE"
        assert d.is_gap is True
        assert "knowledge base" in d.reason.lower()


class TestRetrievalGuard:
    def test_unsafe_retrieval_routes_urgent(self):
        d = decide(_ctx(retrieval_safe=False, retrieval_reason="Poisoned document"))
        assert d.outcome == "ROUTE"
        assert d.priority == "URGENT"
        assert d.is_gap is False


class TestLowTrust:
    def test_low_composite_confidence_routes(self):
        d = decide(_ctx(composite_confidence=0.35))
        assert d.outcome == "ROUTE"
        assert d.is_gap is True
        assert "trust" in d.reason.lower()

    def test_at_threshold_proceeds(self):
        d = decide(_ctx(composite_confidence=0.50))
        assert d.outcome == "ANSWER"


class TestDefaultAnswer:
    def test_happy_path_returns_answer(self):
        d = decide(_ctx())
        assert d.outcome == "ANSWER"
        assert d.is_gap is False
        assert d.reason == ""
