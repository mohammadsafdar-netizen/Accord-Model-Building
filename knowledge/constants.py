"""Configuration for the Insurance Knowledge RAG system."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = Path(__file__).resolve().parent
DATA_DIR = KNOWLEDGE_DIR / "data"
CHROMADB_DIR = KNOWLEDGE_DIR / "chromadb"
SCHEMAS_DIR = ROOT / "schemas"

# Embedding model (sentence-transformers, already installed)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Ollama LLM for chat
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_BASE_URL = "http://localhost:11434"

# ChromaDB collection names
COLLECTION_ACORD_FIELDS = "acord_fields"
COLLECTION_GLOSSARY = "insurance_glossary"
COLLECTION_NAICS = "naics_codes"
COLLECTION_FORM_STRUCTURE = "form_structure"
COLLECTION_STATE_INFO = "state_insurance"
COLLECTION_CUSTOM_DOCS = "custom_documents"

ALL_COLLECTIONS = [
    COLLECTION_ACORD_FIELDS,
    COLLECTION_GLOSSARY,
    COLLECTION_NAICS,
    COLLECTION_FORM_STRUCTURE,
    COLLECTION_STATE_INFO,
    COLLECTION_CUSTOM_DOCS,
]
