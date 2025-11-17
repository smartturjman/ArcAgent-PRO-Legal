# Indexing Setup & Testing Guide

## Overview

The indexing pipeline (`src/index.py`) is now complete and ready to use. It:
1. **Loads** documents from the `data/` directory using UnstructuredReader
2. **Chunks** documents into overlapping segments for better embeddings
3. **Embeds** chunks using Google Generative AI (Gemini `embedding-001` model) with **bilingual support**
4. **Stores** embeddings in Qdrant vector database (Cloud or local)

## Key Changes from Previous Attempts

**Problem:** The `llama-index-vector-stores-qdrant` wrapper had incompatible version requirements (`llama-index-core<0.11`) while the project uses `llama-index-core==0.14.8`.

**Solution:** Rewrote `src/index.py` to use the **direct Qdrant client API** (`qdrant-client==1.15.1`), bypassing the wrapper. This approach is:
- ✓ Compatible with all installed versions
- ✓ Simpler and more transparent
- ✓ Proven to work (examples/connect_qdrant.py validates the connection)

## Prerequisites

### 1. Create `.env` File
Copy the template and add your API keys:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
# Get from https://ai.google.dev/
GEMINI_API_KEY=your_api_key_here

# For local Qdrant (Docker)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# For Qdrant Cloud, use:
# QDRANT_URL=https://your-qdrant-cloud-url
# QDRANT_API_KEY=your_qdrant_cloud_api_key
```

### 2. Ensure Qdrant is Running

**Local (Docker):**
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
# Or if already running:
docker container list  # Find container ID
docker start <container_id>
```

**Test connection:**
```bash
cd venv_repo/ArcAgent-PRO-Legal
source ../venv/bin/activate
python examples/connect_qdrant.py
```

Expected output:
```
Connecting to Qdrant at http://localhost:6333 (api_key set=False)...
Collections after operation:
 - test_collection
```

### 3. Prepare Data

Sample documents already exist in `data/`:
- `sample_legal_en.txt` — English legal agreement
- `sample_legal_zh.txt` — Chinese legal agreement

To add your own documents, place them in `data/` with supported extensions:
- `.pdf`, `.docx`, `.txt`, `.md`, `.html`, `.rtf`, `.csv`, `.xlsx`, `.pptx`

## Usage

### Basic Indexing (All Defaults)

```bash
cd venv_repo/ArcAgent-PRO-Legal
source ../venv/bin/activate
export GEMINI_API_KEY="your_api_key_here"
python src/index.py --data-dir data
```

### Custom Configuration

```bash
python src/index.py \
  --data-dir data \
  --collection-name legal_docs_v1 \
  --chunk-size 512 \
  --chunk-overlap 20 \
  --qdrant-url http://localhost:6333
```

### Using Qdrant Cloud

```bash
python src/index.py \
  --qdrant-url https://your-qdrant-cloud-url \
  --qdrant-api-key your_cloud_api_key \
  --data-dir data
```

## Expected Output

```
=== Data Ingestion & Indexing Pipeline ===

Step 1: Loading documents...
Loaded 2 document(s)
Step 2: Chunking 2 documents...
✓ Chunked into 3 chunk(s) from 2 documents

Step 3: Setting up Gemini embedding...
✓ Gemini embedding model ready

Step 4: Connecting to Qdrant...
Connecting to Qdrant at http://localhost:6333...
Creating collection 'legal_documents' with vector configuration...
✓ Qdrant client ready (collection: legal_documents)

Step 5: Embedding 3 chunk(s) with Gemini...
✓ Generated 3 embedding(s)

Step 6: Storing embeddings in Qdrant collection 'legal_documents'...
✓ Stored 3 point(s) in Qdrant

Step 7: Verifying index...
✓ Collection verified: 3 point(s) stored
  Vector size: 768
  Distance metric: Cosine

=== Indexing Complete ===

✓ 3 chunks indexed in Qdrant
✓ Collection: legal_documents
✓ Embedding model: Gemini (bilingual)
✓ Vector store: Qdrant (http://localhost:6333)
```

## Script Architecture

### `setup_gemini_embedding(api_key=None)`
- Initializes Google Generative AI with Gemini `embedding-001` model
- Model: Supports 768-dimensional embeddings with **bilingual capabilities**
- Reads `GEMINI_API_KEY` from environment if not provided

### `setup_qdrant_vector_store(collection_name, qdrant_url, qdrant_api_key)`
- Connects to Qdrant (Cloud or local)
- Creates collection with `VectorParams(size=768, distance=Distance.COSINE)`
- Returns `QdrantClient` instance for direct API calls

### `index_documents(documents_path, collection_name, chunk_size, chunk_overlap, ...)`
- **Step 1:** Load documents using `load_documents()` from `ingest.py`
- **Step 2:** Chunk documents using `chunk_documents()` from `ingest.py`
- **Step 3:** Initialize Gemini embedding
- **Step 4:** Connect to Qdrant
- **Step 5:** Embed all chunks using `embedding.get_text_embedding_batch(texts)`
- **Step 6:** Create `PointStruct` objects with metadata
- **Step 7:** Insert points into Qdrant via `client.upsert()`
- **Step 8:** Verify storage and print collection info

## Troubleshooting

### Error: `GEMINI_API_KEY not found`
**Solution:** Set the environment variable:
```bash
export GEMINI_API_KEY="your_api_key_here"
# Or add to .env file
```

### Error: `Connection refused` to Qdrant
**Solution:** Start Qdrant Docker:
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### Error: `No documents found in data/`
**Solution:** Ensure files exist and are in supported formats:
```bash
ls -la data/
```

### Error: Embedding failed
**Solution:** Verify Gemini API key is valid:
```bash
python -c "from llama_index.embeddings.gemini import GeminiEmbedding; GeminiEmbedding(api_key='YOUR_KEY')"
```

## Next Steps

After successful indexing:

1. **Verify vectors in Qdrant:**
   ```bash
   python examples/connect_qdrant.py
   ```

2. **Build RAG retrieval pipeline** (next phase):
   - Create query interface for semantic search
   - Implement context-aware LLM responses
   - Add multi-turn conversation support

3. **Evaluate embeddings:**
   - Test bilingual similarity across English/Chinese
   - Benchmark retrieval accuracy
   - Optimize chunk size and overlap

## Dependencies

- `llama-index[embeddings-gemini]` — Gemini integration (v0.14.8+)
- `qdrant-client` — Qdrant vector store (v1.15.1+)
- `google-generativeai` — Google AI API (v0.8.5+)
- `unstructured` — Document parsing (v0.18.20+)
- `python-dotenv` — Environment variable loading

All dependencies are already installed in the venv.

## File Locations

- **Script:** `src/index.py` (262 lines, complete)
- **Data ingestion:** `src/ingest.py` (reused for loading/chunking)
- **Configuration:** `.env` (local secrets, not committed)
- **Examples:** `examples/connect_qdrant.py` (connection test)
- **Requirements:** `requirements.txt` (pinned versions)

---

**Status:** ✅ Complete and ready for testing

Last updated: 2024 (Indexing module v1.0 - Direct Qdrant API)
