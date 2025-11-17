#!/usr/bin/env python3
"""Example: connect to local Qdrant and create a test collection.

This script connects to a Qdrant instance at http://localhost:6333,
deletes an existing `test_collection` if present, and creates a new one.

Run (from repo root):
  source ../venv/bin/activate
  python examples/connect_qdrant.py
"""
import os
import sys
from qdrant_client import QdrantClient
try:
    # qdrant-client types
    from qdrant_client.http.models import VectorParams, Distance
except Exception:
    VectorParams = None
    Distance = None

try:
    # optional: load local .env during development
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv not installed — rely on environment variables
    pass


def main():
    # Read Qdrant connection info from environment (supports Qdrant Cloud)
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY") or None
    print(f"Connecting to Qdrant at {url} (api_key set={bool(api_key)})...")
    # QdrantClient accepts `url` and `api_key` for cloud usage
    client = QdrantClient(url=url, api_key=api_key)

    collection_name = "test_collection"

    # list existing collections
    try:
        cols = client.get_collections()
        existing = [c.name for c in getattr(cols, 'collections', [])]
    except Exception as e:
        print("Failed to list collections:", e)
        existing = []

    if collection_name in existing:
        print(f"Collection '{collection_name}' exists — deleting it for a clean run...")
        try:
            client.delete_collection(collection_name)
        except Exception as e:
            print("Warning: failed to delete collection:", e)

    # create a collection (vector size chosen as 1536 as a common embedding size)
    print(f"Creating collection '{collection_name}'...")
    try:
        if VectorParams is not None and Distance is not None:
            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
        else:
            # fallback for older/newer client versions
            client.recreate_collection(collection_name=collection_name, vector_size=1536, distance="Cosine")
    except TypeError:
        # fallback: try create_collection
        try:
            client.create_collection(collection_name=collection_name, vector_size=1536, distance="Cosine")
        except Exception as e:
            print("Error creating collection:", e)
            sys.exit(2)
    except Exception as e:
        print("Error creating/recreating collection:", e)
        sys.exit(2)

    print("Collections after operation:")
    try:
        cols = client.get_collections()
        for c in getattr(cols, 'collections', []):
            print(" -", c.name)
    except Exception as e:
        print("Failed to list collections after creation:", e)


if __name__ == '__main__':
    main()
