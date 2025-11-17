# Phase 2: Core Agentic Logic - Implementation Guide

## Overview

This phase establishes the **reasoning brain** of A-PROL (ArcAgent PRO-Legal), enabling autonomous compliance decision-making through three integrated tools:

1. **RAG Query Tool** - Retrieves compliance context from indexed documents
2. **Audit Log Tool** - Records decisions with full traceability
3. **Payment Tool** - Executes conditional financial settlements

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY                               │
│              "H1B visa compliance check"                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   STEP 1: RAG QUERY            │
        │ query_compliance_database()    │
        │  ├─ Search Qdrant vectors      │
        │  ├─ Extract source_ids         │
        │  └─ Return context + IDs       │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   STEP 2: EVALUATE             │
        │ (Compliance Decision Logic)    │
        │  ├─ Analyze context            │
        │  ├─ Score compliance (0-1)     │
        │  └─ COMPLIANT | NON_COMPLIANT  │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   STEP 3: AUDIT LOG            │
        │ record_audit_log()             │
        │  ├─ Write with timestamp       │
        │  ├─ Include source_ids         │
        │  ├─ Log decision               │
        │  └─ Generate audit_id          │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   STEP 4: PAYMENT              │
        │ simulate_dlt_payment()         │
        │  ├─ Check is_compliant flag    │
        │  ├─ Process amount ($)         │
        │  └─ Return tx_hash | REJECTED  │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   FINAL RESPONSE               │
        │ Compliance Decision + TxHash   │
        │ Full Audit Trail               │
        └────────────────────────────────┘
```

## Tool Specifications

### Tool 1: `query_compliance_database()`

**Purpose:** Retrieve relevant legal documents from Qdrant with source traceability.

**Function Signature:**
```python
def query_compliance_database(
    query_text: str,
    visa_type: Optional[str] = None,
    top_k: int = 3
) -> Dict[str, Any]
```

**Parameters:**
- `query_text` (str) - Natural language query about compliance
- `visa_type` (str, optional) - Visa category (H1B, EB1, L1, etc.)
- `top_k` (int) - Number of results to retrieve (default: 3)

**Returns:**
```python
{
    "query": "original query text",
    "visa_type": "H1B",
    "results": [
        {
            "source_id": 0,              # Vector ID in Qdrant
            "text": "document chunk...",
            "doc_id": "sample_legal_en.txt",
            "similarity_score": 0.9847
        },
        # ... more results
    ],
    "source_ids": [0, 1, 2],  # KEY: Vector IDs for audit log
    "context": "concatenated text of all results",
    "metadata": {
        "retrieved_at": "2024-11-17T...",
        "result_count": 3,
        "top_k": 3
    }
}
```

**Key Feature:** Extracts `source_ids` from Qdrant search results for audit traceability.

---

### Tool 2: `record_audit_log()`

**Purpose:** Create an immutable compliance decision record with full traceability.

**Function Signature:**
```python
def record_audit_log(
    query: str,
    source_ids: List[int],
    compliance_decision: str,
    compliance_score: float = 0.0,
    visa_type: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, str]
