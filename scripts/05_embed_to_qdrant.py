# scripts/05_embed_to_qdrant.py
import os
import sys

import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

EMBED_URL = os.environ.get("EMBED_NGROK_URL", "")
LOCAL_EMBED = os.environ.get("LOCAL_EMBED", "0") == "1"
qdrant = QdrantClient(host="localhost", port=6333)

_local_model = None


import hashlib
import math


def _hash_embed(text: str, dim: int = 384) -> list[float]:
    """Deterministic pseudo-embedding for local dev when no embed service is available."""
    digest = hashlib.sha256(text.encode()).digest()
    values = []
    while len(values) < dim:
        for byte in digest:
            values.append((byte / 127.5) - 1.0)
            if len(values) == dim:
                break
        digest = hashlib.sha256(digest).digest()
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def get_embeddings(texts: list[str]) -> list[list[float]]:
    global _local_model

    if EMBED_URL and not LOCAL_EMBED:
        embed_base = EMBED_URL.rstrip("/")
        response = requests.post(f"{embed_base}/embed", json={"texts": texts}, timeout=60)
        response.raise_for_status()
        return response.json()["embeddings"]

    if LOCAL_EMBED:
        try:
            if _local_model is None:
                from sentence_transformers import SentenceTransformer

                print("Using local sentence-transformers (BAAI/bge-small-en-v1.5)")
                _local_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            return _local_model.encode(texts).tolist()
        except ImportError:
            print("Using hash-based local embeddings (install sentence-transformers for real vectors)")

    return [_hash_embed(text) for text in texts]


def ensure_collection():
    resp = requests.get("http://localhost:6333/collections/documents", timeout=5)
    if resp.status_code == 404:
        qdrant.create_collection(
            collection_name="documents",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        return
    resp.raise_for_status()
    size = resp.json()["result"]["config"]["params"]["vectors"]["size"]
    if size != 384:
        qdrant.recreate_collection(
            collection_name="documents",
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )


def embed_and_store(records: list[dict]):
    ensure_collection()
    embeddings = get_embeddings([r["text"] for r in records])
    points = [
        PointStruct(id=hash(rec["id"]) % (2**63), vector=emb, payload=rec)
        for emb, rec in zip(embeddings, records)
    ]
    qdrant.upsert(collection_name="documents", points=points)
    print(f"Integration 5 OK: {len(points)} vectors stored in Qdrant")


if __name__ == "__main__":
    embed_and_store(
        [
            {"id": "doc_001", "text": "AI platform integration test"},
            {"id": "doc_002", "text": "Kafka to Airflow pipeline"},
            {"id": "smoke_001", "text": "smoke test document"},
        ]
    )
