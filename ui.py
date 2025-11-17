#!/usr/bin/env python3
"""
A-PROL Interactive UI - Phase 4

Streamlit application providing a user-friendly interface for compliance queries
with real-time transparency into the auditable workflow.

Features:
- Multi-turn conversation with context persistence
- Real-time compliance decision display
- Transparency panel showing audit trail (source IDs, compliance score, tx hash)
- Query history tracking
- Interactive audit log viewer

Usage:
  streamlit run ui.py

"""

import os
import sys
import subprocess
import time
import atexit
from pathlib import Path
from datetime import datetime
import json
import base64
from io import BytesIO
import textwrap

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import requests
from typing import Optional, Dict, Any, List

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
AUTO_START_API = os.getenv("AUTO_START_API", "true").lower() in {"1", "true", "yes"}
API_BOOT_TIMEOUT = int(os.getenv("API_BOOT_TIMEOUT", "15"))
PAGE_TITLE = "A-PROL: Total Compliance Suite"
PAGE_ICON = "⚖️"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = Path(__file__).parent
LOGO_CANDIDATES = [
    PROJECT_ROOT / "smart_turjman_logo.png",
    Path(__file__).resolve().parents[1] / "logo.png"
]
LOGO_BASE64 = None
LOGO_BYTES = None
for logo_path in LOGO_CANDIDATES:
    if logo_path.exists():
        LOGO_BYTES = logo_path.read_bytes()
        LOGO_BASE64 = base64.b64encode(LOGO_BYTES).decode("utf-8")
        break

CUSTOM_STYLES = """
<style>
:root {
    --card-bg: #ffffff;
    --border-color: #e5e7ef;
}
.aprol-header {
    display: flex;
    align-items: center;
    gap: 20px;
    margin-bottom: 0.5rem;
}
.aprol-header img {
    height: 60px;
    width: auto;
    border-radius: 10px;
    box-shadow: 0 8px 18px rgba(0, 0, 0, 0.15);
}
.aprol-header-title {
    margin: 0;
    font-size: 2.6rem;
    line-height: 1.15;
}
.aprol-subtitle {
    margin: 0;
    color: #374151;
    font-weight: 500;
    font-size: 1.05rem;
}
.audit-entry {
    list-style: none;
    padding-left: 0;
    font-size: 0.9rem;
    color: #4b5563;
}
.audit-entry li {
    margin-bottom: 0.3rem;
}
.audit-entry li strong {
    color: #111827;
    font-weight: 600;
}
.section-caption {
    color: #6b7280;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}
.transparency-panel {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 1rem 1.25rem;
    margin-top: 0.8rem;
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}
.transparency-panel h3 {
    margin-top: 0;
    font-size: 1.15rem;
}
div[data-testid="stMetric"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.85rem;
    color: #6b7280;
}
div[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 600;
    color: #111827;
}
.compliance-card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    padding: 24px 28px;
    margin: 0 0 1rem 0;
    width: 100%;
    box-sizing: border-box;
}
.compliance-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
}
.compliance-card-eyebrow {
    color: #6b7280;
    font-size: 0.9rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.compliance-card-title {
    font-size: 1.6rem;
    font-weight: 600;
    color: #111827;
    margin: 0.15rem 0 0;
}
.compliance-badge {
    border-radius: 999px;
    padding: 0.35rem 1rem;
    font-weight: 600;
    font-size: 0.95rem;
    color: white;
    letter-spacing: 0.03em;
}
.compliance-divider {
    border-top: 1px solid rgba(15, 23, 42, 0.08);
    margin: 1.25rem 0;
}
.compliance-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.1rem 1.8rem;
}
.compliance-field-label {
    font-size: 0.85rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.25rem;
}
.compliance-field-value {
    font-size: 1.1rem;
    color: #111827;
    font-weight: 600;
    word-break: break-word;
}
.compliance-field-value code {
    background: #f3f4f6;
    padding: 0.1rem 0.4rem;
    border-radius: 6px;
    font-size: 0.95rem;
}
.compliance-steps {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 1rem;
    width: 100%;
    flex-wrap: wrap;
    justify-content: space-between;
}
.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 0 1 120px;
    text-align: center;
}
.step-icon {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    border: 2px solid #d1d5db;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    color: #9ca3af;
    background: #ffffff;
}
.step-item.complete .step-icon {
    border-color: #10b981;
    background: #ecfdf5;
    color: #059669;
}
.step-label {
    margin-top: 0.4rem;
    font-size: 0.85rem;
    font-weight: 600;
    color: #4b5563;
}
.step-connector {
    height: 2px;
    background: #e5e7eb;
    flex: 1 1 24px;
    min-width: 16px;
    max-width: 60px;
}
.step-connector.complete {
    background: linear-gradient(90deg, #059669, #34d399);
}
.aprol-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(18px);
    padding: 0.85rem 1.5rem;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    box-shadow: 0 20px 60px rgba(15, 23, 42, 0.15);
    margin-bottom: 1.2rem;
}
.nav-left {
    display: flex;
    align-items: center;
    gap: 0.85rem;
}
.nav-logo {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    object-fit: cover;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.15);
}
.nav-logo-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #1d4ed8, #3b82f6);
    color: white;
    font-weight: 700;
    font-size: 1.1rem;
}
.nav-brand {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
    letter-spacing: 0.05em;
}
.nav-subtext {
    font-size: 0.85rem;
    color: #6b7280;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.nav-center {
    font-size: 1.35rem;
    font-weight: 600;
    color: #0f172a;
    letter-spacing: 0.03em;
}
.nav-right {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.nav-icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: #f3f4f6;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    color: #1f2937;
    border: 1px solid rgba(148, 163, 184, 0.4);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.nav-profile span {
    font-weight: 600;
    letter-spacing: 0.05em;
}
section[data-testid="stSidebar"] {
    background-color: #F5F7FA !important;
    min-width: 320px;
    max-width: 360px;
}
section[data-testid="stSidebar"] > div {
    padding: 1.5rem 1.5rem 2rem !important;
}
.sidebar-section {
    background: #ffffff;
    border-radius: 18px;
    padding: 1.2rem 1.3rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
}
.sidebar-section h2,
.sidebar-section h3 {
    margin-top: 0;
    margin-bottom: 0.6rem;
}
</style>
"""