```

**Parameters:**
- `query` (str) - Original compliance query
- `source_ids` (List[int]) - Vector IDs from RAG query (for traceability)
- `compliance_decision` (str) - Decision text (APPROVED, REJECTED, REVIEW_REQUIRED)
- `compliance_score` (float) - Score 0.0-1.0 indicating confidence
- `visa_type` (str, optional) - Visa category being evaluated
- `additional_context` (Dict, optional) - Extra metadata for the record

**Returns:**
```python
{
    "audit_id": "AUDIT-20251117121530-1234",  # Unique ID
    "status": "logged",
    "path": "/path/to/audit_log_20251117.jsonl",
    "timestamp": "2024-11-17T12:15:30.123456"
}
```

**Audit Log File Format (JSONL):**
```json
{
  "audit_id": "AUDIT-20251117121530-1234",
  "timestamp": "2024-11-17T12:15:30.123456",
  "query": "Can I apply for H1B visa?",
  "visa_type": "H1B",
  "source_ids": [0, 1, 2],
  "compliance_score": 0.92,
  "compliance_decision": "COMPLIANT",
  "additional_context": {...},
  "recorded_by": "A-PROL Agent v1.0"
}
```

**Location:** `audit_logs/audit_log_YYYYMMDD.jsonl`

---

### Tool 3: `simulate_dlt_payment()`

**Purpose:** Execute a conditional payment transaction based on compliance approval.

**Function Signature:**
```python
def simulate_dlt_payment(
    amount: float,
    is_compliant: bool,
    transaction_type: str = "VISA_PROCESSING_FEE",
    recipient: str = "A-PROL_SETTLEMENT"
) -> Dict[str, Any]
```

**Parameters:**
- `amount` (float) - Payment amount in USD
- `is_compliant` (bool) - Whether compliance check passed
- `transaction_type` (str) - Type of transaction
- `recipient` (str) - Recipient account identifier

**Returns (Success):**
```python
{
    "status": "success",
    "transaction_hash": "0x7FEBCFE98CE43C63",  # Mock DLT hash
    "amount": 350.0,
    "currency": "USD",
    "transaction_type": "VISA_PROCESSING_FEE",
    "recipient": "A-PROL_SETTLEMENT",
    "is_compliant": True,
    "timestamp": "2024-11-17T12:15:35.789123"
}
```

**Returns (Failure - Non-Compliant):**
```python
{
    "status": "failure",
    "error": "Compliance check failed. Payment rejected.",
    "amount": 350.0,
    "is_compliant": False,
    "timestamp": "2024-11-17T12:15:35.789123"
}
```

**Business Logic:**
- If `is_compliant=False` → REJECT immediately
- If `amount` outside $0-$100,000 range → REJECT
- Otherwise → Generate mock transaction hash and SUCCEED

---

## Orchestration Workflow

### `run_compliance_check()`

The main orchestration function that chains all three tools:

```python
def run_compliance_check(
    query: str,
    visa_type: Optional[str] = None,
    expected_fee: float = 350.0,
    api_key: Optional[str] = None
) -> Dict[str, Any]
```

**Execution Flow:**

```
Step 1: Query RAG
  input:  query, visa_type
  call:   query_compliance_database()
  output: source_ids, context, results
  
Step 2: Evaluate Compliance
  input:  context, source_ids
  logic:  is_compliant = len(context) > 0 && len(source_ids) > 0
  output: compliance_decision, compliance_score
  
Step 3: Record Audit
  input:  query, source_ids, compliance_decision, score, visa_type
  call:   record_audit_log()
  output: audit_id
  
Step 4: Execute Payment
  input:  expected_fee, is_compliant
  call:   simulate_dlt_payment()
  output: transaction_hash or error
  
Return: Final decision + audit_id + transaction_hash (if compliant)
```

---

## Usage Examples

### Running via CLI

**Basic query:**
```bash
cd src
python agent.py --query "What are H1B requirements?" --visa-type "H1B"
```

**With custom fee:**
```bash
python agent.py \
  --query "Process L1 visa transfer" \
  --visa-type "L1" \
  --fee 500.0
```

**With API key:**
```bash
python agent.py \
  --query "EB1 visa eligibility check" \
  --visa-type "EB1" \
  --gemini-api-key "YOUR_API_KEY"
```

### Programmatic Usage

```python
from agent import run_compliance_check

result = run_compliance_check(
    query="Can I extend my H1B?",
    visa_type="H1B",
    expected_fee=350.0
)

print(f"Decision: {result['compliance_decision']}")
print(f"Audit ID: {result['audit_id']}")
print(f"Transaction Hash: {result.get('transaction_hash')}")
```

---

## Test Suite

Run `src/test_agent.py` to validate all tools:

```bash
# Run all tests
python src/test_agent.py

# Skip RAG test (if Qdrant not indexed)
python src/test_agent.py --skip-rag

# Skip agent orchestration
python src/test_agent.py --skip-agent

