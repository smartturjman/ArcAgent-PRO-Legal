"""Test helpers for seeding Qdrant and monkeypatching embeddings.

Provides utilities used by test suites to create deterministic, isolated
test fixtures without calling external LLM services.
"""
from typing import Optional


def monkeypatch_dummy_embed(agent_module, vector_size: int = 768):
    """Monkeypatch `agent_module.setup_gemini_embedding` to return a dummy embedder.

    The dummy embedder returns zero vectors of length `vector_size` for both
    single and batch embedding calls.
    """
    class _DummyEmbed:
        def get_text_embedding(self, text: str):
            return [0.0] * vector_size

        def get_text_embedding_batch(self, texts):
            return [[0.0] * vector_size for _ in texts]

    try:
        agent_module.setup_gemini_embedding = lambda api_key=None: _DummyEmbed()
    except Exception:
        # Best-effort; tests should handle absence gracefully
        pass


def monkeypatch_seed_qdrant(agent_module, idx_module, num_points: int = 3, vector_size: int = 768, collection_name: str = "legal_documents"):
    """Monkeypatch `setup_qdrant_vector_store` used by the agent to seed points.

    This replaces the `idx_module.setup_qdrant_vector_store` behaviour with a wrapper
    that calls the original setup function and then upserts `num_points` dummy
    points (zero vectors) with simple payloads. The agent should import the
    same function (we also overwrite the reference in `agent_module`) so the
    seeding happens immediately after collection creation.
    """
    try:
        from qdrant_client.http.models import PointStruct
    except Exception:
        # If qdrant client models not available, skip seeding
        return

    original_setup = idx_module.setup_qdrant_vector_store

    def _setup_and_seed(*args, **kwargs):
        # Call original setup with whatever args/kwargs were provided
        client = original_setup(*args, **kwargs)

        # Determine collection name from kwargs or positional args or default
        if "collection_name" in kwargs:
            coll = kwargs.get("collection_name")
        elif len(args) >= 1:
            coll = args[0]
        else:
            coll = collection_name

        zero_vector = [0.0] * vector_size
        points = []
        for i in range(1, num_points + 1):
            payload = {
                "text": f"Seeded document #{i} - Golden Visa sample",
                "doc_id": f"sample_doc_{i}.txt",
                "chunk_idx": 0
            }
            pt = PointStruct(id=i, vector=zero_vector, payload=payload)
            points.append(pt)

        try:
            client.upsert(collection_name=coll, points=points)
        except Exception:
            # Fallback for different client versions
            client.upsert(points=points, collection_name=coll)

        return client

    # Overwrite both module references so agent uses the seeded setup
    try:
        idx_module.setup_qdrant_vector_store = _setup_and_seed
    except Exception:
        pass

    try:
        agent_module.setup_qdrant_vector_store = _setup_and_seed
    except Exception:
        pass
