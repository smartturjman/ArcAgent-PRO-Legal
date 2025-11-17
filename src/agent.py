#!/usr/bin/env python3
"""
Agentic Logic Module: Gemini-powered reasoning with RAG, auditing, and payment.

This module implements the core A-PROL agent capable of:
1. Querying the Qdrant RAG for compliance context
2. Recording audit logs with source node IDs
3. Executing conditional payment transactions

Architecture:
  Gemini Agent (FunctionAgent)
    ├── Tool 1: query_compliance_database()     [RAG Retrieval]
    ├── Tool 2: record_audit_log()              [Compliance Auditing]
    └── Tool 3: simulate_dlt_payment()          [Financial Settlement]

Workflow:
  User Query → Agent Reasoning → RAG Query (extract source_nodes)
    → Audit Log (with vector IDs) → Payment Decision → DLT Hash
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, Any, Dict, List
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# LlamaIndex imports
from llama_index.core import Settings
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.core.tools import FunctionTool

# Note: FunctionCallingAgent requires llama-index-llms-gemini which has
# complex dependency chains. For this MVP, we'll use manual orchestration
# below and include the agent initialization for future enhancement.

# Qdrant imports
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent))
from index import setup_gemini_embedding, setup_qdrant_vector_store


# ============================================================================
# AUDIT LOG CONFIGURATION
# ============================================================================

AUDIT_LOG_PATH = Path(__file__).parent.parent / "audit_logs"
AUDIT_LOG_PATH.mkdir(exist_ok=True)


# ============================================================================
# TOOL 1: RAG QUERY ENGINE (Compliance Database)
# ============================================================================

def query_compliance_database(
    query_text: str,
    visa_type: Optional[str] = None,
    top_k: int = 3
) -> Dict[str, Any]:
    """Query the Qdrant compliance database for relevant legal context.
    
    This tool retrieves relevant document chunks from the indexed legal
    documents in Qdrant, extracting source node IDs for audit traceability.
    
    Args:
        query_text: Natural language query about compliance requirements
        visa_type: Optional filter for specific visa type (e.g., "H1B", "EB1")
        top_k: Number of top-k similar documents to retrieve
        
    Returns:
        Dict with:
            - "query": Original query text
            - "results": List of retrieved chunks with metadata
            - "source_ids": List of vector IDs from Qdrant (for audit log)
            - "context": Concatenated text of top results
            - "metadata": Document metadata from source nodes
    """
    print(f"\n[RAG QUERY] Processing: {query_text[:100]}...")
    
    qdrant_client = setup_qdrant_vector_store(
        collection_name="legal_documents",
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY")
    )
    
    embedding_model = setup_gemini_embedding(
        api_key=os.getenv("GEMINI_API_KEY")
    )
    
    try:
        # Embed the query
        query_embedding = embedding_model.get_text_embedding(query_text)
        
        # Search Qdrant for similar vectors
        search_results = qdrant_client.search(
            collection_name="legal_documents",
            query_vector=query_embedding,
            limit=top_k,
            with_payload=True
        )
        
        # Extract results and source IDs
        results = []
        source_ids = []
        context_pieces = []
        
        for scored_point in search_results:
            source_id = scored_point.id
            source_ids.append(source_id)
            
            payload = scored_point.payload or {}
            text = payload.get("text", "")
            doc_id = payload.get("doc_id", "unknown")
            similarity_score = scored_point.score
            
            results.append({
                "source_id": source_id,
                "text": text,
                "doc_id": doc_id,
                "similarity_score": round(similarity_score, 4)
            })
            
            context_pieces.append(text)
        
        # Construct response
        response = {
            "query": query_text,
            "visa_type": visa_type,
            "results": results,
            "source_ids": source_ids,
            "context": "\n\n".join(context_pieces),
            "metadata": {
                "retrieved_at": datetime.now().isoformat(),
                "result_count": len(results),
                "top_k": top_k
            }
        }
        
        print(f"[RAG QUERY] Retrieved {len(results)} document(s) with {len(source_ids)} source IDs")
        return response
        
    except Exception as e:
        print(f"[RAG QUERY] Error: {e}")
        return {
            "query": query_text,
            "error": str(e),
            "results": [],
            "source_ids": [],
            "context": ""
        }


# ============================================================================
# TOOL 2: AUDIT LOG RECORDER (Compliance Auditing)
# ============================================================================

def record_audit_log(
    query: str,
    source_ids: List[int],
    compliance_decision: str,
    compliance_score: float = 0.0,
    visa_type: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """Record compliance decision to immutable audit log (mock DLT).
    
    This tool writes a timestamped, verifiable record of every compliance
    decision made by the agent, including the exact vector IDs from Qdrant
    that were used to reach the decision. This ensures auditability.
    
    Args:
        query: Original compliance query
        source_ids: List of Qdrant vector IDs used for decision
        compliance_decision: Decision text (e.g., "APPROVED", "REJECTED", "REVIEW_REQUIRED")
        compliance_score: Numerical compliance score (0.0-1.0)
        visa_type: Type of visa/application being evaluated
        additional_context: Extra context for the audit record
        
    Returns:
        Dict with:
            - "audit_id": Unique audit log entry ID
            - "status": "logged" or error message
            - "path": Path to audit log file
    """
    print(f"\n[AUDIT LOG] Recording decision: {compliance_decision}")
    
    timestamp = datetime.now().isoformat()
    audit_id = f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(query) % 10000:04d}"
    
    audit_entry = {
        "audit_id": audit_id,
        "timestamp": timestamp,
        "query": query,
        "visa_type": visa_type,
        "source_ids": source_ids,  # Vector IDs for traceability
        "compliance_score": compliance_score,
        "compliance_decision": compliance_decision,
        "additional_context": additional_context or {},
        "recorded_by": "A-PROL Agent v1.0"
    }
    
    try:
        # Write to JSON audit log
        audit_log_file = AUDIT_LOG_PATH / f"audit_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(audit_log_file, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
        
        print(f"[AUDIT LOG] Recorded with ID: {audit_id}")
        
        return {
            "audit_id": audit_id,
            "status": "logged",
            "path": str(audit_log_file),
            "timestamp": timestamp
        }
        
    except Exception as e:
        print(f"[AUDIT LOG] Error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================================
# TOOL 3: DLT PAYMENT SIMULATOR (Financial Settlement)
# ============================================================================

def simulate_dlt_payment(
    amount: float,
    is_compliant: bool,
    transaction_type: str = "VISA_PROCESSING_FEE",
    recipient: str = "A-PROL_SETTLEMENT"
) -> Dict[str, Any]:
    """Simulate a DLT (Distributed Ledger Technology) payment transaction.
    
    This tool executes a conditional payment based on compliance approval.
    In production, this would call a real blockchain/settlement system.
    For now, it simulates the behavior with mock transaction hashes.
    
    Args:
        amount: Payment amount in USD
        is_compliant: Boolean indicating if compliance check passed
        transaction_type: Type of transaction
        recipient: Destination account/wallet identifier
        
    Returns:
        Dict with:
            - "status": "success" or "failure"
            - "transaction_hash": Mock DLT hash (if successful)
            - "amount": Amount processed
            - "timestamp": Transaction timestamp
            - "error": Error message (if failed)
    """
    print(f"\n[PAYMENT] Processing ${amount:.2f} (compliant={is_compliant})")
    
    if not is_compliant:
        print("[PAYMENT] ✗ REJECTED - Compliance check failed")
        return {
            "status": "failure",
            "error": "Compliance check failed. Payment rejected.",
            "amount": amount,
            "is_compliant": False,
            "timestamp": datetime.now().isoformat()
        }
    
    if amount < 0 or amount > 100000:  # Mock validation
        print(f"[PAYMENT] ✗ INVALID - Amount out of range: ${amount}")
        return {
            "status": "failure",
            "error": f"Invalid amount: ${amount}. Must be between $0 and $100,000.",
            "amount": amount,
            "timestamp": datetime.now().isoformat()
        }
    
    # Generate mock DLT transaction hash
    import hashlib
    tx_data = f"{recipient}{amount}{datetime.now().isoformat()}"
    transaction_hash = f"0x{hashlib.sha256(tx_data.encode()).hexdigest()[:16].upper()}"
    
    print(f"[PAYMENT] ✓ SUCCESS - TxHash: {transaction_hash}")
    
    return {
        "status": "success",
        "transaction_hash": transaction_hash,
        "amount": amount,
        "currency": "USD",
        "transaction_type": transaction_type,
        "recipient": recipient,
        "is_compliant": is_compliant,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# AGENT INITIALIZATION & ORCHESTRATION
# ============================================================================

def initialize_agent(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Initialize the compliance agent (manual orchestration version).
    
    For the MVP, we use manual orchestration of the three tools rather than
    relying on FunctionCallingAgent (which requires additional dependencies).
    This approach is:
    - Simpler and more transparent
    - Easier to audit and verify
    - Better for compliance use cases
    
    Args:
        api_key: Gemini API key (uses env var if not provided)
        
    Returns:
        Dict with agent configuration
    """
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set. Set it in .env or environment.")
    
    print("\n[AGENT INIT] Initializing compliance agent...")
    print("[AGENT INIT] ✓ Three tools configured:")
    print("[AGENT INIT]   1. query_compliance_database (RAG Retrieval)")
    print("[AGENT INIT]   2. record_audit_log (Compliance Auditing)")
    print("[AGENT INIT]   3. simulate_dlt_payment (Financial Settlement)")

    # --- Wrapper Tool: compliance_query_wrapper ---
    def compliance_query_wrapper(query: str):
        """
        Wrapper around `query_compliance_database` that exposes the final
        answer and the underlying vector IDs for auditability.
        """
        rag_resp = query_compliance_database(query_text=query, top_k=5)
        # Build a simple human-readable answer from retrieved context
        answer_text = rag_resp.get("context", "").strip() or "No context found."
        vector_ids = rag_resp.get("source_ids", [])
        return {"answer": answer_text, "vector_ids": vector_ids}

    # Convert wrapper and existing functions to FunctionTool objects
    try:
        compliance_tool = FunctionTool.from_defaults(
            fn=compliance_query_wrapper,
            name="query_compliance_database",
            description="Tool to query the compliance database and return answer plus source vector IDs."
        )

        audit_logger_tool = FunctionTool.from_defaults(
            fn=record_audit_log,
            name="record_audit_log",
            description="Writes compliance decision and vector IDs to the immutable audit log (JSONL)."
        )

        financial_tool = FunctionTool.from_defaults(
            fn=simulate_dlt_payment,
            name="simulate_dlt_payment",
            description="Simulates a DLT payment and returns a transaction hash."
        )
    except Exception:
        # If FunctionTool or from_defaults is not available, fall back to function refs
        compliance_tool = compliance_query_wrapper
        audit_logger_tool = record_audit_log
        financial_tool = simulate_dlt_payment

    print("[AGENT INIT] ✓ Agent ready for orchestration\n")

    # Strong system prompt to enforce auditable workflow when using an
    # LLM-based FunctionCalling agent. This instructs the model to always
    # call the compliance database tool first, then record the audit, and
    # only then consider payment authorization.
    system_prompt = (
        "You are the ArcAgent PRO-Legal compliance officer. BEFORE producing any\n"
        "final answer or authorizing any payment, you MUST:\n"
        "  1) Use the 'query_compliance_database' tool to retrieve official source\n"
        "     documents and vector IDs.\n"
        "  2) After receiving evidence, use the 'record_audit_log' tool to record\n"
        "     the vector IDs, decision rationale, and any context.\n"
        "  3) Only after the audit log is recorded may you authorize or simulate\n"
        "     any payment using the 'simulate_dlt_payment' tool.\n"
        "Always include the audit_id and list of source vector IDs in your final output."
    )

    return {
        "api_key": api_key,
        "tools": {
            "compliance_tool": compliance_tool,
            "audit_logger_tool": audit_logger_tool,
            "financial_tool": financial_tool,
        },
        "system_prompt": system_prompt,
        "mode": "sequential"  # Tools execute sequentially for audit trail
    }


