#!/usr/bin/env python3
"""
Run two paths:
  - seeded: seed Qdrant and embedding -> expect COMPLIANT and transaction hash
  - unseeded: no seeding -> expect NON_COMPLIANT and payment rejected

Usage: python src/test_seeded_paths.py
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

def run_seeded_path():
    print("\n=== TEST: Seeded (expect COMPLIANT) ===")
    os.environ.setdefault("GEMINI_API_KEY", "DUMMY_API_KEY")

    import agent
    from agent import run_compliance_check
    import index as idx
    import test_helpers as th

    # Apply helpers
    th.monkeypatch_dummy_embed(agent_module=agent, vector_size=768)
    th.monkeypatch_seed_qdrant(agent_module=agent, idx_module=idx, num_points=3, vector_size=768)

    result = run_compliance_check(query="Seeded test: Golden Visa fees?", visa_type="Golden Visa", expected_fee=250.0, api_key="DUMMY_API_KEY")
    print(json.dumps(result, indent=2))

    assert result.get("status") == "completed", f"Expected completed but got: {result}"
    assert result.get("payment_status") == "SUCCESS", "Expected payment success"
    assert result.get("transaction_hash") and result.get("transaction_hash").startswith("0x")
    print("✓ Seeded path PASSED")


def run_unseeded_path():
    print("\n=== TEST: Unseeded (expect NON_COMPLIANT) ===")
    os.environ.setdefault("GEMINI_API_KEY", "DUMMY_API_KEY")

    import importlib
    import agent
    from agent import run_compliance_check

    # Restore original setup function to avoid seeding
    try:
        import index as idx
        importlib.reload(idx)
        # Also reload agent to pick up original reference
        importlib.reload(agent)
    except Exception:
        pass

    # Monkeypatch only embed to deterministic vectors but do NOT seed Qdrant
    try:
        import test_helpers as th
        th.monkeypatch_dummy_embed(agent_module=agent, vector_size=768)
    except Exception:
        pass

    result = run_compliance_check(query="Unseeded test: Golden Visa fees?", visa_type="Golden Visa", expected_fee=250.0, api_key="DUMMY_API_KEY")
    print(json.dumps(result, indent=2))

    # Expect non-compliant and payment rejected
    assert result.get("compliance_decision") == "NON_COMPLIANT", f"Expected NON_COMPLIANT but got: {result.get('compliance_decision')}"
    assert result.get("payment_status") in ("REJECTED", "COMPLIANCE_FAILURE", "FAILURE"), "Expected payment rejected"
    print("✓ Unseeded path PASSED")


def main():
    run_seeded_path()
    run_unseeded_path()


if __name__ == "__main__":
    main()
