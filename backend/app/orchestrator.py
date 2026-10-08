"""
Mneme Orchestrator — 4-Step Pipeline with Second Brain Hybrid Retrieval

Step 1: GUARD      — Deterministic clinical/PII safety gate (no LLM)
Step 2: CLASSIFY   — LLM intent classification via Bedrock Claude
Step 3: DECIDE     — Routing: ROUTE / GUIDE / ANSWER determination
Step 4: GENERATE   — Hybrid retrieval (Vector + Graph) → grounded LLM answer

The Second Brain upgrade (Step 4):
  Vector search finds semantic entry points →
  Knowledge Graph traversal expands connected context (teams, systems, fields, steps) →
  Trust scoring computes composite confidence →
  LLM generates grounded answer from enriched context bundle
"""

from app import guards, llm, vector_store, router, workflow_engine, audit, knowledge_graph
from app.models import (
    OrchestratorResponse, Source, WorkflowInfo, WorkflowStep, GraphNode
)


# Confidence band thresholds (from architecture spec)
HIGH_THRESHOLD = 0.85
LOW_THRESHOLD = 0.50


def _confidence_band(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= LOW_THRESHOLD:
        return "medium"
    return "low"


def process_query(query: str, role: str, session_id: str) -> OrchestratorResponse:

    # Sanitize PII before any LLM call — raw query retained only for audit log
    sanitized_query = guards.redact_pii(query)

    # ----------------------------------------------------------------
    # STEP 1: SAFETY GUARD — 100% deterministic, no LLM
    # ----------------------------------------------------------------
    is_clinical, refuse_msg = guards.is_clinical_query(query)
    if is_clinical:
        response = OrchestratorResponse(
            outcome="REFUSE",
            message=refuse_msg,
            confidence=1.0,
            confidence_band="high",
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # ----------------------------------------------------------------
    # STEP 2: INTENT CLASSIFICATION — LLM call
    # ----------------------------------------------------------------
    intent = llm.classify_intent(sanitized_query, role)
    llm_confidence = float(intent.get("confidence", 0.0))
    issue_type = intent.get("issue_type", "unclear")
    entities = intent.get("entities", {})

    # ----------------------------------------------------------------
    # STEP 3: ROUTING DECISION — deterministic
    # ----------------------------------------------------------------
    # Low confidence or explicitly unclear → route to human
    if llm_confidence < 0.4 or intent.get("intent") == "unclear":
        route = router.find_route("general_operational", entities)
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=(
                "I'm not confident I understand your request well enough to assist reliably. "
                "To ensure you get accurate help, I'm routing this to the appropriate team."
            ),
            confidence=llm_confidence,
            confidence_band=_confidence_band(llm_confidence),
            routing_target=route["target_team"] if route else "Operations Help Desk",
            escalation_reason="Low classification confidence — human review required",
            priority=route["priority"] if route else "ROUTINE",
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # Check for hard clinical routing rule
    mandatory_route = router.find_route(issue_type, entities)
    if mandatory_route and mandatory_route.get("target_team") == "REFUSE_CLINICAL":
        response = OrchestratorResponse(
            outcome="REFUSE",
            message=(
                "This type of request requires clinical judgment and cannot be handled by Mneme. "
                "Please consult a qualified medical professional immediately."
            ),
            confidence=1.0,
            confidence_band="high",
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # Mandatory human escalation (routing_needed intent)
    if intent.get("intent") == "routing_needed" and mandatory_route:
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=_build_route_message(mandatory_route, issue_type, entities),
            confidence=llm_confidence,
            confidence_band=_confidence_band(llm_confidence),
            routing_target=mandatory_route["target_team"],
            escalation_reason=mandatory_route.get(
                "reason", f"Issue type '{issue_type}' requires human handling"
            ),
            priority=mandatory_route.get("priority", "ROUTINE"),
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # Approval gate precedence: financial/privilege thresholds escalate even
    # if LLM classified as workflow_request — supervisory rules are non-optional
    if mandatory_route and mandatory_route.get("priority") in ("URGENT", "CRITICAL"):
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=_build_route_message(mandatory_route, issue_type, entities),
            confidence=llm_confidence,
            confidence_band=_confidence_band(llm_confidence),
            routing_target=mandatory_route["target_team"],
            escalation_reason=mandatory_route.get(
                "reason", f"Issue type '{issue_type}' requires supervisory approval"
            ),
            priority=mandatory_route.get("priority", "URGENT"),
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # Workflow guidance
    if intent.get("intent") == "workflow_request":
        workflow = workflow_engine.find_workflow_for_intent(intent)
        if workflow:
            wf_info = workflow_engine.start_workflow(workflow["workflow_id"], session_id)
            wf_steps = [
                WorkflowStep(
                    step_number=s["step_number"],
                    description=s["description"],
                    required_fields=s.get("required_fields", []),
                    system_used=s.get("system_used", ""),
                    is_approval_gate=s.get("is_approval_gate", False),
                )
                for s in wf_info.get("steps", [])
            ]
            response = OrchestratorResponse(
                outcome="GUIDE",
                message=_build_guide_intro(workflow, role),
                confidence=llm_confidence,
                confidence_band=_confidence_band(llm_confidence),
                workflow=WorkflowInfo(
                    workflow_id=wf_info["workflow_id"],
                    workflow_name=wf_info["workflow_name"],
                    department=wf_info["department"],
                    owner_team=wf_info["owner_team"],
                    escalation_team=wf_info.get("escalation_team", ""),
                    current_step=1,
                    steps=wf_steps,
                    missing_fields=wf_info.get("missing_fields", []),
                ),
                session_id=session_id,
            )
            _log(session_id, role, query, response)
            return response

    # ----------------------------------------------------------------
    # STEP 4: SECOND BRAIN HYBRID RETRIEVAL
    # ----------------------------------------------------------------

    # Phase A: Vector semantic search
    vector_hits = vector_store.search(query, role, n_results=5)

    if not vector_hits:
        route = router.find_route("general_operational", entities)
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=(
                "I couldn't find relevant information in the approved knowledge base. "
                "I'm routing this to the appropriate team for assistance."
            ),
            confidence=llm_confidence * 0.5,
            confidence_band="low",
            routing_target=route["target_team"] if route else "Operations Help Desk",
            escalation_reason="Query not covered in available knowledge base",
            priority="ROUTINE",
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    top_similarity = vector_hits[0]["relevance"] if vector_hits else 0.0

    # Phase B: Knowledge Graph expansion (Second Brain)
    graph_nodes_response: list[GraphNode] = []
    graph_context_docs: list[dict] = []
    coverage: dict = {}

    if knowledge_graph.is_loaded():
        entry_ids = [hit["source_id"] for hit in vector_hits]
        subgraph = knowledge_graph.traverse_subgraph(
            entry_ids, role, max_hops=3, max_nodes=25
        )
        graph_context_docs = knowledge_graph.build_context_bundle(subgraph)

        # Phase C: Trust scoring — returns (score, coverage_breakdown)
        composite_confidence, coverage = knowledge_graph.compute_trust_score(
            subgraph, top_similarity
        )

        # Build GraphNode list for response (supporting entities only — not Articles already in sources)
        source_ids = {hit["source_id"] for hit in vector_hits}
        for node in subgraph["nodes"]:
            if node["node_id"] not in source_ids and node["node_type"] not in ("Article",):
                graph_nodes_response.append(GraphNode(
                    node_id=node["node_id"],
                    node_type=node["node_type"],
                    title=node["title"],
                    detail=_node_detail(node),
                ))
    else:
        # Graph not loaded — fall back to vector similarity only
        composite_confidence = min(llm_confidence, top_similarity + 0.2)

    # Low final confidence → route to human
    if composite_confidence < LOW_THRESHOLD:
        route = router.find_route("general_operational", entities)
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=(
                "The available documentation doesn't fully cover your question with high confidence. "
                "I'm routing this to the appropriate team to ensure accuracy."
            ),
            confidence=composite_confidence,
            confidence_band="low",
            routing_target=route["target_team"] if route else "Operations Help Desk",
            escalation_reason=f"Low trust score ({composite_confidence:.0%}) — knowledge gap or conflicting sources",
            priority="ROUTINE",
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # Phase D: Enriched LLM generation
    # Merge vector docs + graph context (graph context appended after vector docs)
    all_context = list(vector_hits) + [
        doc for doc in graph_context_docs
        if doc["source_id"] not in {h["source_id"] for h in vector_hits}
    ]

    answer = llm.generate_answer(sanitized_query, all_context, role)

    # Sentence-level citation guard — log failures but don't block (template fallback handles it)
    guard_passed, guard_reason = guards.citation_guard(answer["text"], all_context)
    if not guard_passed:
        print(f"[Orchestrator] Citation guard failed: {guard_reason}")
        # Escalate to template mode on citation guard failure to prevent hallucinated claims
        answer = llm._template_answer(all_context)

    # Build sources list from cited docs
    cited_ids = {c["source_id"] for c in (answer.get("citations") or [])}
    sources = [
        Source(
            source_id=doc["source_id"],
            title=doc["title"],
            department=doc.get("department", ""),
            relevance=round(top_similarity, 2),
        )
        for doc in all_context[:5]
        if doc["source_id"] in cited_ids or not cited_ids
    ][:5]

    response = OrchestratorResponse(
        outcome="ANSWER",
        message=answer["text"],
        confidence=composite_confidence,
        confidence_band=_confidence_band(composite_confidence),
        sources=sources,
        graph_context=graph_nodes_response,
        coverage=coverage,
        llm_mode=answer.get("mode", "llm"),
        banner=answer.get("banner"),
        session_id=session_id,
    )
    _log(session_id, role, query, response)
    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_route_message(rule: dict, issue_type: str, entities: dict) -> str:
    team = rule.get("target_team", "the appropriate team")
    priority = rule.get("priority", "ROUTINE")
    reason = rule.get("reason", "This type of request requires human review")
    amount = entities.get("amount")
    amount_str = f" (amount: ${amount:,.0f})" if amount else ""
    return (
        f"This request{amount_str} has been flagged for escalation to **{team}**. "
        f"{reason}. Priority: **{priority}**. "
        f"A ticket has been created and the team will follow up per SLA."
    )


def _build_guide_intro(workflow: dict, role: str) -> str:
    return (
        f"I'll guide you through **{workflow['workflow_name']}** step by step. "
        f"This workflow is managed by {workflow.get('owner_team', 'the relevant team')}. "
        f"Please complete each step in sequence. If you encounter an issue at any step, "
        f"escalation support is available from {workflow.get('escalation_team', 'your supervisor')}."
    )


def _node_detail(node: dict) -> str:
    ntype = node["node_type"]
    attrs = node["attrs"]
    if ntype == "Team":
        return f"Contact: {attrs.get('contact_extension', 'see directory')}"
    if ntype == "System":
        return f"Vendor: {attrs.get('vendor', '')} | {attrs.get('login_url', '')}"
    if ntype == "Field":
        vals = attrs.get("allowed_values")
        if vals and isinstance(vals, list):
            return f"Values: {', '.join(str(v) for v in vals[:4])}"
        return f"Type: {attrs.get('field_type', 'string')}"
    return ""


def _log(session_id: str, role: str, query: str, response: OrchestratorResponse):
    try:
        redacted = guards.redact_pii(query)
        audit.log_interaction(
            session_id=session_id,
            role=role,
            query=query,
            query_redacted=redacted,
            response=response.model_dump(),
        )
        if response.outcome == "ROUTE" and response.routing_target:
            ticket_id = audit.create_ticket(
                session_id=session_id,
                initiator_role=role,
                target_team=response.routing_target,
                priority=response.priority or "ROUTINE",
                summary=redacted[:200],
                escalation_reason=response.escalation_reason or "",
            )
            response.ticket_id = ticket_id
    except Exception as e:
        print(f"[Orchestrator] Audit log error: {e}")
