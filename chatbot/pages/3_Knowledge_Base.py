"""
Knowledge Base Page — Browse and search the insurance knowledge database.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from knowledge.constants import (
    ALL_COLLECTIONS,
    COLLECTION_ACORD_FIELDS,
    COLLECTION_CUSTOM_DOCS,
    COLLECTION_GLOSSARY,
    COLLECTION_NAICS,
    COLLECTION_STATE_INFO,
)
from knowledge.document_loader import process_upload
from knowledge.knowledge_store import InsuranceKnowledgeStore

st.set_page_config(page_title="Knowledge Base - Insurance Bot", page_icon="📚", layout="wide")
st.title("Insurance Knowledge Base")

# ── Initialize ──
if "kb_store" not in st.session_state:
    with st.spinner("Loading knowledge base..."):
        st.session_state["kb_store"] = InsuranceKnowledgeStore()

store = st.session_state["kb_store"]

# ── Stats ──
stats = store.collection_stats()
st.subheader("Collections")
cols = st.columns(len(stats))
for i, (name, count) in enumerate(stats.items()):
    with cols[i]:
        short = name.replace("_", " ").title()
        st.metric(short, f"{count:,}")

st.divider()

# ── Search ──
st.subheader("Search")
search_col, filter_col = st.columns([3, 1])
with search_col:
    query = st.text_input("Search query", placeholder="e.g., bodily injury, NAICS 332710, California auto requirements")
with filter_col:
    collection_filter = st.selectbox("Collection", ["All"] + ALL_COLLECTIONS)

n_results = st.slider("Number of results", 1, 20, 10)

if query:
    with st.spinner("Searching..."):
        if collection_filter == "All":
            results = store.query_all(query, n_results=n_results)
        else:
            results = store.query(query, collection=collection_filter, n_results=n_results)

    if results:
        st.success(f"Found {len(results)} results")
        for i, r in enumerate(results):
            data_type = r.get("metadata", {}).get("data_type", "unknown")
            distance = r.get("distance", 0)
            relevance = max(0, 100 - int(distance * 50))  # rough relevance score

            type_emoji = {
                "field": "📋",
                "glossary": "📖",
                "abbreviation": "🔤",
                "naics": "🏭",
                "form_structure": "📄",
                "state": "🏛️",
                "custom": "📎",
            }.get(data_type, "📌")

            with st.expander(
                f"{type_emoji} {r['document'][:80]}... (relevance: {relevance}%)",
                expanded=(i < 3),
            ):
                st.markdown(f"**Full text:** {r['document']}")
                st.markdown(f"**Type:** `{data_type}` | **Distance:** `{distance:.4f}`")
                if r.get("metadata"):
                    meta_display = {k: v for k, v in r["metadata"].items() if k != "data_type"}
                    if meta_display:
                        st.json(meta_display)
    else:
        st.info("No results found.")

st.divider()

# ── Quick Lookups ──
st.subheader("Quick Lookups")

tab1, tab2, tab3, tab4 = st.tabs(["ACORD Field", "Glossary Term", "NAICS Code", "State Info"])

with tab1:
    field_name = st.text_input("Field name", placeholder="Policy_Status_BoundIndicator_A")
    if field_name:
        info = store.get_field_info(field_name)
        if info:
            st.success(info["document"])
            st.json(info["metadata"])
        else:
            # Try semantic search
            results = store.query(field_name, collection=COLLECTION_ACORD_FIELDS, n_results=5)
            if results:
                st.info("Exact match not found. Similar fields:")
                for r in results:
                    st.markdown(f"- {r['document'][:120]}")

with tab2:
    term = st.text_input("Insurance term", placeholder="subrogation")
    if term:
        result = store.get_glossary_term(term)
        if result:
            st.success(result["document"])
        else:
            st.warning("Term not found.")

with tab3:
    naics_code = st.text_input("NAICS code", placeholder="332710")
    if naics_code:
        result = store.get_naics_description(naics_code)
        if result:
            st.success(result["document"])
        else:
            st.warning("Code not found.")

with tab4:
    state_code = st.text_input("State code", placeholder="CA")
    if state_code:
        result = store.get_state_info(state_code.upper())
        if result:
            st.success(result["document"])
        else:
            st.warning("State not found.")

st.divider()

# ── Upload Documents ──
st.subheader("Upload Documents")
st.markdown("Add your own documents (policy guides, manuals, notes) to the knowledge base.")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "txt", "md", "json", "csv"],
    help="Supported: PDF, TXT, Markdown, JSON, CSV (max 10MB)",
)
upload_tags = st.text_input(
    "Tags (optional)",
    placeholder="e.g., policy-guide, company-manual",
    help="Comma-separated tags for filtering",
)

if uploaded_file and st.button("Upload to Knowledge Base", type="primary"):
    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > 10 * 1024 * 1024:
        st.error("File too large (max 10MB).")
    else:
        metadata = {}
        if upload_tags.strip():
            metadata["tags"] = upload_tags.strip()
        with st.spinner(f"Processing {uploaded_file.name}..."):
            result = process_upload(file_bytes, uploaded_file.name, store, metadata)
        if result["chunks"] > 0:
            st.success(
                f"Uploaded **{uploaded_file.name}**: {result['chunks']} chunks "
                f"({result['chars']:,} characters)"
            )
        else:
            st.warning("No text could be extracted from this file.")

# ── Manage Uploads ──
with st.expander("Manage Uploaded Documents"):
    custom_docs = store.list_custom_documents(n=200)
    if custom_docs:
        # Group by source file
        files: dict = {}
        for doc in custom_docs:
            fname = doc["metadata"].get("source_file", "unknown")
            if fname not in files:
                files[fname] = {"ids": [], "chunks": 0, "uploaded_at": "", "tags": ""}
            files[fname]["ids"].append(doc["id"])
            files[fname]["chunks"] += 1
            files[fname]["uploaded_at"] = doc["metadata"].get("uploaded_at", "")
            files[fname]["tags"] = doc["metadata"].get("tags", "")

        st.markdown(f"**{len(files)} uploaded file(s), {len(custom_docs)} total chunks**")

        for fname, info in files.items():
            col1, col2 = st.columns([4, 1])
            with col1:
                label = f"**{fname}** — {info['chunks']} chunks"
                if info["uploaded_at"]:
                    label += f" (uploaded {info['uploaded_at']})"
                if info["tags"]:
                    label += f" | tags: {info['tags']}"
                st.markdown(label)
            with col2:
                if st.button("Delete", key=f"del_{fname}"):
                    store.delete_documents(info["ids"], COLLECTION_CUSTOM_DOCS)
                    st.success(f"Deleted {fname}")
                    st.rerun()
    else:
        st.info("No uploaded documents yet.")

st.sidebar.markdown("---")
st.sidebar.markdown("**ACORD Insurance Bot** v1.0")
