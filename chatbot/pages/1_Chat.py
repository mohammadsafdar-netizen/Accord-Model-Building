"""
Chat Page — Conversational insurance assistant with RAG.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from chatbot.chat_engine import generate_response_streaming
from knowledge.constants import ALL_COLLECTIONS, OLLAMA_MODEL
from knowledge.knowledge_store import InsuranceKnowledgeStore

st.set_page_config(page_title="Chat - Insurance Bot", page_icon="💬", layout="wide")
st.title("Insurance Knowledge Chat")

# ── Sidebar controls ──
st.sidebar.header("Settings")
use_rag = st.sidebar.checkbox("Enable RAG context", value=True)
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
n_results = st.sidebar.number_input("Results per collection", 1, 10, 3)

model = st.sidebar.text_input("Ollama model", value=OLLAMA_MODEL)

# Collection filter
collection_options = ["All"] + ALL_COLLECTIONS
selected_collections = st.sidebar.multiselect(
    "Search collections",
    options=collection_options,
    default=["All"],
)
if "All" in selected_collections:
    search_collections = None
else:
    search_collections = selected_collections

st.sidebar.markdown("---")
if st.sidebar.button("Clear chat history"):
    st.session_state["chat_history"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**ACORD Insurance Bot** v1.0")

# ── Initialize ──
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "knowledge_store" not in st.session_state:
    with st.spinner("Loading knowledge base..."):
        st.session_state["knowledge_store"] = InsuranceKnowledgeStore()
        stats = st.session_state["knowledge_store"].collection_stats()
        total = sum(stats.values())
    st.sidebar.success(f"Knowledge base: {total:,} documents")

knowledge_store = st.session_state["knowledge_store"]

# ── Display chat history ──
for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ──
if prompt := st.chat_input("Ask about insurance, ACORD forms, coverage, states..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state["chat_history"].append({"role": "user", "content": prompt})

    # Generate and stream response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        for chunk in generate_response_streaming(
            query=prompt,
            knowledge_store=knowledge_store if use_rag else None,
            use_rag=use_rag,
            n_results=n_results,
            temperature=temperature,
            chat_history=st.session_state["chat_history"],
            model=model,
            collections=search_collections,
        ):
            full_response += chunk
            response_placeholder.markdown(full_response + "▌")

        response_placeholder.markdown(full_response)

    st.session_state["chat_history"].append(
        {"role": "assistant", "content": full_response}
    )
