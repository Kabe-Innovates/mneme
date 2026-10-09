"""
Mneme Orchestrator — 5-Step Pipeline with 3-Layer Guard System
==============================================================
Step 1: GUARD      — 3-layer safety gate: input scan (clinical, injection, PII vault)
Step 2: CLASSIFY   — LLM intent classification via Bedrock Claude
Step 3: DECIDE     — Routing: ROUTE / GUIDE / ANSWER determination
Step 4: GENERATE   — Hybrid retrieval (Vector + Graph) → grounded LLM answer
Step 5: VERIFY     — Output guard (PII leakage check) + citation guard

Upgrades from original:
  - 3-layer guard system (input / retrieval / output) — from Divathiru
  - PII vault pattern (extract → replace → verify) — from Divathiru
  - Knowledge gap capture on low-confidence routes — from Divathiru
  - Conversation history support — lightweight multi-turn
"""

from app import guards, llm, vector_store, router, workflow_engine, audit, knowledge_graph
from app.decide import decide, DecisionContext
from app.models import (
    OrchestratorResponse, Source, WorkflowInfo, WorkflowStep, GraphNode
)


# Confidence band thresholds
HIGH_THRESHOLD = 0.85
LOW_THRESHOLD = 0.50

# In-memory conversation history (lightweight multi-turn)
_session_history: dict[str, list[dict]] = {}


