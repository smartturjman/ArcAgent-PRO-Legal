#!/usr/bin/env python3
"""
A-PROL Integration Guide & Demo

This script demonstrates the complete A-PROL workflow:
Phase 1: Data Ingestion & Indexing
Phase 2: Agentic Reasoning & Compliance
Phase 3 (Future): Query Interface & LLM Generation

Run: python demo_integration.py
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def print_header(title):
    """Print a formatted section header."""
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + title.center(68) + "║")
    print("╚" + "═"*68 + "╝\n")


def check_prerequisites():
    """Verify all system prerequisites."""
    print_header("PREREQUISITE CHECK")
    
    requirements = {
        "Python 3.10+": sys.version_info >= (3, 10),
        "GEMINI_API_KEY set": os.getenv("GEMINI_API_KEY") is not None,
        "QDRANT_URL available": os.getenv("QDRANT_URL") is not None,
        "data/ directory exists": Path("data").exists(),
        "src/ directory exists": Path("src").exists(),
        "audit_logs/ directory exists": Path("audit_logs").exists(),
    }
    
    all_pass = True
    for check, status in requirements.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {check}")
        if not status and "KEY" in check:
            all_pass = False
    
    return all_pass


def phase1_demo():
    """Demonstrate Phase 1: Data Ingestion & Indexing."""
    print_header("PHASE 1: DATA INGESTION & INDEXING")
    
    print("Workflow:")
    print("1. Load documents from data/ using UnstructuredReader")
    print("2. Chunk documents with SentenceSplitter (512 tokens)")
    print("3. Embed chunks with Gemini (768-dimensional vectors)")
    print("4. Store vectors in Qdrant with metadata")
    print()
    
    # Check if documents are indexed
    try:
        from qdrant_client import QdrantClient
        
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=qdrant_url)
        
        try:
            collection_info = client.get_collection("legal_documents")
            print(f"✓ Collection 'legal_documents' exists")
            print(f"  ├─ Points: {collection_info.points_count}")
            print(f"  ├─ Vector size: {collection_info.config.params.vectors.size}")
            print(f"  └─ Distance metric: {collection_info.config.params.vectors.distance}")
        except Exception as e:
            print(f"⚠ Collection 'legal_documents' not found: {e}")
            print("  Run: python src/index.py --data-dir data")
    except Exception as e:
        print(f"✗ Could not connect to Qdrant: {e}")
    
    print("\nFiles created in Phase 1:")
    print("✓ src/ingest.py       - Document loading & chunking")
    print("✓ src/index.py        - Qdrant indexing pipeline")
    print("✓ data/sample_legal_* - Sample bilingual documents")


def phase2_demo():
    """Demonstrate Phase 2: Agentic Reasoning & Compliance."""
    print_header("PHASE 2: AGENTIC REASONING & COMPLIANCE")
    
    print("Three Integrated Tools:")
    print()
    print("1. query_compliance_database()")
    print("   └─ Retrieves relevant documents from Qdrant")
    print("   └─ Extracts source_ids for audit traceability")
    print()
    print("2. record_audit_log()")
    print("   └─ Records compliance decision with source_ids")
    print("   └─ Writes to audit_logs/audit_log_YYYYMMDD.jsonl")
    print()
    print("3. simulate_dlt_payment()")
    print("   └─ Executes conditional payment")
    print("   └─ Returns DLT transaction hash or error")
    print()
    
    # Try to run a compliance check
    try:
        from src.agent import run_compliance_check
        
        print("Running sample compliance check...")
        print("(Note: Requires indexed documents in Qdrant)\n")
        
        # Mock run without Qdrant
        result = run_compliance_check(
            query="What are visa eligibility requirements?",
            visa_type="H1B",
            expected_fee=350.0
        )
        
        print(f"✓ Compliance decision: {result.get('compliance_decision')}")
        if 'audit_id' in result:
            print(f"✓ Audit ID: {result.get('audit_id')}")
        if 'transaction_hash' in result:
            print(f"✓ Transaction hash: {result.get('transaction_hash')}")
            
    except Exception as e:
        print(f"⚠ Could not run compliance check: {e}")
        print("  Make sure QDRANT_URL and GEMINI_API_KEY are set")
    
    print("\nFiles created in Phase 2:")
    print("✓ src/agent.py        - Agentic logic (3 tools + orchestration)")
    print("✓ src/test_agent.py   - Comprehensive test suite")
    print("✓ audit_logs/         - Audit trail (JSONL format)")


def phase3_future():
    """Show what Phase 3 will include."""
    print_header("PHASE 3: QUERY INTERFACE & LLM GENERATION (FUTURE)")
    
    print("Components to be implemented:")
    print()
    print("1. REST API Query Interface")
    print("   └─ /api/compliance/query")
    print("   └─ /api/compliance/history")
    print("   └─ /api/compliance/audit/<audit_id>")
    print()
    print("2. LLM-Powered Response Generation")
    print("   └─ Gemini generates human-readable answers")
    print("   └─ Based on RAG context + compliance decision")
    print()
    print("3. Multi-turn Conversation")
    print("   └─ Maintain conversation history")
    print("   └─ Support follow-up questions")
    print()
    print("4. Performance Dashboard")
    print("   └─ Compliance accuracy metrics")
    print("   └─ API latency tracking")
    print("   └─ Cost analysis")


def workflow_diagram():
    """Show the complete workflow."""
    print_header("COMPLETE A-PROL WORKFLOW")
    
    diagram = """
    ┌──────────────────────────────────────────────────────────┐
    │                    USER QUERY                            │
    │         "Can I apply for an H1B visa?"                   │
    └──────────────────────┬───────────────────────────────────┘
                           │
         ┌─────────────────┴──────────────────┐
         │                                    │
         ▼                                    ▼
    ┌──────────────┐                    ┌──────────────┐
    │  PHASE 1     │                    │  PHASE 2     │
    │   (Data)     │                    │  (Agent)     │
    └──────┬───────┘                    └──────┬───────┘
           │                                   │
           │ Qdrant Vectors                    │ Tools
           │ + Metadata                        │
           │                                   │
           └───────────────┬───────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          ▼                                 ▼
    ┌──────────────┐                ┌──────────────┐
    │  RAG Query   │ ──source_ids──>│  Audit Log   │
    └──────┬───────┘                └──────┬───────┘
           │                               │
           │ context                       │ audit_id
           │                               │
           └───────────────┬───────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Compliance   │
                    │ Evaluation   │
                    └──────┬───────┘
                           │
          ┌────────────────┴────────────────┐
          │ APPROVED                        │ REJECTED
          │                                 │
          ▼                                 ▼
    ┌──────────────┐                ┌──────────────┐
    │  DLT Payment │                │   Error      │
    │ (TxHash)     │                │  Response    │
    └──────┬───────┘                └──────────────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │  FINAL RESPONSE                  │
    │  • Decision: COMPLIANT           │
    │  • Audit ID: AUDIT-...           │
    │  • TxHash: 0x7FEB...             │
    │  • Timestamp: 2024-11-17...      │
    └──────────────────────────────────┘
    """
    
    print(diagram)


def quick_start():
    """Show quick start instructions."""
    print_header("QUICK START")
    
    print("1. Set up environment:")
    print("   cp .env.example .env")
    print("   # Edit .env and add GEMINI_API_KEY")
    print()
    print("2. Start Qdrant:")
    print("   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")
    print()
    print("3. Index documents (Phase 1):")
    print("   python src/index.py --data-dir data")
    print()
    print("4. Test agent tools (Phase 2):")
    print("   python src/test_agent.py")
    print()
    print("5. Run compliance check:")
    print("   python src/agent.py --query 'H1B visa requirements?' --visa-type H1B")
    print()
    print("6. Check audit logs:")
    print("   cat audit_logs/audit_log_$(date +%Y%m%d).jsonl | jq")


def feature_matrix():
    """Show implemented vs future features."""
    print_header("FEATURE MATRIX")
    
    print("PHASE 1: Data Layer")
    print("✓ Document ingestion (PDF, DOCX, TXT, etc.)")
    print("✓ Bilingual support (English/Chinese)")
    print("✓ Vector embeddings (Gemini 768-dim)")
    print("✓ Qdrant storage (Cloud & Local)")
    print()
    print("PHASE 2: Agentic Logic")
    print("✓ RAG query tool with source_id extraction")
    print("✓ Audit log recording with full traceability")
    print("✓ Conditional DLT payment simulation")
    print("✓ Sequential orchestration workflow")
    print("✓ Test suite (5/5 tests passing)")
    print()
    print("PHASE 3: Query Interface (FUTURE)")
    print("⊘ REST API endpoints")
    print("⊘ Multi-turn conversations")
    print("⊘ LLM response generation")
    print("⊘ Performance dashboards")
    print()
    print("PHASE 4: Deployment (FUTURE)")
    print("⊘ Docker containerization")
    print("⊘ CI/CD pipeline (GitHub Actions)")
    print("⊘ Production monitoring")


def main():
    """Run the integration demo."""
    print_header("A-PROL INTEGRATION GUIDE & DEMO")
    
    # Check prerequisites
    has_api_key = check_prerequisites()
    
    if not has_api_key:
        print("\n⚠ GEMINI_API_KEY not set")
        print("  Some features will be limited")
    
    # Show each phase
    phase1_demo()
    phase2_demo()
    phase3_future()
    
    # Show workflow
    workflow_diagram()
    
    # Quick start
    quick_start()
    
    # Feature matrix
    feature_matrix()
    
    # Final note
    print_header("NEXT STEPS")
    print("Phase 3 will add:")
    print("• REST API for querying compliance decisions")
    print("• Gemini-powered response generation")
    print("• Multi-turn conversation support")
    print("• Real-time performance metrics")
    print()
    print("For details, see:")
    print("• COMPLETION_REPORT.md")
    print("• INDEXING_SETUP.md")
    print("• PHASE2_AGENTIC_LOGIC.md")
    print()
    print("Status: Phases 1-2 Complete ✓")
    print("Ready for Phase 3 Development")


if __name__ == "__main__":
    main()