def prepare_function_calling_agent_config(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Prepare a config object for creating a FunctionCalling / tools-based agent.

    This helper returns a dict containing the `system_prompt` and the tool
    objects (wrapped as FunctionTool where available). It attempts to
    construct a live agent if `OpenAIAgent`/`FunctionCallingAgent` is
    available in the environment, but will otherwise return the config
    for a future agent construction.

    Returns:
        Dict with keys: api_key, system_prompt, tools (dict)
    """
    cfg = initialize_agent(api_key=api_key)

    # Try to instantiate a FunctionCalling agent if llama-index provides it.
    try:
        # Import-resilient attempt - names vary across versions
        try:
            from llama_index.agent import OpenAIAgent  # type: ignore
        except Exception:
            from llama_index.agents.openai import OpenAIAgent  # type: ignore

        # If OpenAIAgent exists, attempt construction using the provided tools.
        # Note: this code is guarded and will not break if the class API
        # differs or dependencies are missing.
        tools = []
        for name, tool_obj in cfg["tools"].items():
            # If it's a FunctionTool instance, append directly; otherwise
            # OpenAIAgent/other wrappers may accept plain callables.
            tools.append(tool_obj)

        agent_instance = None
        try:
            agent_instance = OpenAIAgent.from_tools(
                tools=tools,
                verbose=False,
                system_prompt=cfg.get("system_prompt")
            )
        except Exception:
            agent_instance = None

        return {
            "api_key": api_key,
            "system_prompt": cfg.get("system_prompt"),
            "tools": cfg.get("tools"),
            "agent_instance": agent_instance,
        }

    except Exception:
        # If we cannot build an LLM agent, just return the configuration
        return {
            "api_key": api_key,
            "system_prompt": cfg.get("system_prompt"),
            "tools": cfg.get("tools"),
            "agent_instance": None,
        }


# ============================================================================
# COMPLIANCE QUERY ORCHESTRATION
# ============================================================================

def run_compliance_check(
    query: str,
    visa_type: Optional[str] = None,
    expected_fee: float = 350.0,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a complete compliance check workflow with manual orchestration.
    
    This orchestration follows the defined workflow:
    1. Query RAG for compliance context (extracts source_ids)
    2. Evaluate compliance based on context
    3. Record audit log with source vector IDs
    4. Execute payment if compliant
    
    Args:
        query: Compliance question or visa processing request
        visa_type: Type of visa being processed
        expected_fee: Expected processing fee (USD)
        api_key: Gemini API key
        
    Returns:
        Dict with final workflow result including DLT hash
    """
    print("=" * 70)
    print(f"COMPLIANCE WORKFLOW: {query[:60]}...")
    print("=" * 70)
    
    try:
        # Initialize agent configuration
        agent_config = initialize_agent(api_key=api_key)
        
        # STEP 1: Query RAG for compliance context
        print("\n[STEP 1] Querying compliance database...")
        rag_result = query_compliance_database(
            query_text=query,
            visa_type=visa_type,
            top_k=3
        )
        
        if rag_result.get("error"):
            print(f"[STEP 1] ✗ RAG query failed: {rag_result['error']}")
            return {
                "status": "error",
                "error": f"RAG query failed: {rag_result['error']}",
                "query": query
            }
        
        source_ids = rag_result.get("source_ids", [])
        context = rag_result.get("context", "")
        
        print(f"[STEP 1] ✓ Retrieved {len(source_ids)} source document(s)")
        
        # STEP 2: Evaluate compliance (simulated logic)
        print("\n[STEP 2] Evaluating compliance...")
        
        # Simple heuristic: if we have context, mark as compliant
        # In production, this would call a Gemini-powered evaluator
        is_compliant = len(context) > 0 and len(source_ids) > 0
        compliance_score = min(0.95, 0.5 + (len(source_ids) / 10.0))
        
        compliance_decision = "COMPLIANT" if is_compliant else "NON_COMPLIANT"
        print(f"[STEP 2] ✓ Decision: {compliance_decision} (score: {compliance_score:.2f})")
        
        # STEP 3: Record audit log with source IDs
        print("\n[STEP 3] Recording audit log with traceability...")
        audit_result = record_audit_log(
            query=query,
            source_ids=source_ids,
            compliance_decision=compliance_decision,
            compliance_score=compliance_score,
            visa_type=visa_type,
            additional_context={
                "context_length": len(context),
                "document_count": len(source_ids),
                "evaluation_method": "RAG-based"
            }
        )
        
        if audit_result.get("error"):
            print(f"[STEP 3] ✗ Audit log failed: {audit_result['error']}")
            return {
                "status": "error",
                "error": f"Audit logging failed: {audit_result['error']}",
                "query": query
            }
        
        audit_id = audit_result.get("audit_id", "UNKNOWN")
        print(f"[STEP 3] ✓ Audit ID: {audit_id}")
        
        # STEP 4: Execute payment if compliant
        print("\n[STEP 4] Processing payment (if compliant)...")
        payment_result = simulate_dlt_payment(
            amount=expected_fee,
            is_compliant=is_compliant,
            transaction_type="VISA_PROCESSING_FEE",
            recipient="A-PROL_SETTLEMENT"
        )
        
        if payment_result.get("status") == "failure":
            print(f"[STEP 4] ✗ Payment failed: {payment_result.get('error')}")
            return {
                "status": "compliance_failure",
                "query": query,
                "visa_type": visa_type,
                "compliance_decision": compliance_decision,
                "compliance_score": compliance_score,
                "audit_id": audit_id,
                "payment_status": "REJECTED",
                "error": payment_result.get("error")
            }
        
        transaction_hash = payment_result.get("transaction_hash", "UNKNOWN")
        print(f"[STEP 4] ✓ Payment successful!")
        print(f"[STEP 4] ✓ Transaction Hash: {transaction_hash}")
        
        # Final response
        print("\n" + "=" * 70)
        print("COMPLIANCE WORKFLOW COMPLETE")
        print("=" * 70)
        
        return {
            "status": "completed",
            "query": query,
            "visa_type": visa_type,
            "compliance_decision": compliance_decision,
            "compliance_score": compliance_score,
            "audit_id": audit_id,
            "source_ids": source_ids,
            "context_length": len(context),
            "payment_status": "SUCCESS",
            "transaction_hash": transaction_hash,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"\n✗ Error during compliance check: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "query": query
        }


def main():
    """CLI entry point for agent-based compliance checks."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="A-PROL Agent: Autonomous compliance and payment orchestration"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Compliance query or visa processing request"
    )
    parser.add_argument(
        "--visa-type",
        default=None,
        help="Visa type (e.g., H1B, EB1)"
    )
    parser.add_argument(
        "--fee",
        type=float,
        default=350.0,
        help="Processing fee in USD"
    )
    parser.add_argument(
        "--gemini-api-key",
        default=None,
        help="Gemini API key (uses env var if not set)"
    )
    
    args = parser.parse_args()
    
    result = run_compliance_check(
        query=args.query,
        visa_type=args.visa_type,
        expected_fee=args.fee,
        api_key=args.gemini_api_key
    )
    
    print("\n" + json.dumps(result, indent=2))
    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
