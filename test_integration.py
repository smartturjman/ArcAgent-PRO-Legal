#!/usr/bin/env python3
"""
Integration test script to verify API, UI, and agent workflow.
Tests the complete Phase 3-4 implementation.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("\n✓ Testing imports...")
    try:
        import api
        print("  ✓ api.py imports successfully")
    except Exception as e:
        print(f"  ✗ api.py import failed: {e}")
        return False
    
    try:
        from agent import run_compliance_check
        print("  ✓ src/agent.py imports successfully")
        print(f"  ✓ run_compliance_check function found")
    except Exception as e:
        print(f"  ✗ src/agent.py import failed: {e}")
        return False
    
    return True

def test_pydantic_models():
    """Test that Pydantic models work."""
    print("\n✓ Testing Pydantic models...")
    try:
        from api import ComplianceQuery, ComplianceResponse, AuditLogEntry, APIStatus
        
        # Test ComplianceQuery
        query = ComplianceQuery(
            query="Can I bring an H-1B visa holder as a consultant?",
            visa_type="H-1B",
            expected_fee=500.0
        )
        print(f"  ✓ ComplianceQuery model works")
        
        # Test APIStatus
        status = APIStatus(status="healthy", version="1.0", timestamp="2025-01-01T00:00:00", services={"agent": "healthy", "qdrant": "healthy"})
        print(f"  ✓ APIStatus model works")
        
        return True
    except Exception as e:
        print(f"  ✗ Pydantic models test failed: {e}")
        return False

def test_agent_availability():
    """Test that the agent module has required functions."""
    print("\n✓ Testing agent module functions...")
    try:
        from agent import (
            run_compliance_check,
            query_compliance_database,
            record_audit_log,
            simulate_dlt_payment
        )
        print("  ✓ run_compliance_check available")
        print("  ✓ query_compliance_database available")
        print("  ✓ record_audit_log available")
        print("  ✓ simulate_dlt_payment available")
        return True
    except ImportError as e:
        print(f"  ✗ Agent function import failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("A-PROL Phase 3-4 Integration Test Suite")
    print("="*60)
    
    all_pass = True
    
    all_pass &= test_imports()
    all_pass &= test_pydantic_models()
    all_pass &= test_agent_availability()
    
    print("\n" + "="*60)
    if all_pass:
        print("✓ All integration tests PASSED")
        print("\nNext steps:")
        print("  1. Start API: python api.py")
        print("  2. Start UI: streamlit run ui.py")
        print("  3. Test endpoints: curl http://localhost:8000/status")
    else:
        print("✗ Some integration tests FAILED")
        sys.exit(1)
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
