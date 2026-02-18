#!/usr/bin/env python3
"""
Build the ChromaDB knowledge base from collected data.

Reads JSON files from knowledge/data/ and creates 5 ChromaDB collections
with embeddings via sentence-transformers (MiniLM-L6-v2).

Usage:
    .venv/bin/python knowledge/build_knowledge_base.py
    .venv/bin/python knowledge/build_knowledge_base.py --reset  # rebuild from scratch
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from knowledge.constants import (
    CHROMADB_DIR,
    COLLECTION_ACORD_FIELDS,
    COLLECTION_FORM_STRUCTURE,
    COLLECTION_GLOSSARY,
    COLLECTION_NAICS,
    COLLECTION_STATE_INFO,
    DATA_DIR,
    EMBEDDING_MODEL,
)


def get_embedding_function():
    """Create a ChromaDB-compatible embedding function using sentence-transformers."""
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def get_client():
    """Get persistent ChromaDB client."""
    import chromadb
    CHROMADB_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMADB_DIR))


def build_acord_fields(client, ef):
    """Build collection from schema field definitions."""
    data = json.loads((DATA_DIR / "schema_knowledge.json").read_text())
    collection = client.get_or_create_collection(
        name=COLLECTION_ACORD_FIELDS, embedding_function=ef
    )

    ids, documents, metadatas = [], [], []
    for item in data:
        field_name = item["field_name"]
        tooltip = item.get("tooltip", "")
        ftype = item.get("type", "text")
        category = item.get("category", "general")
        form_type = item.get("form_type", "")

        # Build a rich text document for embedding
        human_name = field_name.replace("_", " ").rsplit(" ", 1)[0]  # strip suffix
        doc = f"ACORD {form_type} field: {field_name}. {tooltip}"
        if ftype == "checkbox":
            doc += " This is a checkbox field (true/false)."
        doc += f" Category: {category}."

        ids.append(f"field_{form_type}_{field_name}")
        documents.append(doc)
        metadatas.append({
            "field_name": field_name,
            "form_type": form_type,
            "field_type": ftype,
            "category": category,
            "data_type": "field",
        })

    # ChromaDB batch limit is 5461
    batch_size = 5000
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
        )
    print(f"  acord_fields: {len(ids)} documents")
    return len(ids)


def build_glossary(client, ef):
    """Build collection from insurance glossary terms."""
    data = json.loads((DATA_DIR / "insurance_glossary.json").read_text())

    # Also add abbreviations
    abbrev_path = DATA_DIR / "abbreviations.json"
    if abbrev_path.exists():
        abbrevs = json.loads(abbrev_path.read_text())
    else:
        abbrevs = []

    collection = client.get_or_create_collection(
        name=COLLECTION_GLOSSARY, embedding_function=ef
    )

    ids, documents, metadatas = [], [], []

    for item in data:
        term = item["term"]
        definition = item["definition"]
        doc = f"{term}: {definition}"
        ids.append(f"glossary_{term.lower().replace(' ', '_')[:60]}")
        documents.append(doc)
        metadatas.append({"term": term, "data_type": "glossary"})

    for item in abbrevs:
        abbr = item["abbr"]
        full = item["full"]
        context = item.get("context", "")
        doc = f"{abbr} ({full}): {context}"
        ids.append(f"abbr_{abbr.lower()}")
        documents.append(doc)
        metadatas.append({"term": abbr, "full_name": full, "data_type": "abbreviation"})

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"  insurance_glossary: {len(ids)} documents (terms + abbreviations)")
    return len(ids)


def build_naics(client, ef):
    """Build collection from NAICS codes."""
    data = json.loads((DATA_DIR / "naics_codes.json").read_text())
    collection = client.get_or_create_collection(
        name=COLLECTION_NAICS, embedding_function=ef
    )

    ids, documents, metadatas = [], [], []
    for item in data:
        code = item["code"]
        desc = item["description"]
        doc = f"NAICS {code}: {desc}"
        ids.append(f"naics_{code}")
        documents.append(doc)
        metadatas.append({"code": code, "data_type": "naics"})

    batch_size = 5000
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
        )
    print(f"  naics_codes: {len(ids)} documents")
    return len(ids)


def build_form_structure(client, ef):
    """Build collection from form structure descriptions."""
    data = json.loads((DATA_DIR / "form_structure.json").read_text())
    collection = client.get_or_create_collection(
        name=COLLECTION_FORM_STRUCTURE, embedding_function=ef
    )

    ids, documents, metadatas = [], [], []
    for item in data:
        title = item["title"]
        content = item["content"]
        form_type = item.get("form_type", "all")
        section = item.get("section", "")
        doc = f"{title}. {content}"
        safe_title = title.lower().replace(" ", "_").replace(":", "")[:40]
        ids.append(f"form_{form_type}_{section}_{safe_title}")
        documents.append(doc)
        metadatas.append({
            "form_type": form_type,
            "section": section,
            "data_type": "form_structure",
        })

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"  form_structure: {len(ids)} documents")
    return len(ids)


def build_state_info(client, ef):
    """Build collection from state insurance info."""
    data = json.loads((DATA_DIR / "state_info.json").read_text())
    collection = client.get_or_create_collection(
        name=COLLECTION_STATE_INFO, embedding_function=ef
    )

    ids, documents, metadatas = [], [], []
    for item in data:
        code = item["code"]
        name = item["name"]
        bi = item.get("auto_min_bi", "")
        pd = item.get("auto_min_pd", "")
        doi = item.get("doi_url", "")
        doc = (
            f"{name} ({code}) insurance requirements. "
            f"Minimum auto liability: BI {bi} per person/accident, PD ${pd}. "
            f"Department of Insurance: {doi}"
        )
        ids.append(f"state_{code}")
        documents.append(doc)
        metadatas.append({
            "state_code": code,
            "state_name": name,
            "data_type": "state",
        })

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"  state_insurance: {len(ids)} documents")
    return len(ids)


def main():
    parser = argparse.ArgumentParser(description="Build ChromaDB knowledge base")
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild from scratch")
    args = parser.parse_args()

    if args.reset and CHROMADB_DIR.exists():
        print("Resetting ChromaDB...")
        shutil.rmtree(CHROMADB_DIR)

    print("Building insurance knowledge base...\n")

    ef = get_embedding_function()
    client = get_client()

    total = 0
    total += build_acord_fields(client, ef)
    total += build_glossary(client, ef)
    total += build_naics(client, ef)
    total += build_form_structure(client, ef)
    total += build_state_info(client, ef)

    print(f"\nDone: {total} total documents indexed in ChromaDB")
    print(f"Database: {CHROMADB_DIR}")


if __name__ == "__main__":
    main()
