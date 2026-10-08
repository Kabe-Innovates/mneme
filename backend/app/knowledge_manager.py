"""
Knowledge Manager — Living Second Brain

Manages the knowledge vault: per-item files, index, ingestion log.
Supports incremental indexing so adding one article doesn't rebuild everything.

Vault layout:
  knowledge_vault/
    articles/{article_id}.json
    workflows/{workflow_id}.json
    index.json          — manifest: what's in the brain, status, hash
    ingestion.log       — append-only: every ADD / APPROVE / REINDEX event
"""

import json
import os
import hashlib
import datetime
from typing import Optional

from app import vector_store, knowledge_graph

VAULT_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_vault")
INDEX_PATH = os.path.join(VAULT_DIR, "index.json")
LOG_PATH = os.path.join(VAULT_DIR, "ingestion.log")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _content_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


def _read_index() -> dict:
    if not os.path.exists(INDEX_PATH):
        return {"last_updated": _now(), "items": {}}
    with open(INDEX_PATH) as f:
        return json.load(f)


def _write_index(index: dict) -> None:
    index["last_updated"] = _now()
    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)


def _append_log(event: str, item_id: str, detail: str = "") -> None:
    line = f"{_now()} {event:<10} {item_id}  {detail}\n"
    with open(LOG_PATH, "a") as f:
        f.write(line)


def _article_to_vector_doc(article: dict) -> dict:
    aid = article["article_id"]
    return {
        "id": aid,
        "text": f"{article['title']}\n\n{article['content']}",
        "metadata": {
            "source_id": aid,
            "title": article["title"],
            "department": article.get("department", ""),
            "status": article.get("status", "approved"),
            "visible_to_roles": ",".join(article.get("visible_to_roles", ["ALL"])),
            "category": article.get("category", ""),
            "doc_type": "article",
            "version": article.get("version", "v1"),
            "owner": article.get("owner", ""),
        },
    }


def _workflow_to_vector_doc(wf: dict) -> dict:
    wid = wf["workflow_id"]
    step_text = "\n".join(
        f"Step {s['step_number']}: {s['description']}" for s in wf.get("steps", [])
    )
    return {
        "id": wid,
        "text": f"{wf['workflow_name']}\n\n{step_text}",
        "metadata": {
            "source_id": wid,
            "title": wf["workflow_name"],
            "department": wf.get("department", ""),
            "status": "approved",
            "visible_to_roles": "ALL",
            "category": "workflow",
            "doc_type": "workflow",
            "owner": wf.get("owner_team", ""),
        },
    }


def _index_article_to_graph(article: dict) -> dict:
    """Add a single article to the live NetworkX graph. Returns {nodes, edges} counts."""
    from app.data_loader import _team_id, _role_id  # reuse helpers

    aid = article["article_id"]
    nodes_added = 0
    edges_added = 0

    if knowledge_graph.get_node(aid) is None:
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
        nodes_added += 1

    for role_name in article.get("visible_to_roles", []):
        if role_name == "ALL":
            continue
        rid = _role_id(role_name)
        if knowledge_graph.get_node(rid) is None:
            knowledge_graph.add_node(rid, node_type="Role", title=role_name, name=role_name, status="approved")
            nodes_added += 1
        try:
            knowledge_graph.add_edge(aid, rid, "visible_to")
            edges_added += 1
        except Exception:
            pass

    dept = article.get("department", "")
    if dept:
        tid = _team_id(dept)
        if knowledge_graph.get_node(tid) is None:
            knowledge_graph.add_node(tid, node_type="Team", title=dept, name=dept, status="approved")
            nodes_added += 1
        try:
            knowledge_graph.add_edge(aid, tid, "owned_by")
            edges_added += 1
        except Exception:
            pass

    return {"nodes": nodes_added, "edges": edges_added}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_index() -> dict:
    """Return the full index."""
    return _read_index()


def get_log(lines: int = 100) -> list[str]:
    """Return the last N lines from the ingestion log."""
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        all_lines = f.readlines()
    return [l.rstrip() for l in all_lines[-lines:]]


