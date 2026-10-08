"""
Reseed the Knowledge Vault from the expanded synthetic data files.

Clears the existing vault articles/ and workflows/ directories, regenerates
all item files, rebuilds index.json, and appends a RESEED entry to ingestion.log.

Usage:
    cd backend && python -I -m scripts.reseed_vault
"""

import json
import os
import sys
import hashlib
import datetime
import shutil

# Add parent directory so 'app' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
VAULT_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_vault")
ARTICLES_DIR = os.path.join(VAULT_DIR, "articles")
WORKFLOWS_DIR = os.path.join(VAULT_DIR, "workflows")
INDEX_PATH = os.path.join(VAULT_DIR, "index.json")
LOG_PATH = os.path.join(VAULT_DIR, "ingestion.log")


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _content_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


def _load_json(filename: str) -> list:
    path = os.path.join(DATA_DIR, filename)
    with open(path) as f:
        return json.load(f)


def _append_log(event: str, item_id: str, detail: str = "") -> None:
    line = f"{_now()} {event:<12} {item_id}  {detail}\n"
    with open(LOG_PATH, "a") as f:
        f.write(line)


def reseed():
    # Ensure vault directories exist
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    os.makedirs(WORKFLOWS_DIR, exist_ok=True)

    # Clear existing vault item files (not index or log)
    for f in os.listdir(ARTICLES_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(ARTICLES_DIR, f))
    for f in os.listdir(WORKFLOWS_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(WORKFLOWS_DIR, f))

    articles = _load_json("knowledge_articles.json")
    workflows = _load_json("workflows.json")

    index = {"last_updated": _now(), "items": {}}

    article_count = 0
    for article in articles:
        aid = article["article_id"]
        dest = os.path.join(ARTICLES_DIR, f"{aid}.json")
        with open(dest, "w") as f:
            json.dump(article, f, indent=2)
        content_hash = _content_hash(article)
        index["items"][aid] = {
            "type": "article",
            "title": article["title"],
            "department": article.get("department", ""),
            "status": article.get("status", "approved"),
            "version": article.get("version", ""),
            "content_hash": content_hash,
            "indexed_at": _now(),
            "review_due_date": article.get("review_due_date", ""),
        }
        article_count += 1

    workflow_count = 0
    for wf in workflows:
        wid = wf["workflow_id"]
        dest = os.path.join(WORKFLOWS_DIR, f"{wid}.json")
        with open(dest, "w") as f:
            json.dump(wf, f, indent=2)
        content_hash = _content_hash(wf)
        index["items"][wid] = {
            "type": "workflow",
            "title": wf["workflow_name"],
            "department": wf.get("department", ""),
            "status": "approved",
            "version": "v1.0",
            "content_hash": content_hash,
            "indexed_at": _now(),
            "review_due_date": "",
        }
        workflow_count += 1

    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)

    _append_log("RESEED", "ALL", f"articles={article_count} workflows={workflow_count} total={article_count+workflow_count}")

    print(f"[Reseed] Vault reseeded:")
    print(f"  Articles:  {article_count}")
    print(f"  Workflows: {workflow_count}")
    print(f"  Total:     {article_count + workflow_count}")
    print(f"  Index:     {INDEX_PATH}")
    print(f"  Log:       {LOG_PATH}")


if __name__ == "__main__":
    reseed()
