"""
Streamlit Dashboard for Insurance Form Automation System.
Displays real-time agent state, logs, and form completion status.
Run with: streamlit run dashboard.py
"""
import streamlit as st
import json
import os
import time
from pathlib import Path

# Configuration
LOG_FILE = "logs/events.jsonl"
REFRESH_INTERVAL = 2 # seconds

st.set_page_config(page_title="Insurance Form Automation Dashboard", layout="wide")

def load_logs(limit: int = 100) -> list:
    """Load last N logs from file."""
    if not os.path.exists(LOG_FILE):
        return []
    logs = []
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                logs.append(json.loads(line.strip()))
    except Exception:
        pass
    return logs

def get_latest_state(logs: list) -> dict:
    """Extract latest state from logs."""
    state = {
        "current_agent": "N/A",
        "current_phase": "N/A",
        "submission_status": "N/A",
        "quote_amount": None
    }
    
    for log in reversed(logs):
        msg = log.get("message", "")
        if "Routing to" in msg:
            parts = msg.split("Routing to ")
            if len(parts) > 1:
                state["current_agent"] = parts[1].split(":")[0].strip()
                break
        if "NODE_ENTRY" in log.get("type", ""):
            state["current_agent"] = msg.replace("Entering ", "").replace(" Node", "")
            break
    
    for log in reversed(logs):
        if "submission" in log.get("type", "").lower():
            if "Quote Generated" in log.get("message", ""):
                state["submission_status"] = "Quoted"
                # Try to parse quote amount
                try:
                    msg = log.get("message", "")
                    if "$" in msg:
                        state["quote_amount"] = msg.split("$")[1].strip()
                except:
                    pass
            break
    
    return state

# --- Main Dashboard ---
st.title("🏢 Insurance Form Automation Dashboard")

# Auto-refresh
placeholder = st.empty()

while True:
    with placeholder.container():
        logs = load_logs(200)
        state = get_latest_state(logs)
        
        # --- Status Cards ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Current Agent", state["current_agent"])
        with col2:
            st.metric("Current Phase", state.get("current_phase", "Common Fields"))
        with col3:
            st.metric("Submission Status", state["submission_status"])
        with col4:
            st.metric("Quote Amount", f"${state['quote_amount']}" if state['quote_amount'] else "N/A")
        
        st.divider()
        
        # --- Logs Table ---
        st.subheader("📜 Event Log (Last 50)")
        
        if logs:
            log_data = []
            for log in reversed(logs[-50:]):
                log_data.append({
                    "Timestamp": log.get("timestamp", "")[:19],
                    "Level": log.get("level", ""),
                    "Type": log.get("type", ""),
                    "Message": log.get("message", "")[:80]
                })
            st.dataframe(log_data, use_container_width=True)
        else:
            st.info("No logs yet. Run the main application to generate events.")
        
        st.divider()
        
        # --- Conversation History (if available in logs) ---
        st.subheader("💬 Recent Conversation")
        conversation = []
        for log in logs:
            if log.get("type") == "CONVERSATION":
                conversation.append(log.get("message", ""))
        
        if conversation:
            for msg in conversation[-10:]:
                st.write(f"🤖 {msg}")
        else:
            st.info("No conversation logged yet.")
    
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
