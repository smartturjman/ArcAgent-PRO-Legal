#!/usr/bin/env python3
"""
A-PROL REST API Backend - Phase 3

FastAPI application providing three core endpoints:
1. /chat - Submit compliance queries and receive decisions
2. /status - Check API and agent status
3. /audit/{audit_id} - Retrieve compliance audit logs

This API bridges the Python agent backend with frontend applications.

Usage:
  uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import hashlib

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent import run_compliance_check, query_compliance_database, record_audit_log, simulate_dlt_payment


# ============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================================

class ComplianceQuery(BaseModel):
    """Request model for compliance queries."""
    query: str
    visa_type: Optional[str] = None
    expected_fee: float = 350.0


class ComplianceResponse(BaseModel):
    """Response model for compliance queries."""
    status: str
    query: str
    visa_type: Optional[str] = None
    compliance_decision: str
    compliance_score: float
    audit_id: str
    source_ids: List[int]
    context_length: int
    transaction_hash: Optional[str] = None
    payment_status: str
    timestamp: str
    error: Optional[str] = None


class AuditLogEntry(BaseModel):
    """Audit log entry model."""
    audit_id: str
    timestamp: str
    query: str
    visa_type: Optional[str]
    source_ids: List[int]
    compliance_score: float
    compliance_decision: str
    additional_context: Dict[str, Any]
    recorded_by: str


class APIStatus(BaseModel):
    """API status model."""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]


class EvidenceUploadResponse(BaseModel):
    """Response payload for legal forensics uploads."""
    status: str
    filename: str
    size_bytes: int
    evidence_id: str
    evidence_hash: str
    stored_path: str
    tokenized_at: str
    message: Optional[str] = None


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="A-PROL REST API",
    description="Autonomous legal compliance agent with auditable workflow + ALDP Legal Forensics",
    version="1.1.0"
)
FORENSICS_ENDPOINT = "/forensics/evidence"
MAX_EVIDENCE_BYTES = 200 * 1024 * 1024  # 200 MB upload limit
# ============================================================================
# NEW ENDPOINT: /audit/corporate - Corporate Audit
# ============================================================================

class CorporateAuditResponse(BaseModel):
    status: str
    audit_id: str
    message: str

@app.post("/audit/corporate", response_model=CorporateAuditResponse)
async def audit_corporate(request: Request):
    """
    Corporate Audit: Accepts document summary and audit type, triggers ALDP compliance logic.
    """
    raw_body = (await request.body()).decode("utf-8").strip()
    if not raw_body:
        raise HTTPException(
            status_code=400,
            detail="Empty payload received. Please provide a JSON body for the audit."
        )
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON format provided in the audit payload."
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="JSON payload must be an object with key/value pairs."
        )

    audit_type = payload.get("audit_type", "GENERAL")
    document_summary = payload.get("document_summary") or payload.get("summary") or json.dumps(payload)

    # Simulate audit logic and generate audit_id
    import uuid
    audit_id = f"CORPAUD-{uuid.uuid4().hex[:12]}"
    # Here you would call ALDP compliance logic
    # For demo, just log and return
    print(f"[CORP AUDIT] {audit_type}: {document_summary}")
    return CorporateAuditResponse(
        status="completed",
        audit_id=audit_id,
        message=f"Corporate audit '{audit_type}' completed."
    )

# ============================================================================
# NEW ENDPOINT: /forensics/evidence - Legal Forensics File Upload
# ============================================================================

@app.post(
    FORENSICS_ENDPOINT,
    response_model=EvidenceUploadResponse,
    summary="Upload legal forensics evidence"
)
async def upload_evidence(file: UploadFile = File(...)):
    """
    Legal Forensics: Accept a file upload, persist it locally, and compute
    a SHA256 hash that serves as the tokenized evidence identifier.
    """
    evidence_dir = Path(__file__).parent / "evidence_uploads"
    evidence_dir.mkdir(exist_ok=True)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > MAX_EVIDENCE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_EVIDENCE_BYTES // (1024 * 1024)}MB limit."
        )

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_name = f"{timestamp}_{file.filename}"
    file_path = evidence_dir / safe_name
    with open(file_path, "wb") as out_file:
        out_file.write(content)

    evidence_hash = hashlib.sha256(content).hexdigest()
    evidence_id = f"TOKEN-{evidence_hash[:16].upper()}"

    print(f"[FORENSICS] Uploaded {file.filename}, path={file_path}, hash={evidence_hash}")

    return EvidenceUploadResponse(
        status="success",
        filename=file.filename,
        size_bytes=len(content),
        evidence_id=evidence_id,
        evidence_hash=evidence_hash,
        stored_path=str(file_path),
        tokenized_at=datetime.utcnow().isoformat(),
        message="Evidence stored and tokenized for custody tracking."
    )

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ENDPOINT 1: /chat - Compliance Query Submission
# ============================================================================

@app.post("/chat", response_model=ComplianceResponse)
async def chat(query_request: ComplianceQuery):
    """
    Submit a compliance query and receive a decision with audit trail.
    
    This endpoint executes the complete Phase 2 workflow:
    1. Query RAG for compliance context
    2. Evaluate compliance
    3. Record audit log with source IDs
    4. Execute payment if compliant
    
    Args:
        query_request: ComplianceQuery with query text, visa_type, and fee
        
    Returns:
        ComplianceResponse with decision, audit_id, and transaction_hash
        
    Example:
        POST /chat
        {
            "query": "Can I apply for an H1B visa?",
            "visa_type": "H1B",
            "expected_fee": 350.0
        }
    """
    print(f"\n[API] Received query: {query_request.query[:60]}...")
    
    try:
        # Execute the complete compliance check workflow
        result = run_compliance_check(
            query=query_request.query,
            visa_type=query_request.visa_type,
            expected_fee=query_request.expected_fee
        )
        
        # Validate result contains expected fields
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
        
        # Build response
        response = ComplianceResponse(
            status=result.get("status", "completed"),
            query=query_request.query,
            visa_type=query_request.visa_type,
            compliance_decision=result.get("compliance_decision", "UNKNOWN"),
            compliance_score=result.get("compliance_score", 0.0),
            audit_id=result.get("audit_id", ""),
            source_ids=result.get("source_ids", []),
            context_length=result.get("context_length", 0),
            transaction_hash=result.get("transaction_hash"),
            payment_status=result.get("payment_status", "PENDING"),
            timestamp=result.get("timestamp", datetime.now().isoformat()),
            error=result.get("error")
        )
        
        print(f"[API] ✓ Query processed - Decision: {response.compliance_decision}")
        return response
        
    except Exception as e:
        print(f"[API] ✗ Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 2: /status - API Status Check
# ============================================================================

@app.get("/status", response_model=APIStatus)
async def status():
    """
    Check the status of the A-PROL API and its services.
    
    Returns:
        APIStatus with overall status and individual service states
        
    Example:
        GET /status
        
    Response:
        {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": "2024-11-17T12:00:00",
            "services": {
                "qdrant": "connected",
                "gemini": "configured",
                "agent": "ready"
            }
        }
    """
    print("\n[API] Health check requested")
    
    # Check services
    services = {
        "qdrant": "available",
        "gemini": "available" if os.getenv("GEMINI_API_KEY") else "not_configured",
        "agent": "ready"
    }
    
    overall_status = "healthy" if all(v != "not_configured" for v in services.values()) else "degraded"
    
    return APIStatus(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        services=services
    )


# ============================================================================
# ENDPOINT 3: /audit/{audit_id} - Audit Log Retrieval
# ============================================================================

@app.get("/audit/{audit_id}", response_model=AuditLogEntry)
async def get_audit_log(audit_id: str):
    """
    Retrieve a compliance audit log entry by ID.
    
    This endpoint retrieves the immutable audit record created during
    the compliance check, including source vector IDs, compliance score,
    and decision details.
    
    Args:
        audit_id: Unique audit log identifier (e.g., "AUDIT-20251117121530-1234")
        
    Returns:
        AuditLogEntry with full audit trail
        
    Example:
        GET /audit/AUDIT-20251117121530-1234
        
    Response:
        {
            "audit_id": "AUDIT-20251117121530-1234",
            "timestamp": "2024-11-17T12:15:30.123456",
            "query": "H1B visa eligibility?",
            "visa_type": "H1B",
            "source_ids": [0, 1, 2],
            "compliance_score": 0.92,
            "compliance_decision": "COMPLIANT",
            "additional_context": {...},
            "recorded_by": "A-PROL Agent v1.0"
        }
    """
    print(f"\n[API] Retrieving audit log: {audit_id}")
    
    try:
        # Read audit logs
        audit_logs_dir = Path(__file__).parent / "audit_logs"
        
        if not audit_logs_dir.exists():
            raise HTTPException(status_code=404, detail="Audit logs directory not found")
        
        # Search for audit entry in all log files
        for log_file in audit_logs_dir.glob("*.jsonl"):
            with open(log_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if entry.get("audit_id") == audit_id:
                        print(f"[API] ✓ Found audit entry: {audit_id}")
                        return AuditLogEntry(**entry)
        
        # Not found
        raise HTTPException(
            status_code=404,
            detail=f"Audit log entry '{audit_id}' not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] ✗ Error retrieving audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADDITIONAL ENDPOINT: /audit/list - List Recent Audits
# ============================================================================

@app.get("/audit/list", response_model=List[Dict[str, Any]])
async def list_audits(limit: int = Query(10, ge=1, le=100)):
    """
    List recent compliance audit entries.
    
    Args:
        limit: Maximum number of entries to return (default: 10, max: 100)
        
    Returns:
        List of recent audit entries
        
    Example:
        GET /audit/list?limit=5
    """
    print(f"\n[API] Listing recent audits (limit: {limit})")
    
    try:
        audit_logs_dir = Path(__file__).parent / "audit_logs"
        
        if not audit_logs_dir.exists():
            return []
        
        entries = []
        
        # Read entries from all log files (newest first)
        for log_file in sorted(audit_logs_dir.glob("*.jsonl"), reverse=True):
            with open(log_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    entries.append(entry)
                    if len(entries) >= limit:
                        return entries[:limit]
        
        print(f"[API] ✓ Found {len(entries)} audit entries")
        return entries
        
    except Exception as e:
        print(f"[API] ✗ Error listing audits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint with documentation."""
    return {
        "name": "A-PROL REST API",
        "version": "1.0.0",
        "description": "Autonomous legal compliance agent with auditable workflow",
        "endpoints": {
            "POST /chat": "Submit compliance query",
            "POST /audit/corporate": "Submit corporate audit payloads",
            f"POST {FORENSICS_ENDPOINT}": "Upload legal forensics evidence",
            "GET /status": "Check API status",
            "GET /audit/{audit_id}": "Retrieve audit log",
            "GET /audit/list": "List recent audits",
            "GET /docs": "Interactive API documentation (Swagger UI)"
        },
        "docs": "/docs"
    }


# ============================================================================
# SERVER STARTUP
# ============================================================================

def main():
    """Run the API server."""
    print("\n" + "="*70)
    print("A-PROL REST API Server")
    print("="*70)
    print("\nStarting FastAPI server...")
    print("Endpoints:")
    print("  POST /chat              - Submit compliance queries")
    print("  GET /status             - Check API status")
    print("  GET /audit/{audit_id}   - Retrieve audit logs")
    print("  GET /audit/list         - List recent audits")
    print("  GET /docs               - Interactive documentation")
    print("\nServer running at: http://localhost:8000")
    print("Swagger UI at: http://localhost:8000/docs")
    print("="*70 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
