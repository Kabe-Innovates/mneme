"""
Mneme Knowledge Graph — "Second Brain" Engine

NetworkX-backed in-memory DAG with 11 node types and 11 edge types.
Provides BFS subgraph traversal with:
  - Cycle protection via visited set
  - Back-edge masking on 'precedes' edges
  - Supernode penalty: W(u,v) = 1/log(1+degree(v)), drop if < TAU
  - Role-based access control (RBAC) filtering
  - Trust/confidence scoring per architecture spec
"""

import math
from collections import Counter, deque
from datetime import date

import networkx as nx

# --- Constants ---

VALID_NODE_TYPES = {
    "Article", "Workflow", "Step", "Form",
    "System", "Team", "Role", "Field",
    "Location", "Asset", "Report",
}

VALID_EDGE_TYPES = {
    "defined_in", "has_step", "precedes", "requires",
    "done_in", "owned_by", "escalates_to", "supersedes",
    "visible_to", "located_at", "produces",
}

# Supernode penalty threshold — neighbors with W < TAU are pruned
TAU = 0.15

# Global graph instance
_graph: nx.DiGraph = nx.DiGraph()
_loaded: bool = False


# ---------------------------------------------------------------------------
# Construction API
# ---------------------------------------------------------------------------

def add_node(node_id: str, node_type: str, **attrs) -> None:
    if node_type not in VALID_NODE_TYPES:
        raise ValueError(f"Unknown node type: {node_type}")
    _graph.add_node(node_id, node_type=node_type, **attrs)


def add_edge(from_id: str, to_id: str, edge_type: str) -> None:
    if edge_type not in VALID_EDGE_TYPES:
        raise ValueError(f"Unknown edge type: {edge_type}")
    # Auto-create placeholder nodes if they don't exist (defensive)
    if from_id not in _graph:
        _graph.add_node(from_id, node_type="Unknown")
    if to_id not in _graph:
        _graph.add_node(to_id, node_type="Unknown")
    _graph.add_edge(from_id, to_id, edge_type=edge_type)


def get_node(node_id: str) -> dict | None:
    if node_id not in _graph:
        return None
    return dict(_graph.nodes[node_id])


def clear() -> None:
    global _loaded
    _graph.clear()
    _loaded = False


def mark_loaded() -> None:
    global _loaded
    _loaded = True


def is_loaded() -> bool:
    return _loaded


def get_stats() -> dict:
    type_counts = Counter(
        data.get("node_type", "Unknown")
        for _, data in _graph.nodes(data=True)
    )
    edge_type_counts = Counter(
        data.get("edge_type", "unknown")
        for _, _, data in _graph.edges(data=True)
    )
    return {
        "total_nodes": _graph.number_of_nodes(),
        "total_edges": _graph.number_of_edges(),
        "node_types": dict(type_counts),
        "edge_types": dict(edge_type_counts),
    }


# ---------------------------------------------------------------------------
# RBAC helper
# ---------------------------------------------------------------------------

def _is_visible(node_id: str, role: str) -> bool:
    """Return True if this node is accessible to the given role."""
    node_data = _graph.nodes.get(node_id, {})
    visible_to = node_data.get("visible_to_roles")
    if not visible_to:
        return True  # no restriction
    if visible_to == "ALL" or "ALL" in visible_to:
        return True
    if isinstance(visible_to, list):
        return role in visible_to
    if isinstance(visible_to, str):
        return role in visible_to.split(",")
    return True


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

def traverse_subgraph(
    start_node_ids: list[str],
    role: str,
    max_hops: int = 2,
    max_nodes: int = 15,
) -> dict:
    """
    BFS from start_node_ids along typed edges.

    Returns:
        {
          "nodes": [{"node_id", "node_type", "title", "attrs"}],
          "edges": [{"from", "edge_type", "to"}],
          "node_type_counts": Counter,
        }
    """
    # Filter start nodes to only those that exist in the graph
    valid_starts = [n for n in start_node_ids if n in _graph]
    if not valid_starts:
        return {"nodes": [], "edges": [], "node_type_counts": Counter()}

    visited: set[str] = set()
    edges_collected: list[dict] = []
    frontier: deque[str] = deque(valid_starts)

    # BFS loop, hop-bounded
    for _hop in range(max_hops):
        if not frontier or len(visited) >= max_nodes:
            break
        next_frontier: deque[str] = deque()

        while frontier:
            node_id = frontier.popleft()
            if node_id in visited or len(visited) >= max_nodes:
                continue

            # RBAC check
            if not _is_visible(node_id, role):
                continue

            visited.add(node_id)

            # Expand neighbors
            for neighbor_id, edge_data in _graph[node_id].items():
                edge_type = edge_data.get("edge_type", "")

                # Mask back-edges on 'precedes' to prevent cycle traps
                if edge_type == "precedes" and neighbor_id in visited:
                    continue

                # Supernode penalty: penalize highly-connected hub nodes
                degree = _graph.degree(neighbor_id)
                weight = 1.0 / math.log(1 + degree) if degree > 0 else 1.0
                if weight < TAU:
                    continue

                edges_collected.append({
                    "from": node_id,
                    "edge_type": edge_type,
                    "to": neighbor_id,
                })
                next_frontier.append(neighbor_id)

        frontier = next_frontier

    # Build node detail list
    node_details = []
    for nid in visited:
        if nid not in _graph:
            continue
        ndata = dict(_graph.nodes[nid])
        node_details.append({
            "node_id": nid,
            "node_type": ndata.get("node_type", "Unknown"),
            "title": ndata.get("title") or ndata.get("name") or nid,
            "attrs": ndata,
        })

    type_counts = Counter(n["node_type"] for n in node_details)

    return {
        "nodes": node_details,
        "edges": edges_collected,
        "node_type_counts": type_counts,
    }


