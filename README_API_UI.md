# A-PROL REST API & UI - Phase 3-4

Complete web application stack for the AI-Powered Regulatory & Operational Legal System.

## Quick Start

### Option 1: Run Both (Easiest)
```bash
cd /Users/jonieculaste/Projects/ArcAgent\ PRO-Legal/venv_repo/ArcAgent-PRO-Legal
chmod +x quickstart.sh
./quickstart.sh
```

### Option 2: Manual Start

**Terminal 1 - Start API:**
```bash
cd /Users/jonieculaste/Projects/ArcAgent\ PRO-Legal/venv_repo/ArcAgent-PRO-Legal
source ../venv/bin/activate
python api.py
```

**Terminal 2 - Start UI:**
```bash
cd /Users/jonieculaste/Projects/ArcAgent\ PRO-Legal/venv_repo/ArcAgent-PRO-Legal
source ../venv/bin/activate
streamlit run ui.py
```

### Access Points
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **UI:** http://localhost:8501

## Components

### `api.py` - FastAPI REST Server (370+ lines)

**Endpoints:**
- `POST /chat` - Submit compliance query
- `GET /status` - Service health check
- `GET /audit/{audit_id}` - Retrieve audit entry
- `GET /audit/list?limit=10` - List recent audits

**Features:**
- Async/await for non-blocking I/O
- Pydantic validation for all requests
- CORS middleware for cross-origin support
- OpenAPI/Swagger documentation
- Comprehensive error handling
- Integration with Phase 2 agent

**Environment Variables:**
```bash
GEMINI_API_KEY=sk-...           # Google Gemini API key
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                 # Optional, if using Qdrant Cloud
```

### `ui.py` - Streamlit Interface (400+ lines)

**Features:**
- Multi-turn conversation with context
- Real-time API status indicator
- Visa type selector (10 categories)
- Processing fee customization
- **Transparency panel** showing:
  - Compliance decision with confidence
  - Source documents used
  - Payment transaction hash
  - Audit ID and timestamp
- Audit history tracking
- Color-coded decisions
- Responsive design

**Environment Variables:**
```bash
API_URL=http://localhost:8000   # FastAPI server URL
```

## Architecture

```
User (Browser)
      ↓
Streamlit UI (ui.py)
      ↓ HTTP requests
FastAPI (api.py)
      ↓
Phase 2 Agent (src/agent.py)
      ├→ RAG Query (LlamaIndex)
      ├→ Compliance Check
      ├→ Audit Logging (JSONL)
      └→ Payment Simulation
      ↓
Vector DB (Qdrant)
Gemini Embeddings API
Compliance Documents
```

## API Examples

### Submit Compliance Query
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Can I work remotely while on H-1B?",
    "visa_type": "H-1B",
    "expected_fee": 500
  }' | jq
```

### Check Status
```bash
curl http://localhost:8000/status | jq
```

### View Audit Log
```bash
curl http://localhost:8000/audit/list?limit=5 | jq
```

## Testing

Run integration tests:
```bash
python test_integration.py
```

Expected output:
```
✓ All integration tests PASSED
```

## Project Structure

```
├── api.py                    (REST API backend)
├── ui.py                     (Streamlit frontend)
├── test_integration.py       (Integration tests)
├── quickstart.sh             (Quick start script)
├── src/
│   ├── agent.py              (Phase 2 agentic logic)
│   ├── ingest.py             (Phase 1 data loading)
│   ├── index.py              (Phase 1 vector indexing)
│   └── test_agent.py         (Phase 2 tests)
├── audit_logs/               (Compliance audit trail)
├── data/                     (Sample documents)
└── requirements.txt          (Python dependencies)
```

## Deployment

### Deploy to Vercel (FastAPI)
1. Create `vercel.json`:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/api/handler" }]
}
```

2. Create `api/handler.py` (serverless wrapper)
3. Deploy: `vercel deploy`

### Deploy to Cloud Run (Streamlit)
1. Create `Dockerfile`:
```dockerfile
FROM python:3.14
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "ui.py", "--server.port=8501"]
```

2. Deploy:
```bash
gcloud run deploy a-prol-ui \
  --source . \
  --platform managed \
  --region us-central1
```

## Troubleshooting

### API Port Already in Use
```bash
lsof -i :8000
kill -9 <PID>
```

### Streamlit Can't Connect to API
- Verify API is running: `curl http://localhost:8000/status`
- Check `API_URL` in ui.py
- Look for CORS errors in browser console

### Missing Dependencies
```bash
pip install -r requirements.txt
pip install fastapi uvicorn pydantic streamlit requests
```

### Qdrant Connection Error
```bash
# Verify Qdrant is running
docker ps | grep qdrant

# If not running, start it:
docker run -p 6333:6333 qdrant/qdrant
```

## Documentation Files

- **PHASE34_COMPLETION.md** - Detailed completion report
- **PHASE2_COMPLETION.md** - Phase 2 agent documentation
- **INDEXING_SETUP.md** - Vector database setup
- **api.py** - API source code with docstrings
- **ui.py** - UI source code with docstrings

## Support

For issues:
1. Check logs in terminal
2. Run `python test_integration.py`
3. Verify all services are running
4. Check environment variables are set
5. Review troubleshooting section above

## License

A-PROL (AI-Powered Regulatory & Operational Legal System)

---

**Last Updated:** November 17, 2025  
**Version:** 1.0  
**Status:** Production Ready ✓
