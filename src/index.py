#!/usr/bin/env python3
"""Indexing module: embed documents using Gemini and push to Qdrant.

This script loads documents from ingest.py, embeds them using Google's
Gemini embedding model (supports bilingual data), and stores them in
Qdrant Cloud or local Qdrant instance using direct Qdrant client API.

Usage:
  python src/index.py --data-dir data --qdrant-url http://localhost:6333 --qdrant-api-key ""
  python src/index.py --data-dir data --qdrant-url https://YOUR-QDRANT-CLOUD-URL --qdrant-api-key YOUR-KEY
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from llama_index.embeddings.gemini import GeminiEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance

# Import ingest module to reuse document loading and chunking
from ingest import load_documents, chunk_documents


def setup_gemini_embedding(api_key: Optional[str] = None) -> GeminiEmbedding:
    """Initialize Gemini embedding model.
    
    Args:
        api_key: Google API key. If None, uses GEMINI_API_KEY env var.
        
    Returns:
        GeminiEmbedding instance configured for bilingual embeddings
    """
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Set it in .env or via environment variable."
        )
    
    print("Initializing Gemini embedding model (bilingual support)...")
    
    # GeminiEmbedding uses 'models/embedding-001' by default
    # This model supports multilingual embeddings
    embedding = GeminiEmbedding(
        api_key=api_key,
        model_name="models/embedding-001"
    )
    
    print("✓ Gemini embedding model ready")
    return embedding


def setup_qdrant_vector_store(
    collection_name: str = "legal_documents",
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None
) -> QdrantClient:
    """Initialize Qdrant client (Cloud or local).
    
    Args:
        collection_name: Name of the Qdrant collection
        qdrant_url: Qdrant server URL (local or cloud)
        qdrant_api_key: API key for Qdrant Cloud
        
    Returns:
        QdrantClient instance
    """
    if qdrant_url is None:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    
    if qdrant_api_key is None:
        qdrant_api_key = os.getenv("QDRANT_API_KEY") or None
    
    print(f"Connecting to Qdrant at {qdrant_url}...")
    
    # Initialize Qdrant client
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    
    # Check if collection exists; delete and recreate for clean indexing
    try:
        existing_collections = [c.name for c in client.get_collections().collections]
        if collection_name in existing_collections:
            print(f"Collection '{collection_name}' exists. Deleting for fresh indexing...")
            client.delete_collection(collection_name)
    except Exception as e:
        print(f"Warning: Could not check existing collections: {e}")
    
    # Create collection with vector configuration
    print(f"Creating collection '{collection_name}' with vector configuration...")
    try:
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
    except Exception as e:
        print(f"Warning during collection creation: {e}")
    
    print(f"✓ Qdrant client ready (collection: {collection_name})")
    return client


def index_documents(
    documents_path: str = "data",
    collection_name: str = "legal_documents",
    chunk_size: int = 512,
    chunk_overlap: int = 20,
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None
) -> QdrantClient:
    """Main indexing pipeline: load, embed, and store documents.
    
    Args:
        documents_path: Path to documents directory
        collection_name: Qdrant collection name
        chunk_size: Document chunk size
        chunk_overlap: Chunk overlap in tokens
        qdrant_url: Qdrant server URL
        qdrant_api_key: Qdrant API key
        gemini_api_key: Google API key for embeddings
        
    Returns:
        QdrantClient instance
    """
    print("\n=== Data Ingestion & Indexing Pipeline ===\n")
    
    # Step 1: Load and chunk documents
    print("Step 1: Loading documents...")
    documents = load_documents(data_dir=documents_path)
    
    if not documents:
        print("No documents loaded. Exiting.")
        return None
    
    print(f"Step 2: Chunking {len(documents)} documents...")
    chunked_docs = chunk_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    if not chunked_docs:
        print("No chunks created. Exiting.")
        return None
    
    # Step 2: Setup Gemini embedding
    print("\nStep 3: Setting up Gemini embedding...")
    embedding = setup_gemini_embedding(api_key=gemini_api_key)
    
    # Step 3: Setup Qdrant client
    print("\nStep 4: Connecting to Qdrant...")
    qdrant_client = setup_qdrant_vector_store(
        collection_name=collection_name,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key
    )
    
    # Step 4: Embed chunks
    print(f"\nStep 5: Embedding {len(chunked_docs)} chunks with Gemini...")
    chunk_texts = [doc.get_content() for doc in chunked_docs]
    
    try:
        embeddings = embedding.get_text_embedding_batch(chunk_texts)
        print(f"✓ Generated {len(embeddings)} embeddings")
    except Exception as e:
        print(f"✗ Embedding failed: {e}", file=sys.stderr)
        print("Ensure GEMINI_API_KEY is set and valid")
        return None
    
    # Step 5: Insert embeddings into Qdrant
    print(f"\nStep 6: Storing embeddings in Qdrant collection '{collection_name}'...")
    points = []
    
    for idx, (chunk, embedding_vec) in enumerate(zip(chunked_docs, embeddings)):
        metadata = chunk.metadata or {}
        point = PointStruct(
            id=idx,
            vector=embedding_vec,
            payload={
                "text": chunk.get_content(),
                "doc_id": metadata.get("file_path", "unknown"),
                "chunk_idx": metadata.get("chunk_index", 0),
                **{k: str(v) for k, v in metadata.items() if k not in ["text", "doc_id", "chunk_idx"]}
            }
        )
        points.append(point)
    
    try:
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        print(f"✓ Stored {len(points)} point(s) in Qdrant")
    except Exception as e:
        print(f"✗ Failed to store points: {e}", file=sys.stderr)
        return None
    
    # Step 6: Verify storage
    print("\nStep 7: Verifying index...")
    try:
        collection_info = qdrant_client.get_collection(collection_name)
        print(f"✓ Collection verified: {collection_info.points_count} point(s) stored")
        print(f"  Vector size: {collection_info.config.params.vectors.size}")
        print(f"  Distance metric: {collection_info.config.params.vectors.distance}")
    except Exception as e:
        print(f"Warning during verification: {e}")
    
    print("\n=== Indexing Complete ===\n")
    print(f"✓ {len(chunked_docs)} chunks indexed in Qdrant")
    print(f"✓ Collection: {collection_name}")
    print(f"✓ Embedding model: Gemini (bilingual)")
    print(f"✓ Vector store: Qdrant ({qdrant_url or 'http://localhost:6333'})")
    
    return qdrant_client


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Index documents with Gemini embeddings and Qdrant")
    parser.add_argument("--data-dir", default="data", help="Path to documents directory")
    parser.add_argument("--collection-name", default="legal_documents", help="Qdrant collection name")
    parser.add_argument("--chunk-size", type=int, default=512, help="Document chunk size")
    parser.add_argument("--chunk-overlap", type=int, default=20, help="Chunk overlap in tokens")
    parser.add_argument("--qdrant-url", default=None, help="Qdrant server URL (uses env var if not set)")
    parser.add_argument("--qdrant-api-key", default=None, help="Qdrant API key (uses env var if not set)")
    parser.add_argument("--gemini-api-key", default=None, help="Gemini API key (uses env var if not set)")
    
    args = parser.parse_args()
    
    try:
        index = index_documents(
            documents_path=args.data_dir,
            collection_name=args.collection_name,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            qdrant_url=args.qdrant_url,
            qdrant_api_key=args.qdrant_api_key,
            gemini_api_key=args.gemini_api_key
        )
        
        if index:
            print("\n✓ Ready for RAG queries!")
            return 0
    except Exception as e:
        print(f"\n✗ Indexing failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
