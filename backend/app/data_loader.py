import json
import os
from app import vector_store, knowledge_graph

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_json(filename: str) -> list:
    path = os.path.join(DATA_DIR, filename)
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Vector store ingestion (ChromaDB)
# ---------------------------------------------------------------------------

def ingest_vectors():
    docs = []

    articles = load_json("knowledge_articles.json")
    for article in articles:
        docs.append({
            "id": article["article_id"],
            "text": f"{article['title']}\n\n{article['content']}",
            "metadata": {
                "source_id": article["article_id"],
                "title": article["title"],
                "department": article.get("department", ""),
                "status": article.get("status", "approved"),
                "visible_to_roles": ",".join(article.get("visible_to_roles", ["ALL"])),
                "category": article.get("category", ""),
                "doc_type": "article",
                "version": article.get("version", ""),
                "owner": article.get("owner", ""),
            },
        })

    workflows = load_json("workflows.json")
    for wf in workflows:
        step_text = "\n".join(
            f"Step {s['step_number']}: {s['description']}"
            for s in wf.get("steps", [])
        )
        docs.append({
            "id": wf["workflow_id"],
            "text": f"{wf['workflow_name']}\n\n{step_text}",
            "metadata": {
                "source_id": wf["workflow_id"],
                "title": wf["workflow_name"],
                "department": wf.get("department", ""),
                "status": "approved",
                "visible_to_roles": "ALL",
                "category": "workflow",
                "doc_type": "workflow",
                "owner": wf.get("owner_team", ""),
            },
        })

    vector_store.ingest_documents(docs)
    print(f"[DataLoader] Vector ingestion complete — {len(docs)} documents indexed")


# ---------------------------------------------------------------------------
# Knowledge Graph construction
# ---------------------------------------------------------------------------

def _team_id(name: str) -> str:
    return f"TEAM-{name.replace(' ', '-').replace('&', 'and')}"


def _role_id(name: str) -> str:
    return f"ROLE-{name.replace(' ', '-').replace('&', 'and')}"


def _system_id(name: str) -> str:
    return f"SYS-{name.replace(' ', '-')}"


def _field_id(name: str) -> str:
    return f"FIELD-{name}"


def _step_id(workflow_id: str, step_number: int) -> str:
    return f"{workflow_id}_STEP_{step_number}"


