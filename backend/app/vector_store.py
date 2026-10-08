import chromadb
from chromadb.utils import embedding_functions
import os

_client = None
_collection = None

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Try Titan embeddings; fall back to local sentence-transformers if Bedrock unavailable
    try:
        from app.embeddings import TitanEmbeddingFunction
        # Quick test to see if Bedrock is reachable
        ef = TitanEmbeddingFunction()
        ef(["test"])
        embed_fn = ef
        print("[VectorStore] Using AWS Bedrock Titan embeddings")
    except Exception as e:
        print(f"[VectorStore] Titan unavailable ({e}), falling back to local embeddings")
        embed_fn = embedding_functions.DefaultEmbeddingFunction()

    _collection = _client.get_or_create_collection(
        name="mneme_knowledge",
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def ingest_documents(docs: list[dict]):
    col = _get_collection()
    existing = set(col.get()["ids"])

    new_docs = [d for d in docs if d["id"] not in existing]
    if not new_docs:
        print(f"[VectorStore] All {len(docs)} documents already ingested, skipping")
        return

    col.add(
        ids=[d["id"] for d in new_docs],
        documents=[d["text"] for d in new_docs],
        metadatas=[d["metadata"] for d in new_docs],
    )
    print(f"[VectorStore] Ingested {len(new_docs)} new documents")


def search(query: str, role: str, n_results: int = 5) -> list[dict]:
    col = _get_collection()
    results = col.query(
        query_texts=[query],
        n_results=min(n_results * 2, 20),  # Over-fetch for post-filtering
        where={"status": "approved"},
    )

    if not results["ids"][0]:
        return []

    docs = []
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i] if results.get("distances") else 0.5

        # Role-based access: check visible_to_roles
        visible = meta.get("visible_to_roles", "ALL")
        if visible != "ALL" and role not in visible:
            continue

        relevance = round(max(0.0, 1.0 - distance), 3)
        docs.append({
            "source_id": meta.get("source_id", doc_id),
            "title": meta.get("title", ""),
            "content": results["documents"][0][i],
            "department": meta.get("department", ""),
            "category": meta.get("category", ""),
            "relevance": relevance,
        })

        if len(docs) >= n_results:
            break

    return docs


def upsert_document(doc: dict) -> None:
    """Insert or update a single document (Living Second Brain incremental indexing)."""
    col = _get_collection()
    col.upsert(
        ids=[doc["id"]],
        documents=[doc["text"]],
        metadatas=[doc["metadata"]],
    )


def collection_count() -> int:
    return _get_collection().count()
