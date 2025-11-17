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
from pathlib import Path
from datetime import datetime
import json

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

API_URL = os.getenv("API_URL", "http://localhost:8000")
PAGE_TITLE = "A-PROL: Autonomous Legal Compliance Agent"
PAGE_ICON = "⚖️"

# Visa types for selector
VISA_TYPES = [
    "H1B", "EB1", "EB2", "EB3", "L1", "L1A", "L1B", "O1", "E2", "Other"
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
    
    if "visa_type" not in st.session_state:
        st.session_state.visa_type = "H1B"
    
    if "fee" not in st.session_state:
        st.session_state.fee = 350.0
    
    if "audit_history" not in st.session_state:
        st.session_state.audit_history = []


init_session_state()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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
    try:
        response = requests.get(f"{API_URL}/status", timeout=5)
        response.raise_for_status()
        return response.json()
    except:
        return {"status": "offline"}


def call_api_audit(audit_id: str) -> Dict[str, Any]:
    """Retrieve an audit log entry."""
    try:
        response = requests.get(f"{API_URL}/audit/{audit_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return {"error": "Audit log not found"}


def render_compliance_decision(decision: str, score: float) -> None:
    """Render the compliance decision with visual indicator."""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        color = COMPLIANCE_COLORS.get(decision, "#999999")
        st.markdown(
            f"""
            <div style="
                background-color: {color};
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                color: white;
                font-weight: bold;
                font-size: 24px;
            ">
            {decision}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.metric("Score", f"{score:.2%}")


def render_transparency_panel(result: Dict[str, Any]) -> None:
    """Render the transparency panel showing audit trail details."""
    st.divider()
    st.subheader("🔍 Transparency Panel - Audit Trail")
    
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
    st.divider()
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
                        render_transparency_panel(msg["result"])


def render_audit_history() -> None:
    """Render the audit history sidebar."""
    st.sidebar.divider()
    st.sidebar.subheader("📋 Audit History")
    
    if st.session_state.audit_history:
        for audit in st.session_state.audit_history[-5:]:
            with st.sidebar.expander(f"🔹 {audit.get('audit_id', 'Unknown')[-8:]}"):
                st.write(f"**Query:** {audit.get('query', 'N/A')[:50]}...")
                st.write(f"**Decision:** {audit.get('compliance_decision', 'N/A')}")
                st.write(f"**Score:** {audit.get('compliance_score', 0):.2%}")
                st.write(f"**Visa Type:** {audit.get('visa_type', 'N/A')}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main Streamlit application."""
    
    # Header
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    st.markdown("*Autonomous legal compliance checking with full auditability and transparent decision-making*")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Status
        with st.spinner("Checking API status..."):
            status = call_api_status()
        
        if status.get("status") == "healthy":
            st.success("✓ API Connected")
        else:
            st.error("✗ API Disconnected")
            st.info(f"API URL: {API_URL}")
        
        st.divider()
        
        # Query parameters
        st.subheader("Query Parameters")
        visa_type = st.selectbox(
            "Visa Type",
            VISA_TYPES,
            index=VISA_TYPES.index(st.session_state.visa_type),
            key="visa_type_selector"
        )
        
        fee = st.number_input(
            "Processing Fee ($)",
            min_value=0.0,
            max_value=100000.0,
            value=350.0,
            step=50.0,
            key="fee_input"
        )
        
        st.session_state.visa_type = visa_type
        st.session_state.fee = fee
        
        # Clear history button
        st.divider()
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_result = None
            st.rerun()
        
        # Audit history
        render_audit_history()
    
    # Main content
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.subheader("📝 Compliance Query")
        
        user_query = st.text_area(
            "Enter your compliance question:",
            placeholder="e.g., Can I apply for an H1B visa? What are the requirements?",
            height=100,
            key="query_input"
        )
        
        col_submit, col_clear = st.columns(2)
        
        with col_submit:
            submit_button = st.button("🚀 Submit Query", use_container_width=True, type="primary")
        
        with col_clear:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.current_query = None
    
    with col2:
        st.subheader("✅ Compliance Decision")
        
        if submit_button and user_query:
            # Update current query
            st.session_state.current_query = user_query
            
            # Show spinner while processing
            with st.spinner("🔍 Analyzing query... (RAG Search → Audit Log → Payment Processing)"):
                result = call_api_chat(
                    query=user_query,
                    visa_type=visa_type,
                    fee=fee
                )
            
            # Handle response
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.session_state.last_result = result
                
                # Add to conversation history
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_query
                })
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Compliance decision: {result.get('compliance_decision', 'UNKNOWN')}",
                    "result": result
                })
                
                # Add to audit history
                st.session_state.audit_history.append({
                    "query": user_query,
                    "audit_id": result.get("audit_id"),
                    "compliance_decision": result.get("compliance_decision"),
                    "compliance_score": result.get("compliance_score"),
                    "visa_type": visa_type
                })
                
                # Display decision
                render_compliance_decision(
                    result.get("compliance_decision", "UNKNOWN"),
                    result.get("compliance_score", 0.0)
                )
                
                # Display transparency panel
                render_transparency_panel(result)
        
        elif st.session_state.last_result:
            # Show previous result
            result = st.session_state.last_result
            render_compliance_decision(
                result.get("compliance_decision", "UNKNOWN"),
                result.get("compliance_score", 0.0)
            )
            render_transparency_panel(result)
    
    # Conversation history
    st.divider()
    render_conversation_history()
    
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
