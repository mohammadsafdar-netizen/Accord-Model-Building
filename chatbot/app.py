"""
Insurance Knowledge Bot — Streamlit Welcome Page

Run with:
    .venv/bin/streamlit run chatbot/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="ACORD Insurance Bot",
    page_icon="🏢",
    layout="wide",
)

st.title("ACORD Insurance Knowledge Bot")

st.markdown("""
Welcome to the **Insurance Knowledge Assistant** — an AI-powered tool for insurance agents and underwriters.

### Features

- **Chat** — Ask questions about insurance terminology, ACORD forms, coverage types, state requirements, and NAICS codes
- **Extract Form** — Upload an ACORD PDF and extract structured field data
- **Knowledge Base** — Browse and search the insurance knowledge database

### Knowledge Sources

| Source | Entries | Description |
|--------|---------|-------------|
| ACORD Field Definitions | ~1,585 | Every field across forms 125, 127, 137 with tooltips |
| Insurance Glossary | ~94 | Core insurance terms and definitions |
| Abbreviations | ~38 | Common industry abbreviations (BI, PD, CGL, etc.) |
| NAICS Codes | ~2,125 | Industry classification codes from Census Bureau |
| State Insurance Info | 51 | All US states + DC with minimum auto coverage requirements |
| Form Structure | 27 | ACORD form layouts, page descriptions, categories |

### Getting Started

Select a page from the **sidebar** to begin.
""")

st.sidebar.markdown("---")
st.sidebar.markdown("**ACORD Insurance Bot** v1.0")
st.sidebar.markdown("Powered by Ollama + ChromaDB")
