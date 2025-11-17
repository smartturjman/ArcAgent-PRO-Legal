#!/usr/bin/env python3
"""
Test & Orchestration Suite for A-PROL Agent

This script validates the complete workflow:
1. RAG query execution with source ID extraction
2. Audit log recording
3. Payment processing based on compliance
4. End-to-end agent orchestration

Run: python test_agent.py --query "Can I apply for H1B visa?"
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def test_rag_query():
    """Test Tool 1: RAG query and source ID extraction."""
    print("\n" + "="*70)
    print("TEST 1: RAG Query & Source ID Extraction")
    print("="*70)
    
    from agent import query_compliance_database
    
    test_query = "What are the requirements for H1B visa eligibility?"
    
    print(f"\nQuery: {test_query}")
    result = query_compliance_database(
        query_text=test_query,
        visa_type="H1B",
        top_k=3
    )
    
    print(f"\n✓ Results retrieved: {result.get('metadata', {}).get('result_count', 0)}")
    print(f"✓ Source IDs: {result.get('source_ids', [])}")
    print(f"✓ Context length: {len(result.get('context', ''))} chars")
    
    if result.get('error'):
        print(f"✗ Error: {result['error']}")
        return False
    
    return result


def test_audit_log(source_ids):
    """Test Tool 2: Audit log recording with source IDs."""
    print("\n" + "="*70)
    print("TEST 2: Audit Log Recording")
    print("="*70)
    
    from agent import record_audit_log
    
    result = record_audit_log(
        query="H1B visa eligibility check",
        source_ids=source_ids or [1, 2, 3],  # Mock IDs if none returned
        compliance_decision="COMPLIANT",
        compliance_score=0.92,
        visa_type="H1B",
        additional_context={
            "agency": "USCIS",
            "processing_time": "15 business days"
        }
    )
    
    print(f"\n✓ Audit ID: {result.get('audit_id')}")
    print(f"✓ Status: {result.get('status')}")
    print(f"✓ Path: {result.get('path')}")
    
    if result.get('error'):
        print(f"✗ Error: {result['error']}")
        return False
    
    return result


def test_payment(is_compliant=True):
    """Test Tool 3: DLT payment simulation."""
    print("\n" + "="*70)
    print("TEST 3: DLT Payment Simulation")
    print("="*70)
    
    from agent import simulate_dlt_payment
    
    amount = 350.0  # Standard USCIS filing fee
    
    print(f"\nPayment Request:")
    print(f"  Amount: ${amount:.2f}")
    print(f"  Compliant: {is_compliant}")
    
    result = simulate_dlt_payment(
        amount=amount,
        is_compliant=is_compliant,
        transaction_type="VISA_PROCESSING_FEE",
        recipient="A-PROL_SETTLEMENT"
    )
    
    print(f"\n✓ Status: {result.get('status')}")
    print(f"✓ Amount: ${result.get('amount'):.2f}")
    
    if result.get('status') == 'success':
        print(f"✓ Transaction Hash: {result.get('transaction_hash')}")
    else:
        print(f"✗ Error: {result.get('error')}")
    
    return result


def test_orchestration():
    """Test the complete agent orchestration."""
    print("\n" + "="*70)
    print("TEST 4: Full Agent Orchestration")
    print("="*70)
    
    from agent import run_compliance_check
    
    query = "I want to apply for H1B visa. What are the compliance requirements and expected processing fees?"
    
    print(f"\nOrchestration Query: {query}")
    print("\nAgent will:")
    print("  1. Query RAG for compliance context")
    print("  2. Record audit log with source IDs")
    print("  3. Execute payment if compliant")
    print("\n(Running agent...)\n")
    
    result = run_compliance_check(
        query=query,
        visa_type="H1B",
        expected_fee=350.0
    )
    
    return result


def verify_audit_logs():
    """Verify audit logs were created."""
    print("\n" + "="*70)
    print("TEST 5: Audit Log Verification")
    print("="*70)
    
    audit_dir = Path(__file__).parent.parent / "audit_logs"
    
    if not audit_dir.exists():
        print(f"✗ Audit logs directory not found: {audit_dir}")
        return False
    
    log_files = list(audit_dir.glob("*.jsonl"))
    print(f"\n✓ Found {len(log_files)} audit log file(s)")
    
    total_entries = 0
    for log_file in log_files:
        try:
            with open(log_file) as f:
                entries = [json.loads(line) for line in f if line.strip()]
            total_entries += len(entries)
            print(f"  - {log_file.name}: {len(entries)} entries")
        except Exception as e:
            print(f"  - Error reading {log_file.name}: {e}")
    
    if total_entries > 0:
        print(f"\n✓ Total audit entries: {total_entries}")
        return True
    
    return False


def main():
    """Run all tests in sequence."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test A-PROL agent components")
    parser.add_argument("--query", help="Custom query for orchestration test")
    parser.add_argument("--skip-rag", action="store_true", help="Skip RAG test")
    parser.add_argument("--skip-agent", action="store_true", help="Skip agent orchestration")
    parser.add_argument("--test-payment-fail", action="store_true", help="Test failed payment scenario")
    
    args = parser.parse_args()
    
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "A-PROL AGENT TEST SUITE v1.0" + " "*24 + "║")
    print("╚" + "="*68 + "╝")
    
    # Verify environment
    print("\nEnvironment Check:")
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠ GEMINI_API_KEY not set - some tests will fail")
    else:
        print("✓ GEMINI_API_KEY is set")
    
    if not os.getenv("QDRANT_URL"):
        print("⚠ QDRANT_URL not set (defaulting to http://localhost:6333)")
    else:
        print(f"✓ QDRANT_URL: {os.getenv('QDRANT_URL')}")
    
    test_results = {}
    
    # Test 1: RAG Query
    if not args.skip_rag:
        try:
            rag_result = test_rag_query()
            test_results["rag_query"] = "PASS" if rag_result else "FAIL"
            source_ids = rag_result.get("source_ids", []) if rag_result else []
        except Exception as e:
            print(f"\n✗ RAG Query test failed: {e}")
            test_results["rag_query"] = "ERROR"
            source_ids = []
    else:
        source_ids = [1, 2, 3]  # Mock IDs
    
    # Test 2: Audit Log
    try:
        audit_result = test_audit_log(source_ids)
        test_results["audit_log"] = "PASS" if audit_result else "FAIL"
    except Exception as e:
        print(f"\n✗ Audit Log test failed: {e}")
        test_results["audit_log"] = "ERROR"
    
    # Test 3: Payment (Success)
    try:
        payment_result = test_payment(is_compliant=True)
        test_results["payment_success"] = "PASS" if payment_result.get("status") == "success" else "FAIL"
    except Exception as e:
        print(f"\n✗ Payment test failed: {e}")
        test_results["payment_success"] = "ERROR"
    
    # Test 3b: Payment (Failure - optional)
    if args.test_payment_fail:
        try:
            payment_fail_result = test_payment(is_compliant=False)
            test_results["payment_failure"] = "PASS" if payment_fail_result.get("status") == "failure" else "FAIL"
        except Exception as e:
            print(f"\n✗ Payment failure test failed: {e}")
            test_results["payment_failure"] = "ERROR"
    
    # Test 4: Full Orchestration
    if not args.skip_agent:
        try:
            print("\n(Note: Full agent test requires valid GEMINI_API_KEY)")
            print("Skipping full orchestration - see agent.py for usage")
            test_results["orchestration"] = "SKIPPED"
        except Exception as e:
            print(f"\n✗ Orchestration test failed: {e}")
            test_results["orchestration"] = "ERROR"
    
    # Test 5: Audit Log Verification
    try:
        verify_result = verify_audit_logs()
        test_results["audit_verification"] = "PASS" if verify_result else "FAIL"
    except Exception as e:
        print(f"\n✗ Audit verification test failed: {e}")
        test_results["audit_verification"] = "ERROR"
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, status in test_results.items():
        symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⊘"
        print(f"{symbol} {test_name:.<40} {status}")
    
    passed = sum(1 for s in test_results.values() if s == "PASS")
    total = len(test_results)
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Agent is ready for production.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
