"""
Document loader for uploading files to the insurance knowledge base.

Supports: PDF, TXT, MD, JSON, CSV
Extracts text → chunks → adds to ChromaDB custom_documents collection.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional

from knowledge.constants import COLLECTION_CUSTOM_DOCS


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from uploaded file bytes."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n\n".join(pages)

    if ext in (".txt", ".md"):
        return file_bytes.decode("utf-8", errors="replace")

    if ext == ".json":
        data = json.loads(file_bytes.decode("utf-8", errors="replace"))
        return json.dumps(data, indent=2, ensure_ascii=False)

    if ext == ".csv":
        text = file_bytes.decode("utf-8", errors="replace")
        return text

    raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at sentence/paragraph boundary
        if end < len(text):
            for sep in ("\n\n", "\n", ". ", ", ", " "):
                last = chunk.rfind(sep)
                if last > chunk_size // 2:
                    chunk = chunk[: last + len(sep)]
                    end = start + len(chunk)
                    break

        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks


def process_upload(
    file_bytes: bytes,
    filename: str,
    store,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Full upload pipeline: extract text → chunk → add to ChromaDB.

    Args:
        file_bytes: Raw file content
        filename: Original filename (used for type detection)
        store: InsuranceKnowledgeStore instance
        metadata: Optional extra metadata (source, tags, etc.)

    Returns:
        {"chunks": int, "chars": int, "filename": str}
    """
    text = extract_text(file_bytes, filename)
    if not text.strip():
        return {"chunks": 0, "chars": 0, "filename": filename}

    chunks = chunk_text(text)
    if not chunks:
        return {"chunks": 0, "chars": len(text), "filename": filename}

    # Build metadata for each chunk
    base_meta = {
        "data_type": "custom",
        "source_file": filename,
        "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if metadata:
        base_meta.update(metadata)

    metadatas = []
    ids = []
    file_hash = hashlib.md5(file_bytes).hexdigest()[:8]
    for i, chunk in enumerate(chunks):
        chunk_meta = {**base_meta, "chunk_index": i, "total_chunks": len(chunks)}
        metadatas.append(chunk_meta)
        ids.append(f"upload_{file_hash}_{i}")

    store.add_documents(
        texts=chunks,
        metadatas=metadatas,
        collection=COLLECTION_CUSTOM_DOCS,
        ids=ids,
    )

    return {"chunks": len(chunks), "chars": len(text), "filename": filename}
