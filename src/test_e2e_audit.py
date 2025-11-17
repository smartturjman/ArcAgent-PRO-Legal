#!/usr/bin/env python3
"""
End-to-end test: run compliance workflow and verify audit log + tx hash.

Usage: python src/test_e2e_audit.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

def main():
    import os
    # Ensure GEMINI_API_KEY is set to avoid initialize_agent raising
    os.environ.setdefault("GEMINI_API_KEY", "DUMMY_API_KEY")

    # Import agent and monkeypatch its reference to setup_gemini_embedding
    import agent
    from agent import run_compliance_check

    # Use shared test helpers to monkeypatch embedding and seed Qdrant
    try:
        import test_helpers as th
        import index as idx

        th.monkeypatch_dummy_embed(agent_module=agent, vector_size=768)
        th.monkeypatch_seed_qdrant(agent_module=agent, idx_module=idx, num_points=3, vector_size=768)
    except Exception as e:
        print(f"Warning: could not apply test helpers: {e}")

    print("\n=== E2E AUDIT TEST ===")
    query = "What are the fees for a 5-year Golden Visa?"

    # Provide a dummy API key to avoid initialize_agent raising
    result = run_compliance_check(query=query, visa_type="Golden Visa", expected_fee=250.0, api_key="DUMMY_API_KEY")

    print("Result:\n", json.dumps(result, indent=2))

    # Basic assertions: for this seeded test we expect a successful payment
    assert result.get("status") == "completed", f"Workflow did not complete: {result}"
    audit_id = result.get("audit_id")
    assert audit_id and audit_id.startswith("AUDIT-"), f"Missing or invalid audit_id: {audit_id}"

    tx_hash = result.get("transaction_hash")
    assert tx_hash and tx_hash.startswith("0x"), f"Missing or invalid transaction_hash: {tx_hash}"

    # Verify audit log file contains the audit entry
    audit_dir = Path(__file__).parent.parent / "audit_logs"
    today_file = audit_dir / f"audit_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
    assert today_file.exists(), f"Audit log file not found: {today_file}"

    found = False
    with open(today_file) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get("audit_id") == audit_id:
                found = True
                print("Found audit entry:", entry.get("audit_id"))
                # check vector ids present
                assert isinstance(entry.get("source_ids"), list), "source_ids missing in audit entry"
                break

    assert found, f"Audit entry {audit_id} not found in {today_file}"

    print("\n✓ E2E Audit test PASSED")


if __name__ == "__main__":
    main()