# ---------------------------------------------------------------------------
# Context bundle assembly
# ---------------------------------------------------------------------------

# Priority order for LLM context: Articles first (authoritative), then
# Workflows/Steps (procedural), then supporting entities (Teams, Systems, Fields)
NODE_PRIORITY = {
    "Article": 0,
    "Workflow": 1,
    "Step": 2,
    "Field": 3,
    "System": 4,
    "Team": 5,
    "Form": 6,
    "Role": 7,
    "Location": 8,
    "Asset": 9,
    "Report": 10,
    "Unknown": 99,
}


def build_context_bundle(subgraph: dict) -> list[dict]:
    """
    Convert a traversal subgraph into LLM-ready context documents.

    Articles and Workflows include their full content/description.
    Supporting entities (Teams, Systems, Fields) are summarised concisely.
    """
    nodes = sorted(
        subgraph["nodes"],
        key=lambda n: NODE_PRIORITY.get(n["node_type"], 99),
    )
    edges = subgraph["edges"]

    # Build neighbour map for "connected_to" annotations
    neighbours: dict[str, list[str]] = {}
    for e in edges:
        neighbours.setdefault(e["from"], []).append(
            f"{e['edge_type']} → {e['to']}"
        )

    bundle = []
    for node in nodes:
        nid = node["node_id"]
        ntype = node["node_type"]
        attrs = node["attrs"]
        connected = neighbours.get(nid, [])

        content = _node_to_content(nid, ntype, attrs, connected)
        if content:
            bundle.append({
                "source_id": nid,
                "title": node["title"],
                "content": content,
                "node_type": ntype,
                "connected_to": connected,
            })

    return bundle