def add_article(article_data: dict, submitted_by: str = "user") -> dict:
    """
    Store a new article in the vault as status=draft.
    Does NOT index into ChromaDB or graph — drafts are invisible to queries.
    Returns the assigned article_id.
    """
    article_id = article_data.get("article_id")
    if not article_id:
        raise ValueError("article_data must include 'article_id'")

    article_data["status"] = "draft"
    if "visible_to_roles" not in article_data:
        article_data["visible_to_roles"] = ["ALL"]

    fp = f"articles/{article_id}.json"
    full_path = os.path.join(VAULT_DIR, fp)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        json.dump(article_data, f, indent=2)

    index = _read_index()
    index["items"][article_id] = {
        "file": fp,
        "type": "article",
        "status": "draft",
        "version": article_data.get("version", "v1"),
        "content_hash": _content_hash(article_data),
        "indexed_at": None,
        "department": article_data.get("department", ""),
        "title": article_data.get("title", ""),
    }
    _write_index(index)
    _append_log("ADD", article_id, f"v{article_data.get('version','1')}  draft  by={submitted_by}")

    return {"article_id": article_id, "status": "draft"}


def approve_article(article_id: str, approved_by: str = "supervisor") -> dict:
    """
    Approve a draft article:
      1. Sets status=approved in the vault file and index
      2. Upserts into ChromaDB (single document, ~50ms)
      3. Adds nodes + edges into the live NetworkX graph (O(1))
      4. Logs APPROVE + REINDEX events
    Returns {nodes_added, edges_added, message}
    """
    index = _read_index()
    entry = index["items"].get(article_id)
    if not entry:
        raise ValueError(f"Article '{article_id}' not found in index")

    fp = os.path.join(VAULT_DIR, entry["file"])
    with open(fp) as f:
        article = json.load(f)

    article["status"] = "approved"
    with open(fp, "w") as f:
        json.dump(article, f, indent=2)

    entry["status"] = "approved"
    entry["content_hash"] = _content_hash(article)
    _write_index(index)
    _append_log("APPROVE", article_id, f"approved  by={approved_by}")

    # Incremental indexing — no rebuild needed
    graph_stats = {"nodes": 0, "edges": 0}
    vector_ok = False

    try:
        doc = _article_to_vector_doc(article)
        vector_store.upsert_document(doc)
        vector_ok = True
    except Exception as e:
        _append_log("ERROR", article_id, f"vector upsert failed: {e}")

    if knowledge_graph.is_loaded():
        try:
            graph_stats = _index_article_to_graph(article)
        except Exception as e:
            _append_log("ERROR", article_id, f"graph index failed: {e}")

    # Update indexed_at in index
    index = _read_index()
    index["items"][article_id]["indexed_at"] = _now()
    _write_index(index)

    detail = f"vector={'ok' if vector_ok else 'err'}  nodes={graph_stats['nodes']}  edges={graph_stats['edges']}"
    _append_log("REINDEX", article_id, detail)

    return {
        "article_id": article_id,
        "status": "approved",
        "vector_indexed": vector_ok,
        "nodes_added": graph_stats["nodes"],
        "edges_added": graph_stats["edges"],
    }


def update_article(article_id: str, updates: dict, updated_by: str = "user") -> dict:
    """
    Update fields on an existing article (any status).
    If it was approved, re-indexes immediately.
    If it was draft, just saves the file.
    """
    index = _read_index()
    entry = index["items"].get(article_id)
    if not entry:
        raise ValueError(f"Article '{article_id}' not found in index")

    fp = os.path.join(VAULT_DIR, entry["file"])
    with open(fp) as f:
        article = json.load(f)

    article.update(updates)
    with open(fp, "w") as f:
        json.dump(article, f, indent=2)

    entry["content_hash"] = _content_hash(article)
    entry["title"] = article.get("title", entry.get("title", ""))
    _write_index(index)
    _append_log("UPDATE", article_id, f"by={updated_by}")

    if entry["status"] == "approved":
        return approve_article(article_id, approved_by=updated_by)

    return {"article_id": article_id, "status": entry["status"], "updated": True}


def list_items(status_filter: Optional[str] = None) -> list[dict]:
    """Return index items, optionally filtered by status (approved/draft)."""
    index = _read_index()
    items = []
    for item_id, meta in index["items"].items():
        if status_filter and meta.get("status") != status_filter:
            continue
        items.append({"id": item_id, **meta})
    items.sort(key=lambda x: x.get("indexed_at") or "", reverse=True)
    return items
