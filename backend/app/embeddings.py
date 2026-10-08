import json
import os
import boto3
from chromadb import EmbeddingFunction, Documents, Embeddings

_bedrock = None

EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")


def _get_client():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )
    return _bedrock


def embed_text(text: str) -> list[float]:
    client = _get_client()
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    response = client.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


class TitanEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return [embed_text(text) for text in input]