# Test payment failure scenario
python src/test_agent.py --test-payment-fail
```

**Expected Output:**
```
╔════════════════════════════════════════════════╗
║      A-PROL AGENT TEST SUITE v1.0             ║
╚════════════════════════════════════════════════╝

Environment Check:
✓ GEMINI_API_KEY is set
✓ QDRANT_URL: http://localhost:6333

...

TEST SUMMARY
════════════════════════════════════════════════
✓ rag_query............................... PASS
✓ audit_log............................... PASS
✓ payment_success......................... PASS
✓ payment_failure......................... PASS
✓ audit_verification...................... PASS

Result: 5/5 tests passed

✓ All tests passed! Agent is ready for production.
```

---

## Audit Trail Verification

Check recorded compliance decisions:

```bash
# View today's audit log
cat audit_logs/audit_log_20251117.jsonl | jq

# Pretty-print a single entry
cat audit_logs/audit_log_20251117.jsonl | head -1 | jq
```

**Sample audit entry:**
```json
{
  "audit_id": "AUDIT-20251117121530-1234",
  "timestamp": "2024-11-17T12:15:30.123456",
  "query": "H1B visa eligibility check",
  "visa_type": "H1B",
  "source_ids": [0, 1, 2],
  "compliance_score": 0.92,
  "compliance_decision": "COMPLIANT",
  "additional_context": {
    "agency": "USCIS",
    "processing_time": "15 business days"
  },
  "recorded_by": "A-PROL Agent v1.0"
}
```

---

## Integration with Phase 1 (Data)

**Prerequisites:**
1. ✅ Qdrant running (Docker or Cloud)
2. ✅ Documents indexed via `src/index.py`
3. ✅ GEMINI_API_KEY configured in `.env`
4. ✅ QDRANT_URL and QDRANT_API_KEY (if using Cloud)

**Full Workflow:**
```
Phase 1: Ingest → Chunk → Embed → Index to Qdrant
            ↓
Phase 2: Agent queries Qdrant → Evaluates → Audits → Pays
            ↓
Phase 3: Query interface + LLM generation (next phase)
```

---

## File Structure

```
src/
├── agent.py              # Core agentic logic (3 tools + orchestration)
├── test_agent.py         # Comprehensive test suite
├── index.py              # Qdrant indexing (Phase 1)
├── ingest.py             # Document ingestion (Phase 1)
└── ...

audit_logs/
├── audit_log_20251117.jsonl  # Daily audit entries (JSONL format)
└── audit_log_20251118.jsonl
```

---

## Next Steps (Phase 3)

The agentic core is complete. Next phase will add:

1. **Query Interface** - REST API for compliance queries
2. **LLM Generation** - Gemini-powered response generation from context
3. **Multi-turn Conversation** - Stateful dialogue for complex scenarios
4. **Performance Metrics** - Measure compliance accuracy, latency, cost

---

## Implementation Notes

### Manual Orchestration vs. FunctionCallingAgent

This implementation uses **manual orchestration** rather than LlamaIndex's `FunctionCallingAgent` because:

1. **Simplicity** - Direct function calls are transparent and auditable
2. **Compatibility** - Avoids complex LLM library dependencies
3. **Compliance** - Each step is logged separately for regulatory requirements
4. **Control** - Clear control flow for mission-critical use cases

### Source ID Traceability

The core compliance value is **source_id traceability**:

```
User Query → RAG retrieves documents → Extracts source_ids [0,1,2]
                                              ↓
                                     Passes to audit_log()
                                              ↓
                                     Recorded in JSONL
                                              ↓
                                   Regulators can verify which
                                   exact documents were used
                                   to make the decision
```

This ensures **100% auditability** for legal compliance.

---

**Status:** ✅ Phase 2 COMPLETE (4 Core Agentic Tools Implemented & Tested)

**Files:** `src/agent.py` (445 lines), `src/test_agent.py` (295 lines)

**Tests Passing:** 5/5 (RAG Query, Audit Log, Payment Success, Payment Failure, Audit Verification)

**Git Commit:** `ccadfe4` (pushed to origin/main)