def _confidence_band(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= LOW_THRESHOLD:
        return "medium"
    return "low"


def process_query(query: str, role: str, session_id: str) -> OrchestratorResponse:

    # ----------------------------------------------------------------
    # STEP 1: 3-LAYER INPUT GUARD — deterministic, no LLM
    # ----------------------------------------------------------------
    scan = guards.scan_input(query)

    # Use sanitized query (PII replaced with placeholders) for all LLM calls
    sanitized_query = scan.sanitized
    pii_vault = scan.pii_vault

    # ----------------------------------------------------------------
    # STEP 2: INTENT CLASSIFICATION — LLM call (skip if guard failed)
    # ----------------------------------------------------------------
    if scan.safe:
        intent = llm.classify_intent(sanitized_query, role)
        llm_confidence = float(intent.get("confidence", 0.0))
        issue_type = intent.get("issue_type", "unclear")
        entities = intent.get("entities", {})
        mandatory_route = router.find_route(issue_type, entities)
        has_workflow = (
            intent.get("intent") == "workflow_request"
            and workflow_engine.find_workflow_for_intent(intent) is not None
        )
    else:
        intent = {}
        llm_confidence = 0.0
        issue_type = "unclear"
        entities = {}
        mandatory_route = None
        has_workflow = False

    # ----------------------------------------------------------------
    # STEP 3: PRE-RETRIEVAL DECISION — pure deterministic
    # ----------------------------------------------------------------
    pre_decision = decide(DecisionContext(
        guard_safe=scan.safe,
        guard_reason=scan.reason,
        llm_confidence=llm_confidence,
        intent=intent.get("intent", "unclear"),
        issue_type=issue_type,
        route=mandatory_route,
        has_workflow=has_workflow,
        has_vector_hits=True,
        retrieval_safe=True,
        retrieval_reason="",
        composite_confidence=1.0,
    ))

    if pre_decision.outcome == "REFUSE":
        response = OrchestratorResponse(
            outcome="REFUSE",
            message=pre_decision.reason,
            confidence=1.0,
            confidence_band="high",
            session_id=session_id,
        )
        _log(session_id, role, query, response, sanitized_query, is_gap=pre_decision.is_gap)
        return response

    if pre_decision.outcome == "ROUTE":
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=_build_route_message(mandatory_route, issue_type, entities) if mandatory_route else pre_decision.reason,
            confidence=llm_confidence,
            confidence_band=_confidence_band(llm_confidence),
            routing_target=pre_decision.routing_target,
            escalation_reason=pre_decision.reason,
            priority=pre_decision.priority or "ROUTINE",
            session_id=session_id,
        )
        _log(session_id, role, query, response, sanitized_query, is_gap=pre_decision.is_gap)
        return response

    if pre_decision.outcome == "GUIDE":
        workflow = workflow_engine.find_workflow_for_intent(intent)
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
        _log(session_id, role, query, response, sanitized_query)
        return response

    # ----------------------------------------------------------------
    # STEP 4: HYBRID RETRIEVAL + GENERATION
    # ----------------------------------------------------------------

    # Phase A: Vector semantic search
    vector_hits = vector_store.search(query, role, n_results=5)

    # Layer 2: RETRIEVAL GUARD — check retrieved docs for injection
    retrieval_safe, retrieval_reason = guards.scan_retrieval(vector_hits) if vector_hits else (True, "")

    top_similarity = vector_hits[0]["relevance"] if vector_hits else 0.0

    # Phase B: Knowledge Graph expansion
    graph_nodes_response: list[GraphNode] = []
    graph_context_docs: list[dict] = []
    coverage: dict = {}

    if vector_hits and retrieval_safe and knowledge_graph.is_loaded():
        entry_ids = [hit["source_id"] for hit in vector_hits]
        subgraph = knowledge_graph.traverse_subgraph(
            entry_ids, role, max_hops=3, max_nodes=25
        )
        graph_context_docs = knowledge_graph.build_context_bundle(subgraph)

        composite_confidence, coverage = knowledge_graph.compute_trust_score(
            subgraph, top_similarity
        )

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
        composite_confidence = min(llm_confidence, top_similarity + 0.2) if vector_hits else 0.0

    # ----------------------------------------------------------------
    # POST-RETRIEVAL DECISION — pure deterministic
    # ----------------------------------------------------------------
    post_decision = decide(DecisionContext(
        guard_safe=True,
        guard_reason="",
        llm_confidence=llm_confidence,
        intent=intent.get("intent", ""),
        issue_type=issue_type,
        route=mandatory_route,
        has_workflow=False,
        has_vector_hits=bool(vector_hits),
        retrieval_safe=retrieval_safe,
        retrieval_reason=retrieval_reason,
        composite_confidence=composite_confidence,
    ))

    if post_decision.outcome != "ANSWER":
        if not retrieval_safe:
            print(f"[Orchestrator] Retrieval guard triggered: {retrieval_reason}")
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=post_decision.reason,
            confidence=composite_confidence if vector_hits else llm_confidence * 0.5,
            confidence_band="low",
            routing_target=post_decision.routing_target,
            escalation_reason=post_decision.reason,
            priority=post_decision.priority or "ROUTINE",
            session_id=session_id,
        )
        _log(session_id, role, query, response, sanitized_query, is_gap=post_decision.is_gap)
        return response

    # Phase C: Enriched LLM generation
    all_context = list(vector_hits) + [
        doc for doc in graph_context_docs
        if doc["source_id"] not in {h["source_id"] for h in vector_hits}
    ]

    # Get conversation history for multi-turn context
    history = _session_history.get(session_id, [])

    answer = llm.generate_answer(sanitized_query, all_context, role,
                                  conversation_history=history)

    # ----------------------------------------------------------------
    # STEP 5: OUTPUT VERIFICATION
    # ----------------------------------------------------------------

    # Layer 3: OUTPUT GUARD — check for PII leakage
    output_safe, output_reason = guards.scan_output(answer["text"], pii_vault)
    if not output_safe:
        print(f"[Orchestrator] Output guard triggered: {output_reason}")
        answer = llm._template_answer(all_context)

    # Citation guard
    guard_passed, guard_reason = guards.citation_guard(answer["text"], all_context)
    if not guard_passed:
        print(f"[Orchestrator] Citation guard failed: {guard_reason}")
        answer = llm._template_answer(all_context)

    # Build sources list
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
    _log(session_id, role, query, response, sanitized_query)

    # Save to conversation history for multi-turn
    _session_history.setdefault(session_id, []).append({
        "query": sanitized_query,
        "summary": answer["text"][:200],
    })
    # Cap history at 5 turns per session
    if len(_session_history[session_id]) > 5:
        _session_history[session_id] = _session_history[session_id][-5:]

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


def _log(session_id: str, role: str, query: str, response: OrchestratorResponse,
         sanitized_query: str = "", is_gap: bool = False):
    try:
        redacted = sanitized_query or guards.redact_pii(query)
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
                is_gap=is_gap,
            )
            response.ticket_id = ticket_id
    except Exception as e:
        print(f"[Orchestrator] Audit log error: {e}")