def _node_to_content(nid: str, ntype: str, attrs: dict, connected: list[str]) -> str:
    """Format a graph node into a readable text block for LLM context."""
    lines = []

    if ntype == "Article":
        body = attrs.get("content") or attrs.get("body", "")
        lines.append(f"Policy/SOP [{nid}]: {attrs.get('title', '')}")
        if attrs.get("version"):
            lines.append(f"Version: {attrs['version']} | Effective: {attrs.get('effective_date', 'N/A')}")
        if attrs.get("owner"):
            lines.append(f"Owner: {attrs['owner']} | Department: {attrs.get('department', '')}")
        if body:
            lines.append(f"\n{body}")

    elif ntype == "Workflow":
        lines.append(f"Workflow [{nid}]: {attrs.get('title') or attrs.get('workflow_name', '')}")
        lines.append(f"Department: {attrs.get('department', '')} | Owner Team: {attrs.get('owner_team', '')}")
        if attrs.get("escalation_team"):
            lines.append(f"Escalation Team: {attrs['escalation_team']}")

    elif ntype == "Step":
        lines.append(f"Step {attrs.get('step_number', '?')} [{nid}]: {attrs.get('title') or attrs.get('description', '')}")
        if attrs.get("system_used"):
            lines.append(f"System: {attrs['system_used']}")
        if attrs.get("required_fields"):
            fields = attrs["required_fields"]
            if isinstance(fields, list):
                lines.append(f"Required fields: {', '.join(fields)}")
        if attrs.get("is_approval_gate"):
            lines.append("⚠ APPROVAL GATE: Requires supervisor sign-off before proceeding.")

    elif ntype == "Team":
        lines.append(f"Team [{nid}]: {attrs.get('name') or attrs.get('title', nid)}")
        if attrs.get("contact_extension"):
            lines.append(f"Contact: ext {attrs['contact_extension']}")
        if attrs.get("escalation_sla"):
            lines.append(f"SLA: {attrs['escalation_sla']}")

    elif ntype == "System":
        lines.append(f"System [{nid}]: {attrs.get('name') or attrs.get('title', nid)}")
        if attrs.get("vendor"):
            lines.append(f"Vendor: {attrs['vendor']}")
        if attrs.get("login_url"):
            lines.append(f"Access: {attrs['login_url']}")

    elif ntype == "Field":
        lines.append(f"Required Field [{nid}]: {attrs.get('label') or attrs.get('name', nid)}")
        lines.append(f"Type: {attrs.get('field_type', 'string')} | Required: {attrs.get('is_required', True)}")
        if attrs.get("allowed_values"):
            vals = attrs["allowed_values"]
            if isinstance(vals, list):
                lines.append(f"Allowed values: {', '.join(str(v) for v in vals)}")
        if attrs.get("validation_regex"):
            lines.append(f"Format: {attrs['validation_regex']}")
        if attrs.get("is_sensitive"):
            lines.append("🔒 Sensitive — handle with care.")

    elif ntype == "Form":
        lines.append(f"Form [{nid}]: {attrs.get('title') or attrs.get('code', nid)}")
        if attrs.get("download_path"):
            lines.append(f"Download: {attrs['download_path']}")

    else:
        # Generic fallback for Role, Location, Asset, Report
        title = attrs.get("title") or attrs.get("name") or nid
        lines.append(f"{ntype} [{nid}]: {title}")

    if connected:
        lines.append(f"Connections: {'; '.join(connected[:5])}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trust / Confidence Scoring
# ---------------------------------------------------------------------------

def compute_trust_score(
    subgraph: dict,
    vector_similarity: float,
) -> tuple[float, dict]:
    """
    Composite trust score.

    S = 0.35 * T_trust + 0.30 * C_coverage + 0.20 * G_connectivity + 0.15 * Sim_retrieval

    Returns (score, coverage_breakdown) where coverage_breakdown maps the 5
    operational questions to 0/1 — surfaced directly in the API response.
    """
    nodes = subgraph.get("nodes", [])
    edges = subgraph.get("edges", [])

    default_coverage = {"WHAT": 0, "WHERE": 0, "NEXT": 0, "WHO": 0, "HOW": 0}
    if not nodes:
        return max(0.0, min(1.0, vector_similarity)), default_coverage

    # --- T_trust (0.35): document freshness and approval status ---
    today = date.today().isoformat()
    approved_count = 0
    total_articles = 0
    for n in nodes:
        if n["node_type"] == "Article":
            total_articles += 1
            attrs = n["attrs"]
            if attrs.get("status") == "approved":
                review_due = attrs.get("review_due_date", "9999-12-31")
                if not review_due or review_due >= today:
                    approved_count += 1
                else:
                    approved_count += 0.5
    T_trust = (approved_count / total_articles) if total_articles > 0 else 0.8

    # --- C_coverage (0.30): 5-question framework ---
    # WHAT: approved Article in subgraph
    # WHERE: System or Location node present
    # NEXT: Step or Workflow node present (procedural path exists)
    # WHO: Team or Role node present (ownership known)
    # HOW: Field or Form node present (field-level detail available)
    type_set = {n["node_type"] for n in nodes}
    edge_types = {e["edge_type"] for e in edges}
    coverage_map = {
        "WHAT": int(bool(type_set & {"Article"})),
        "WHERE": int(bool(type_set & {"System", "Location"}) or "done_in" in edge_types),
        "NEXT": int(bool(type_set & {"Step", "Workflow"}) or "has_step" in edge_types),
        "WHO": int(bool(type_set & {"Team", "Role"}) or "owned_by" in edge_types or "escalates_to" in edge_types),
        "HOW": int(bool(type_set & {"Field", "Form"}) or "requires" in edge_types),
    }
    C_coverage = sum(coverage_map.values()) / 5.0

    # --- G_connectivity (0.20): edge density of subgraph ---
    n_nodes = len(nodes)
    n_edges = len(edges)
    max_edges = n_nodes * (n_nodes - 1) if n_nodes > 1 else 1
    G_connectivity = min(1.0, n_edges / max_edges * 5)

    # --- Sim_retrieval (0.15): vector similarity passed in ---
    Sim_retrieval = max(0.0, min(1.0, vector_similarity))

    score = (
        0.35 * T_trust
        + 0.30 * C_coverage
        + 0.20 * G_connectivity
        + 0.15 * Sim_retrieval
    )
    return round(min(1.0, max(0.0, score)), 3), coverage_map