def build_graph():
    """
    Parse all synthetic JSON files and construct the NetworkX Knowledge Graph.

    Node types created: Article, Workflow, Step, Team, Role, System, Field
    Edge types created: visible_to, owned_by, escalates_to, defined_in,
                        has_step, precedes, done_in, requires
    """
    knowledge_graph.clear()

    articles = load_json("knowledge_articles.json")
    workflows = load_json("workflows.json")
    field_defs = load_json("field_definitions.json")

    # ----------------------------------------------------------------
    # Field nodes (before steps — steps reference them)
    # ----------------------------------------------------------------
    for fd in field_defs:
        fid = _field_id(fd["field_name"])
        knowledge_graph.add_node(
            fid,
            node_type="Field",
            title=fd.get("label", fd["field_name"]),
            name=fd.get("label", fd["field_name"]),
            field_name=fd["field_name"],
            field_type=fd.get("field_type", "string"),
            allowed_values=fd.get("allowed_values"),
            validation_regex=fd.get("validation_regex"),
            is_required=fd.get("is_required", True),
            is_sensitive=fd.get("is_sensitive", False),
            description=fd.get("description", ""),
            status="approved",
        )

    # ----------------------------------------------------------------
    # Article nodes + Role nodes + Team nodes + edges
    # ----------------------------------------------------------------
    for article in articles:
        aid = article["article_id"]
        knowledge_graph.add_node(
            aid,
            node_type="Article",
            title=article["title"],
            content=article["content"],
            department=article.get("department", ""),
            status=article.get("status", "approved"),
            version=article.get("version", ""),
            effective_date=article.get("effective_date", ""),
            review_due_date=article.get("review_due_date", ""),
            owner=article.get("owner", ""),
            category=article.get("category", ""),
            visible_to_roles=article.get("visible_to_roles", ["ALL"]),
        )

        # visible_to edges → Role nodes
        for role_name in article.get("visible_to_roles", []):
            if role_name == "ALL":
                continue
            rid = _role_id(role_name)
            if knowledge_graph.get_node(rid) is None:
                knowledge_graph.add_node(
                    rid,
                    node_type="Role",
                    title=role_name,
                    name=role_name,
                    status="approved",
                )
            knowledge_graph.add_edge(aid, rid, "visible_to")

        # owned_by edge → Team node
        dept = article.get("department", "")
        if dept:
            tid = _team_id(dept)
            if knowledge_graph.get_node(tid) is None:
                knowledge_graph.add_node(
                    tid,
                    node_type="Team",
                    title=dept,
                    name=dept,
                    status="approved",
                )
            knowledge_graph.add_edge(aid, tid, "owned_by")

    # ----------------------------------------------------------------
    # Workflow nodes + Step nodes + System nodes + edges
    # ----------------------------------------------------------------
    for wf in workflows:
        wid = wf["workflow_id"]

        knowledge_graph.add_node(
            wid,
            node_type="Workflow",
            title=wf["workflow_name"],
            workflow_name=wf["workflow_name"],
            department=wf.get("department", ""),
            owner_team=wf.get("owner_team", ""),
            escalation_team=wf.get("escalation_team", ""),
            status="approved",
            visible_to_roles=["ALL"],
        )

        # defined_in → governing Article
        governing = wf.get("governing_article", "")
        if governing and knowledge_graph.get_node(governing):
            knowledge_graph.add_edge(wid, governing, "defined_in")

        # owned_by → Team
        owner = wf.get("owner_team", "")
        if owner:
            tid = _team_id(owner)
            if knowledge_graph.get_node(tid) is None:
                knowledge_graph.add_node(
                    tid,
                    node_type="Team",
                    title=owner,
                    name=owner,
                    status="approved",
                )
            knowledge_graph.add_edge(wid, tid, "owned_by")

        # escalates_to → Team
        escalation = wf.get("escalation_team", "")
        if escalation:
            eid = _team_id(escalation)
            if knowledge_graph.get_node(eid) is None:
                knowledge_graph.add_node(
                    eid,
                    node_type="Team",
                    title=escalation,
                    name=escalation,
                    status="approved",
                )
            knowledge_graph.add_edge(wid, eid, "escalates_to")

        # Steps
        steps = wf.get("steps", [])
        prev_step_id = None
        for step in sorted(steps, key=lambda s: s["step_number"]):
            sid = _step_id(wid, step["step_number"])
            knowledge_graph.add_node(
                sid,
                node_type="Step",
                title=step["description"][:80],
                description=step["description"],
                step_number=step["step_number"],
                required_fields=step.get("required_fields", []),
                system_used=step.get("system_used", ""),
                is_approval_gate=step.get("is_approval_gate", False),
                status="approved",
                visible_to_roles=["ALL"],
            )
            knowledge_graph.add_edge(wid, sid, "has_step")

            # precedes: link sequential steps
            if prev_step_id:
                knowledge_graph.add_edge(prev_step_id, sid, "precedes")
            prev_step_id = sid

            # done_in → System node
            sys_name = step.get("system_used", "")
            if sys_name:
                sys_id = _system_id(sys_name)
                if knowledge_graph.get_node(sys_id) is None:
                    knowledge_graph.add_node(
                        sys_id,
                        node_type="System",
                        title=sys_name,
                        name=sys_name,
                        status="approved",
                    )
                knowledge_graph.add_edge(sid, sys_id, "done_in")

            # requires → Field nodes
            for field_name in step.get("required_fields", []):
                fid = _field_id(field_name)
                if knowledge_graph.get_node(fid) is None:
                    # Field not in field_definitions.json — create minimal node
                    knowledge_graph.add_node(
                        fid,
                        node_type="Field",
                        title=field_name.replace("_", " ").title(),
                        name=field_name,
                        field_name=field_name,
                        field_type="string",
                        is_required=True,
                        is_sensitive=False,
                        status="approved",
                    )
                knowledge_graph.add_edge(sid, fid, "requires")

    knowledge_graph.mark_loaded()

    stats = knowledge_graph.get_stats()
    print(
        f"[DataLoader] Knowledge Graph built — "
        f"{stats['total_nodes']} nodes, {stats['total_edges']} edges"
    )
    print(f"[DataLoader] Node types: {stats['node_types']}")
    return stats


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------

def ingest_all():
    ingest_vectors()
    build_graph()
