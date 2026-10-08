from app import guards, llm, vector_store, router, workflow_engine, audit
from app.models import OrchestratorResponse, Source, WorkflowInfo, WorkflowStep


def process_query(query: str, role: str, session_id: str) -> OrchestratorResponse:

    # STEP 1: SAFETY GUARD — deterministic, no LLM
    is_clinical, refuse_msg = guards.is_clinical_query(query)
    if is_clinical:
        response = OrchestratorResponse(
            outcome="REFUSE",
            message=refuse_msg,
            confidence=1.0,
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # STEP 2: INTENT CLASSIFICATION — LLM call
    intent = llm.classify_intent(query, role)
    confidence = float(intent.get("confidence", 0.0))
    issue_type = intent.get("issue_type", "unclear")
    entities = intent.get("entities", {})

    # STEP 3: ROUTING DECISION — deterministic
    # Low confidence or explicitly unclear → route to human
    if confidence < 0.4 or intent.get("intent") == "unclear":
        route = router.find_route("general_operational", entities)
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=(
                "I'm not confident I understand your request well enough to assist reliably. "
                "To ensure you get accurate help, I'm routing this to the appropriate team."
            ),
            confidence=confidence,
            routing_target=route["target_team"] if route else "Operations Help Desk",
            escalation_reason="Low classification confidence — human review required",
            priority=route["priority"] if route else "ROUTINE",
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # Check for mandatory routing rules (e.g., insurance_denial, patient_safety)
    mandatory_route = router.find_route(issue_type, entities)
    if mandatory_route and mandatory_route.get("target_team") == "REFUSE_CLINICAL":
        response = OrchestratorResponse(
            outcome="REFUSE",
            message=(
                "This type of request requires clinical judgment and cannot be handled by Mneme. "
                "Please consult a qualified medical professional immediately."
            ),
            confidence=1.0,
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # Check if this is a routing-needed intent with a mandatory escalation rule
    if intent.get("intent") == "routing_needed" and mandatory_route:
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=_build_route_message(mandatory_route, issue_type, entities),
            confidence=confidence,
            routing_target=mandatory_route["target_team"],
            escalation_reason=mandatory_route.get("reason", f"Issue type '{issue_type}' requires human handling"),
            priority=mandatory_route.get("priority", "ROUTINE"),
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # STEP 4: WORKFLOW GUIDANCE — check for workflow match
    if intent.get("intent") == "workflow_request":
        workflow = workflow_engine.find_workflow_for_intent(intent)
        if workflow:
            wf_info = workflow_engine.get_workflow_for_response(workflow, session_id)
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
                confidence=confidence,
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

    # STEP 5: KNOWLEDGE RETRIEVAL + ANSWER GENERATION
    docs = vector_store.search(query, role, n_results=5)

    if not docs:
        # No relevant docs found → route to human
        route = router.find_route("general_operational", entities)
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=(
                "I couldn't find relevant information in the approved knowledge base to answer your question. "
                "I'm routing this to the appropriate team for assistance."
            ),
            confidence=confidence * 0.5,
            routing_target=route["target_team"] if route else "Operations Help Desk",
            escalation_reason="Query not covered in available knowledge base",
            priority="ROUTINE",
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    # Low retrieval relevance → route
    top_relevance = docs[0]["relevance"] if docs else 0.0
    if top_relevance < 0.3:
        route = router.find_route("general_operational", entities)
        response = OrchestratorResponse(
            outcome="ROUTE",
            message=(
                "The available documentation doesn't closely match your question. "
                "I'm routing this to the appropriate team to ensure accuracy."
            ),
            confidence=confidence * top_relevance,
            routing_target=route["target_team"] if route else "Operations Help Desk",
            escalation_reason="Low retrieval relevance — knowledge gap detected",
            priority="ROUTINE",
            session_id=session_id,
        )
        _log(session_id, role, query, response)
        return response

    answer = llm.generate_answer(query, docs, role)
    sources = [
        Source(
            source_id=c["source_id"],
            title=c["title"],
            department=c.get("department", ""),
            relevance=round(top_relevance, 2),
        )
        for c in (answer.get("citations") or docs[:3])
    ]

    response = OrchestratorResponse(
        outcome="ANSWER",
        message=answer["text"],
        confidence=min(confidence, top_relevance + 0.2),
        sources=sources,
        session_id=session_id,
    )
    _log(session_id, role, query, response)
    return response


def _build_route_message(rule: dict, issue_type: str, entities: dict) -> str:
    team = rule.get("target_team", "the appropriate team")
    priority = rule.get("priority", "ROUTINE")
    reason = rule.get("reason", f"This type of request requires human review")

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
    except Exception as e:
        print(f"[Orchestrator] Audit log error: {e}")