# Visa types for selector
VISA_TYPES = [
    "5-Year Golden Visa (Investor)",
    "10-Year Golden Visa (Talent)",
    "PRO Service (New Company Setup)",
    "Employment Visa Renewal"
]

# Compliance colors
COMPLIANCE_COLORS = {
    "COMPLIANT": "#00AA00",
    "NON_COMPLIANT": "#AA0000",
    "REVIEW_REQUIRED": "#FFAA00"
}


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(CUSTOM_STYLES, unsafe_allow_html=True)


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize Streamlit session state for multi-turn conversation."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "current_query" not in st.session_state:
        st.session_state.current_query = None
    
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    
    if "last_error" not in st.session_state:
        st.session_state.last_error = None
    
    if "visa_type" not in st.session_state:
        st.session_state.visa_type = VISA_TYPES[0]
    
    if "fee" not in st.session_state:
        st.session_state.fee = 350.0
    
    if "audit_history" not in st.session_state:
        st.session_state.audit_history = []
    
    if "compliance_query_input" not in st.session_state:
        st.session_state.compliance_query_input = ""


init_session_state()

if "api_bootstrap_done" not in st.session_state:
    st.session_state.api_bootstrap_done = False
if "api_bootstrap_error" not in st.session_state:
    st.session_state.api_bootstrap_error = None
if "api_process" not in st.session_state:
    st.session_state.api_process = None

