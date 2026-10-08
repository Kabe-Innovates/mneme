import json
import os
from app import vector_store, knowledge_graph

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_json(filename: str) -> list:
    path = os.path.join(DATA_DIR, filename)
    with open(path) as f:
        return json.load(f)


def _load_json_optional(filename: str) -> list:
    """Load a JSON file; return empty list if the file does not exist yet."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
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

    # Index forms so they are discoverable through semantic search
    forms = _load_json_optional("forms.json")
    for form in forms:
        field_list = ", ".join(form.get("fields", []))
        docs.append({
            "id": form["form_id"],
            "text": f"{form['title']}\n\nDepartment: {form.get('department', '')}\n{form.get('description', '')}\nFields: {field_list}",
            "metadata": {
                "source_id": form["form_id"],
                "title": form["title"],
                "department": form.get("department", ""),
                "status": "approved",
                "visible_to_roles": "ALL",
                "category": "form",
                "doc_type": "form",
                "owner": form.get("department", ""),
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

    Node types: Article, Workflow, Step, Form, Team, Role, System, Field,
                Location, Asset, Report
    Edge types: visible_to, owned_by, escalates_to, defined_in, has_step,
                precedes, done_in, requires, supersedes, located_at, produces
    """
    knowledge_graph.clear()

    articles = load_json("knowledge_articles.json")
    workflows = load_json("workflows.json")
    field_defs = load_json("field_definitions.json")
    forms = _load_json_optional("forms.json")
    locations = _load_json_optional("locations.json")
    assets = _load_json_optional("assets.json")
    reports = _load_json_optional("reports.json")
    teams_data = _load_json_optional("teams.json")
    systems_data = _load_json_optional("systems.json")

    # ----------------------------------------------------------------
    # Pre-build rich Team nodes from teams.json
    # ----------------------------------------------------------------
    for td in teams_data:
        tid = td["team_id"]
        knowledge_graph.add_node(
            tid,
            node_type="Team",
            title=td["name"],
            name=td["name"],
            department=td.get("department", ""),
            contact_extension=td.get("contact_extension", ""),
            escalation_sla=td.get("escalation_sla", ""),
            email=td.get("email", ""),
            handles=td.get("handles", []),
            status="approved",
        )

    # ----------------------------------------------------------------
    # Pre-build rich System nodes from systems.json
    # ----------------------------------------------------------------
    for sd in systems_data:
        sys_node_id = sd["system_id"]
        knowledge_graph.add_node(
            sys_node_id,
            node_type="System",
            title=sd["name"],
            name=sd["name"],
            vendor=sd.get("vendor", ""),
            login_url=sd.get("login_url", ""),
            description=sd.get("description", ""),
            department=sd.get("department", ""),
            support_contact=sd.get("support_contact", ""),
            status="approved",
        )

    # ----------------------------------------------------------------
    # Location nodes
    # ----------------------------------------------------------------
    for loc in locations:
        lid = loc["location_id"]
        knowledge_graph.add_node(
            lid,
            node_type="Location",
            title=loc["name"],
            name=loc["name"],
            building=loc.get("building", ""),
            floor=loc.get("floor", ""),
            department=loc.get("department", ""),
            bed_count=loc.get("bed_count", 0),
            room_type=loc.get("room_type", ""),
            phone_extension=loc.get("phone_extension", ""),
            status="approved",
        )
        # located_at: department team → location
        dept = loc.get("department", "")
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
            knowledge_graph.add_edge(tid, lid, "located_at")

    # ----------------------------------------------------------------
    # Asset nodes
    # ----------------------------------------------------------------
    for asset in assets:
        asg_id = asset["asset_id"]
        knowledge_graph.add_node(
            asg_id,
            node_type="Asset",
            title=asset["name"],
            name=asset["name"],
            asset_type=asset.get("type", ""),
            manufacturer=asset.get("manufacturer", ""),
            model=asset.get("model", ""),
            pm_schedule=asset.get("pm_schedule", ""),
            is_life_critical=asset.get("is_life_critical", False),
            serial_number=asset.get("serial_number", ""),
            installation_date=asset.get("installation_date", ""),
            warranty_expiry=asset.get("warranty_expiry", ""),
            status="approved",
        )
        # located_at → Location node
        loc_id = asset.get("location_id", "")
        if loc_id and knowledge_graph.get_node(loc_id):
            knowledge_graph.add_edge(asg_id, loc_id, "located_at")

        # owned_by → Team (department)
        dept = asset.get("department", "")
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
            knowledge_graph.add_edge(asg_id, tid, "owned_by")

    # ----------------------------------------------------------------
    # Report nodes
    # ----------------------------------------------------------------
    for rpt in reports:
        rpt_id = rpt["report_id"]
        knowledge_graph.add_node(
            rpt_id,
            node_type="Report",
            title=rpt["title"],
            name=rpt["title"],
            frequency=rpt.get("frequency", ""),
            department=rpt.get("department", ""),
            owner=rpt.get("owner", ""),
            description=rpt.get("description", ""),
            governing_article=rpt.get("governing_article", ""),
            produced_by_system=rpt.get("produced_by_system", ""),
            status="approved",
        )
        # produces: System → Report
        sys_name = rpt.get("produced_by_system", "")
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
            knowledge_graph.add_edge(sys_id, rpt_id, "produces")

        # owned_by → Team
        dept = rpt.get("department", "")
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
            knowledge_graph.add_edge(rpt_id, tid, "owned_by")

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

        # owned_by edge → Team node (merge with existing rich node if present)
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

        # supersedes edge (if article declares it)
        superseded = article.get("supersedes", "")
        if superseded and knowledge_graph.get_node(superseded):
            knowledge_graph.add_edge(aid, superseded, "supersedes")

    # ----------------------------------------------------------------
    # Form nodes
    # ----------------------------------------------------------------
    for form in forms:
        fmid = form["form_id"]
        knowledge_graph.add_node(
            fmid,
            node_type="Form",
            title=form["title"],
            name=form["title"],
            code=form.get("code", ""),
            department=form.get("department", ""),
            description=form.get("description", ""),
            download_path=form.get("download_path", ""),
            status="approved",
        )

        # defined_in → governing Article
        governing = form.get("governing_article", "")
        if governing and knowledge_graph.get_node(governing):
            knowledge_graph.add_edge(fmid, governing, "defined_in")

        # requires → Field nodes
        for field_name in form.get("fields", []):
            fid = _field_id(field_name)
            if knowledge_graph.get_node(fid) is None:
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
            knowledge_graph.add_edge(fmid, fid, "requires")

        # owned_by → Team
        dept = form.get("department", "")
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
            knowledge_graph.add_edge(fmid, tid, "owned_by")

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

            # done_in → System node (prefer rich node from systems.json if name matches)
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
