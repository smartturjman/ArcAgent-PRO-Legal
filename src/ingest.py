#!/usr/bin/env python3
"""Data ingestion module using LlamaIndex and Unstructured.

Loads and parses bilingual documents from a /data directory using
LlamaIndex's SimpleDirectoryReader with Unstructured backend.

Usage:
  python src/ingest.py --data-dir data/ --chunk-size 512 --chunk-overlap 20
"""

import os
import sys
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from llama_index.readers.file import UnstructuredReader
from llama_index.core.schema import Document
from llama_index.core.text_splitter import SentenceSplitter


def load_documents(data_dir: str = "data") -> List[Document]:
    """Load documents from a directory using UnstructuredReader backend.
    
    Args:
        data_dir: Path to directory containing documents (default: "data")
        
    Returns:
        List of LlamaIndex Document objects
    """
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"Warning: data directory '{data_dir}' does not exist. Creating it...")
        data_path.mkdir(parents=True, exist_ok=True)
        print(f"Created {data_dir}/ — add documents there and rerun.")
        return []
    
    print(f"Loading documents from {data_dir}/...")
    
    # Find all supported files in the directory
    supported_exts = [".pdf", ".docx", ".txt", ".md", ".html", ".rtf", ".csv", ".xlsx", ".pptx"]
    document_files = []
    
    for ext in supported_exts:
        document_files.extend(data_path.glob(f"**/*{ext}"))
    
    if not document_files:
        print(f"No supported documents found in {data_dir}/")
        print(f"Supported formats: {', '.join(supported_exts)}")
        return []
    
    print(f"Found {len(document_files)} document(s)")
    
    documents = []
    reader = UnstructuredReader()
    
    for file_path in document_files:
        print(f"  Loading: {file_path.relative_to(data_path)}")
        try:
            file_docs = reader.load_data(file=str(file_path))
            for doc in file_docs:
                # Preserve file path in metadata
                if not doc.metadata:
                    doc.metadata = {}
                doc.metadata["file_path"] = str(file_path.relative_to(data_path))
            documents.extend(file_docs)
        except Exception as e:
            print(f"    Warning: Error loading {file_path}: {e}")
    
    print(f"Loaded {len(documents)} documents from {data_dir}/")
    return documents


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 512,
    chunk_overlap: int = 20
) -> List[Document]:
    """Chunk documents into smaller pieces for better embedding and retrieval.
    
    Args:
        documents: List of documents to chunk
        chunk_size: Number of tokens per chunk (default: 512)
        chunk_overlap: Number of overlapping tokens between chunks (default: 20)
        
    Returns:
        List of chunked documents
    """
    if not documents:
        print("No documents to chunk.")
        return []
    
    print(f"Chunking {len(documents)} documents (chunk_size={chunk_size}, overlap={chunk_overlap})...")
    
    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    chunked_docs = []
    for doc in documents:
        content = doc.get_content()
        splits = splitter.split_text(content)
        for i, split in enumerate(splits):
            # Create a new document for each chunk with metadata
            chunk_doc = Document(
                text=split,
                metadata={
                    **(doc.metadata or {}),
                    "source": (doc.metadata or {}).get("file_path", "unknown"),
                    "chunk_index": i
                }
            )
            chunked_docs.append(chunk_doc)
    
    print(f"Created {len(chunked_docs)} chunks from {len(documents)} documents")
    return chunked_docs


def main():
    """Main ingestion pipeline: load documents and chunk them."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest and chunk documents")
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size in tokens")
    parser.add_argument("--chunk-overlap", type=int, default=20, help="Chunk overlap in tokens")
    parser.add_argument("--verbose", action="store_true", help="Print document details")
    args = parser.parse_args()
    
    # Load documents
    documents = load_documents(data_dir=args.data_dir)
    
    if not documents:
        print("No documents loaded. Exiting.")
        return
    
    if args.verbose:
        for doc in documents:
            metadata = doc.metadata or {}
            print(f"  - {metadata.get('file_path', 'unknown')}: {len(doc.get_content())} chars")
    
    # Chunk documents
    chunked_docs = chunk_documents(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    if chunked_docs and args.verbose:
        print("\nSample chunks (first 3):")
        for i, doc in enumerate(chunked_docs[:3]):
            metadata = doc.metadata or {}
            print(f"\n  Chunk {i+1}:")
            print(f"    Source: {metadata.get('source')}")
            print(f"    Text: {doc.get_content()[:100]}...")
    
    print("\nData ingestion complete!")
    return documents, chunked_docs


if __name__ == "__main__":
    main()