def reset_compliance_query():
    """Reset compliance query input and associated state."""
    st.session_state.compliance_query_input = ""
    st.session_state.current_query = None
    st.session_state.last_result = None
    st.session_state.last_error = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _ping_api_status(timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """Return API status payload or None if backend is unreachable."""
    try:
        response = requests.get(f"{API_URL}/status", timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _ensure_api_server_running() -> bool:
    """Start the FastAPI backend automatically if enabled."""
    if not AUTO_START_API:
        return False

    if _ping_api_status():
        st.session_state.api_bootstrap_error = None
        st.session_state.api_bootstrap_done = True
        return True

    api_log_path = BASE_DIR / "api_autostart.log"
    try:
        log_handle = open(api_log_path, "a")
        process = subprocess.Popen(
            [sys.executable, "api.py"],
            cwd=BASE_DIR,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
        st.session_state.api_process = process

        def _cleanup():
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except Exception:
                pass
            try:
                log_handle.close()
            except Exception:
                pass

        atexit.register(_cleanup)
    except Exception as exc:
        st.session_state.api_bootstrap_error = str(exc)
        return False

    deadline = time.time() + API_BOOT_TIMEOUT
    while time.time() < deadline:
        time.sleep(1)
        if _ping_api_status():
            st.session_state.api_bootstrap_error = None
            st.session_state.api_bootstrap_done = True
            return True

    st.session_state.api_bootstrap_error = (
        f"Timed out waiting for FastAPI to start after {API_BOOT_TIMEOUT}s."
    )
    return False


def call_api_chat(query: str, visa_type: Optional[str] = None, fee: float = 350.0) -> Dict[str, Any]:
    """Call the /chat endpoint on the REST API."""
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "query": query,
                "visa_type": visa_type,
                "expected_fee": fee
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Cannot connect to API at {API_URL}. Is the server running?"}
    except Exception as e:
        return {"error": str(e)}


def call_api_status() -> Dict[str, Any]:
    """Call the /status endpoint on the REST API."""
    payload = _ping_api_status()
    if payload:
        return payload
    return {"status": "offline"}


def call_api_audit(audit_id: str) -> Dict[str, Any]:
    """Retrieve an audit log entry."""
    try:
        response = requests.get(f"{API_URL}/audit/{audit_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return {"error": "Audit log not found"}


def render_compliance_decision(result: Dict[str, Any]) -> None:
    """Render the compliance decision as a modern enterprise card."""
    decision = result.get("compliance_decision", "UNKNOWN")
    score = result.get("compliance_score", 0.0)
    audit_id = result.get("audit_id", "N/A")
    source_ids = result.get("source_ids", [])
    context_length = result.get("context_length", 0)
    payment_status = result.get("payment_status", "UNKNOWN")
    transaction_hash = result.get("transaction_hash") or "—"
    vector_ids = ", ".join(map(str, source_ids)) if source_ids else "—"

    badge_color = COMPLIANCE_COLORS.get(decision, "#1f2937")
    payment_display = payment_status.replace("_", " ").title()
    steps_data = [
        ("RAG Retrieved", bool(source_ids)),
        ("Audit Logged", bool(audit_id and audit_id != "N/A")),
        ("Compliance Verified", decision and decision != "UNKNOWN"),
        ("Payment Executed", payment_status.upper() == "SUCCESS"),
    ]
    step_parts = []
    for idx, (label, complete) in enumerate(steps_data):
        status_class = "complete" if complete else ""
        icon_symbol = "&#10003;" if complete else ""
        step_parts.append(textwrap.dedent(f"""
            <div class="step-item {status_class}">
                <div class="step-icon">{icon_symbol}</div>
                <div class="step-label">{label}</div>
            </div>
        """).strip())
        if idx < len(steps_data) - 1:
            connector_class = "complete" if complete else ""
            step_parts.append(f'<div class="step-connector {connector_class}"></div>')
    steps_html = "".join(step_parts)

    fields = [
        ("Score", f"{score:.2%}"),
        ("Audit ID", audit_id if audit_id else "N/A"),
        ("Source Document Count", str(len(source_ids))),
        ("Context Size", f"{context_length:,} chars"),
        ("Payment Status", payment_display),
        ("Transaction Hash", transaction_hash),
    ]

    grid_cells = []
    for label, value in fields:
        display_value = value
        if label in {"Transaction Hash"} and value not in {"—", "N/A"}:
            display_value = f"<code>{value}</code>"
        grid_cells.append(textwrap.dedent(f"""
            <div>
                <div class="compliance-field-label">{label}</div>
                <div class="compliance-field-value">{display_value}</div>
            </div>
        """).strip())
    grid_html = "".join(grid_cells)

    card_html = textwrap.dedent(f"""
        <div class="compliance-card">
            <div class="compliance-card-header">
                <div>
                    <div class="compliance-card-eyebrow">Compliance Decision</div>
                    <p class="compliance-card-title">Result Overview</p>
                </div>
                <span class="compliance-badge" style="background:{badge_color};">{decision}</span>
            </div>
            <div class="compliance-steps">
                {steps_html}
            </div>
            <div class="compliance-divider"></div>
            <div class="compliance-grid">
                {grid_html}
            </div>
            <div class="compliance-divider"></div>
            <div class="compliance-field-label" style="margin-bottom:0.35rem;">Vector IDs</div>
            <div class="compliance-field-value"><code>{vector_ids}</code></div>
        </div>
    """).strip()
    st.markdown(card_html, unsafe_allow_html=True)


def render_transparency_panel(result: Dict[str, Any]) -> None:
    """Render the transparency panel showing audit trail details."""
    st.markdown('<div class="transparency-panel">', unsafe_allow_html=True)
    st.markdown("#### 🔍 Transparency Panel - Audit Trail")
    
    # Create columns for audit data
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Audit ID", result.get("audit_id", "N/A")[-8:], help="Unique audit identifier")
    
    with col2:
        source_ids = result.get("source_ids", [])
        st.metric("Source Documents", len(source_ids), help="Number of documents used for decision")
    
    with col3:
        st.metric("Context Size", f"{result.get('context_length', 0)} chars", help="Total context length")
    
    # Transaction details
    st.markdown("<hr/>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Payment Status:**")
        payment_status = result.get("payment_status", "UNKNOWN")
        if payment_status == "SUCCESS":
            st.success(payment_status)
        else:
            st.error(payment_status)
    
    with col2:
        if result.get("transaction_hash"):
            st.write("**Transaction Hash:**")
            st.code(result.get("transaction_hash"), language="text")
    
    # Source IDs display
    if source_ids:
        st.write("**Vector IDs (Source Documents):**")
        st.info(f"Source IDs: {source_ids}")
    
    # Timestamp
    st.caption(f"Decision recorded at: {result.get('timestamp', 'unknown')}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_conversation_history() -> None:
    """Render the conversation history."""
    if st.session_state.messages:
        st.subheader("💬 Conversation History")
        
        for i, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(msg["content"])
                    if msg.get("result"):
                        summary = msg["result"]
                        audit_id = summary.get("audit_id", "N/A")[-8:]
                        st.caption(
                            f"Audit {audit_id} • Score {summary.get('compliance_score', 0):.2%} • "
                            f"Payment {summary.get('payment_status', 'UNKNOWN')}"
                        )


def render_audit_history(container=None) -> None:
    """Render the audit history inside the provided container."""
    target = container or st
    if not st.session_state.audit_history:
        target.caption("Submissions will appear here once a compliance review is completed.")
        return
    
    recent_audits = list(reversed(st.session_state.audit_history[-5:]))
    for audit in recent_audits:
        audit_id = audit.get("audit_id", "Unknown")[-8:]
        preview = audit.get("query", "N/A")
        preview = (preview[:70] + "...") if len(preview) > 73 else preview
        with target.expander(f"{audit_id} • {audit.get('compliance_decision', 'N/A')}"):
            container_html = f"""
            <ul class="audit-entry">
                <li><strong>Query:</strong> {preview}</li>
                <li><strong>Score:</strong> {audit.get('compliance_score', 0):.2%}</li>
                <li><strong>Visa Type:</strong> {audit.get('visa_type', 'N/A')}</li>
            </ul>
            """
            target.markdown(container_html, unsafe_allow_html=True)
            if audit.get("transaction_hash"):
                target.caption("Transaction Hash")
                target.code(audit["transaction_hash"], language="text")
            if audit.get("evidence_id"):
                target.caption("Tokenized Evidence ID")
                target.code(audit["evidence_id"], language="text")


# ============================================================================
# MAIN APPLICATION
# ============================================================================


def call_api_corporate_audit(payload: str) -> Dict[str, Any]:
    """Call the /audit/corporate endpoint."""
    try:
        response = requests.post(f"{API_URL}/audit/corporate", data=payload, headers={"Content-Type": "application/json"}, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def call_api_forensics_evidence(file) -> Dict[str, Any]:
    """Call the /forensics/evidence endpoint with file upload."""
    try:
        files = {"file": (file.name, file, file.type)}
        response = requests.post(f"{API_URL}/forensics/evidence", files=files, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    """Main Streamlit application."""

    # Attempt to auto-start the FastAPI backend if requested
    if AUTO_START_API:
        backend_online = _ping_api_status() is not None
        if not backend_online:
            st.session_state.api_bootstrap_done = False
        if not st.session_state.api_bootstrap_done:
            with st.spinner("Starting FastAPI backend..."):
                backend_online = _ensure_api_server_running()
            if backend_online:
                st.success("FastAPI backend started for this session.")
            elif st.session_state.api_bootstrap_error:
                st.warning(f"Auto-start failed: {st.session_state.api_bootstrap_error}")

    col_logo, col_title = st.columns([1, 3])
    with col_logo:
        if LOGO_BYTES:
            st.image(BytesIO(LOGO_BYTES), width=80)
        else:
            st.markdown("### **A-PROL**")
    with col_title:
        st.markdown("## **Total Compliance Suite**")
    st.markdown(
        '<p class="aprol-subtitle">A comprehensive Meta-Agent ensuring full regulatory governance for high-value services. '
        'Executes autonomous DLT payments (Financial Agent) only after verifying compliance via Qdrant RAG. '
        'Provides auditable evidence tokenization for legal defense forensics.</p>',
        unsafe_allow_html=True
    )
    st.divider()

    with st.sidebar:
        if LOGO_BYTES:
            st.image(BytesIO(LOGO_BYTES), caption="Smart Turjman", use_container_width=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.header("🧭 Control Center")
        with st.spinner("Checking API status..."):
            status = call_api_status()
        if status.get("status") == "healthy":
            st.success("✓ API Connected")
        else:
            st.error("✗ API Disconnected")
            st.info(f"API URL: {API_URL}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("🧩 Query Parameters")
        visa_type = st.selectbox(
            "Visa Type",
            VISA_TYPES,
            index=VISA_TYPES.index(st.session_state.visa_type),
            key="visa_type_selector"
        )
        fee = st.number_input(
            "Processing Fee (AED)",
            min_value=0.0,
            max_value=100000.0,
            value=1500.0,
            step=50.0,
            key="fee_input"
        )
        st.session_state.visa_type = visa_type
        st.session_state.fee = fee
        if st.button("Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_result = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        with st.expander("📋 Audit History", expanded=False):
            render_audit_history()
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabs for new services
    tabs = st.tabs(["Compliance Query", "Corporate Audit Check", "Legal Forensics Upload"])

    # Tab 1: Compliance Query (existing)
    with tabs[0]:
        col1, col2 = st.columns([0.55, 0.45], gap="large")
        with col1:
            st.markdown("#### Compliance Query")
            user_query = st.text_area(
                label="",
                key="compliance_query_input",
                placeholder="What is the current fee for a 5-Year Investor Golden Visa? Please confirm the required documents, and authorize payment.",
                height=150,
                label_visibility="collapsed"
            )
            col_submit, col_clear = st.columns(2)
            with col_submit:
                submit_button = st.button("Submit Query", use_container_width=True, type="primary")
            with col_clear:
                st.button("Reset", use_container_width=True, on_click=reset_compliance_query)
        with col2:
            st.markdown("#### Compliance Decision")
            trimmed_query = user_query.strip()
            if submit_button:
                if not trimmed_query:
                    st.session_state.last_result = None
                    st.session_state.last_error = "Please enter a compliance question before submitting."
                else:
                    st.session_state.current_query = trimmed_query
                    with st.spinner("Analyzing query... (RAG Search → Audit Log → Payment Processing)"):
                        result = call_api_chat(
                            query=trimmed_query,
                            visa_type=visa_type,
                            fee=fee
                        )
                    if result.get("error"):
                        st.session_state.last_result = None
                        st.session_state.last_error = result["error"]
                    else:
                        st.session_state.last_result = result
                        st.session_state.last_error = None
                        st.session_state.messages.append({
                            "role": "user",
                            "content": trimmed_query
                        })
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Compliance decision: {result.get('compliance_decision', 'UNKNOWN')}",
                            "result": result
                        })
                        st.session_state.audit_history.append({
                            "query": trimmed_query,
                            "audit_id": result.get("audit_id"),
                            "compliance_decision": result.get("compliance_decision"),
                            "compliance_score": result.get("compliance_score"),
                            "visa_type": visa_type,
                            "transaction_hash": result.get("transaction_hash"),
                            "evidence_id": result.get("evidence_hash")
                        })
            if st.session_state.last_error:
                st.error(f"Error: {st.session_state.last_error}")
            elif st.session_state.last_result:
                result = st.session_state.last_result
                if result.get("note"):
                    st.info(f"Mode: {result['note']}")
                render_compliance_decision(result)
                render_transparency_panel(result)
            else:
                st.info("Submit a compliance query to generate a decision.")
        st.divider()
        render_conversation_history()

    # Tab 2: Corporate Audit Check
    with tabs[1]:
        with st.container():
            st.markdown("#### Corporate Audit Check")
            st.caption("Submit structured payloads for corporate compliance reviews.")
            audit_payload = st.text_area(
                "Enter JSON payload for corporate audit:",
                placeholder='{"audit_type": "UBO", "trade_license": "TL-09876", "beneficial_owner_id": "800123"}',
                height=120,
                key="corporate_audit_input"
            )
            if st.button("Submit Corporate Audit", key="submit_corporate_audit"):
                with st.spinner("Submitting corporate audit..."):
                    result = call_api_corporate_audit(audit_payload)
                if result.get("error"):
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("Corporate audit submitted successfully.")
                    st.json(result)
                    st.session_state.audit_history.append({
                        "query": audit_payload,
                        "audit_id": result.get("audit_id"),
                        "compliance_decision": result.get("compliance_decision"),
                        "compliance_score": result.get("compliance_score"),
                        "transaction_hash": result.get("transaction_hash"),
                        "evidence_id": result.get("evidence_hash")
                    })

    # Tab 3: Legal Forensics Upload
    with tabs[2]:
        with st.container():
            st.markdown("#### Legal Forensics Upload")
            st.caption("Ingest documents, media, or evidence for tokenization and custody tracking.")
            uploaded_file = st.file_uploader("Upload multi-modal evidence for tokenization and chain-of-custody audit.", type=None, key="forensics_file_upload")
            if uploaded_file and st.button("Submit Evidence File", key="submit_evidence_file"):
                with st.spinner("Uploading and processing evidence file..."):
                    result = call_api_forensics_evidence(uploaded_file)
                if result.get("error"):
                    st.error(f"Error: {result['error']}")
                else:
                    st.success("Evidence file uploaded and processed.")
                    st.json(result)
                    st.session_state.audit_history.append({
                        "query": f"File upload: {uploaded_file.name}",
                        "audit_id": result.get("audit_id"),
                        "compliance_decision": result.get("compliance_decision"),
                        "compliance_score": result.get("compliance_score"),
                        "transaction_hash": result.get("transaction_hash"),
                        "evidence_id": result.get("evidence_hash")
                    })

    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🔐 All decisions are logged and auditable")
    with col2:
        st.caption("⚡ Powered by Gemini + Qdrant + FastAPI")
    with col3:
        st.caption("📊 Full transparency through audit trail")

if __name__ == "__main__":
    main()
