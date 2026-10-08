import json
import os
from app import vector_store

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_json(filename: str) -> list:
    path = os.path.join(DATA_DIR, filename)
    with open(path) as f:
        return json.load(f)


def ingest_all():
    docs = []

    # Ingest knowledge articles
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

    # Ingest workflow steps as searchable documents
    workflows = load_json("workflows.json")
    for wf in workflows:
        # Index the whole workflow as one doc
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
    print(f"[DataLoader] Ingestion complete — {len(docs)} documents indexed")
