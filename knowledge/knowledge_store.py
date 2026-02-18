"""
Insurance Knowledge Store — retrieval interface for the RAG system.

Provides semantic search across all knowledge collections (ACORD fields,
insurance glossary, NAICS codes, form structure, state info).

Used by both the Streamlit chatbot and the extraction pipeline.

Usage:
    from knowledge.knowledge_store import InsuranceKnowledgeStore

    store = InsuranceKnowledgeStore()
    results = store.query("what is bodily injury coverage")
    context = store.format_context(results)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from knowledge.constants import (
    ALL_COLLECTIONS,
    CHROMADB_DIR,
    COLLECTION_ACORD_FIELDS,
    COLLECTION_CUSTOM_DOCS,
    COLLECTION_FORM_STRUCTURE,
    COLLECTION_GLOSSARY,
    COLLECTION_NAICS,
    COLLECTION_STATE_INFO,
    EMBEDDING_MODEL,
)


class InsuranceKnowledgeStore:
    """Semantic search across insurance knowledge collections."""

    def __init__(self, db_path: Optional[Path] = None):
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        self._db_path = db_path or CHROMADB_DIR
        self._ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
        self._client = chromadb.PersistentClient(path=str(self._db_path))
        self._collections = {}

    def _get_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name, embedding_function=self._ef
            )
        return self._collections[name]

    def query(
        self,
        text: str,
        collection: Optional[str] = None,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        Search a specific collection.

        Args:
            text: Query text
            collection: Collection name (default: glossary)
            n_results: Number of results
            where: Optional metadata filter (e.g., {"form_type": "125"})

        Returns:
            List of {id, document, metadata, distance} dicts
        """
        col_name = collection or COLLECTION_GLOSSARY
        col = self._get_collection(col_name)

        kwargs: dict[str, Any] = {
            "query_texts": [text],
            "n_results": min(n_results, col.count() or 1),
        }
        if where:
            kwargs["where"] = where

        results = col.query(**kwargs)
        return self._parse_results(results)

    def query_all(
        self,
        text: str,
        n_results: int = 3,
        collections: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Search across all (or specified) collections and merge results.

        Args:
            text: Query text
            n_results: Results per collection
            collections: Which collections to search (default: all)

        Returns:
            List of results sorted by relevance (distance)
        """
        targets = collections or ALL_COLLECTIONS
        all_results = []
        for col_name in targets:
            try:
                results = self.query(text, collection=col_name, n_results=n_results)
                all_results.extend(results)
            except Exception:
                continue

        # Sort by distance (lower = more relevant)
        all_results.sort(key=lambda r: r.get("distance", 999))
        return all_results

    def get_field_info(self, field_name: str) -> Optional[dict]:
        """Direct lookup for a specific ACORD field by exact name."""
        col = self._get_collection(COLLECTION_ACORD_FIELDS)
        try:
            result = col.get(
                where={"field_name": field_name},
                limit=1,
            )
            if result and result["ids"]:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
        except Exception:
            pass
        return None

    def get_glossary_term(self, term: str) -> Optional[dict]:
        """Search for an insurance term in the glossary."""
        results = self.query(term, collection=COLLECTION_GLOSSARY, n_results=1)
        return results[0] if results else None

    def get_naics_description(self, code: str) -> Optional[dict]:
        """Look up a NAICS code description."""
        col = self._get_collection(COLLECTION_NAICS)
        # Try exact metadata match first
        try:
            result = col.get(
                where={"code": str(code)},
                limit=1,
            )
            if result and result["ids"]:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
        except Exception:
            pass
        # Fallback: semantic search
        results = self.query(f"NAICS code {code}", collection=COLLECTION_NAICS, n_results=1)
        return results[0] if results else None

    def get_state_info(self, state_code: str) -> Optional[dict]:
        """Look up state insurance information."""
        col = self._get_collection(COLLECTION_STATE_INFO)
        try:
            result = col.get(
                ids=[f"state_{state_code.upper()}"],
                limit=1,
            )
            if result and result["ids"]:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
        except Exception:
            pass
        return None

    def get_form_info(self, form_type: str) -> list[dict]:
        """Get all structure info for a specific form type."""
        return self.query(
            f"ACORD {form_type}",
            collection=COLLECTION_FORM_STRUCTURE,
            n_results=10,
            where={"form_type": form_type},
        )

    def format_context(self, results: list[dict], max_chars: int = 3000) -> str:
        """Format search results into a context string for LLM prompt injection."""
        if not results:
            return ""

        lines = ["Relevant knowledge:"]
        total_chars = 0
        for r in results:
            doc = r.get("document", "")
            data_type = r.get("metadata", {}).get("data_type", "")
            prefix = {
                "field": "ACORD Field",
                "glossary": "Insurance Term",
                "abbreviation": "Abbreviation",
                "naics": "Industry Code",
                "form_structure": "Form Info",
                "state": "State Info",
            }.get(data_type, "Info")

            line = f"- [{prefix}] {doc}"
            if total_chars + len(line) > max_chars:
                break
            lines.append(line)
            total_chars += len(line)

        return "\n".join(lines)

    # ==================================================================
    # Document upload / management
    # ==================================================================

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict],
        collection: str = COLLECTION_CUSTOM_DOCS,
        ids: Optional[list[str]] = None,
    ) -> int:
        """Add documents to a collection. Returns count added."""
        import hashlib
        import time as _time

        col = self._get_collection(collection)
        if ids is None:
            ids = [
                f"upload_{hashlib.md5((t + str(_time.time()) + str(i)).encode()).hexdigest()[:12]}"
                for i, t in enumerate(texts)
            ]
        col.upsert(ids=ids, documents=texts, metadatas=metadatas)
        return len(texts)

    def delete_documents(self, ids: list[str], collection: str = COLLECTION_CUSTOM_DOCS) -> int:
        """Delete documents by ID. Returns count deleted."""
        col = self._get_collection(collection)
        col.delete(ids=ids)
        return len(ids)

    def list_custom_documents(self, n: int = 100) -> list[dict]:
        """List all documents in the custom_documents collection."""
        col = self._get_collection(COLLECTION_CUSTOM_DOCS)
        count = col.count()
        if count == 0:
            return []
        result = col.get(limit=min(n, count), include=["documents", "metadatas"])
        docs = []
        for i, id_ in enumerate(result["ids"]):
            docs.append({
                "id": id_,
                "document": result["documents"][i] if result["documents"] else "",
                "metadata": result["metadatas"][i] if result["metadatas"] else {},
            })
        return docs

    def collection_stats(self) -> dict[str, int]:
        """Return document counts per collection."""
        stats = {}
        for name in ALL_COLLECTIONS:
            try:
                col = self._get_collection(name)
                stats[name] = col.count()
            except Exception:
                stats[name] = 0
        return stats

    @staticmethod
    def _parse_results(results: dict) -> list[dict]:
        """Parse ChromaDB query results into a flat list of dicts."""
        parsed = []
        if not results or not results.get("ids"):
            return parsed

        ids = results["ids"][0] if results["ids"] else []
        docs = results["documents"][0] if results.get("documents") else []
        metas = results["metadatas"][0] if results.get("metadatas") else []
        dists = results["distances"][0] if results.get("distances") else []

        for i, id_ in enumerate(ids):
            parsed.append({
                "id": id_,
                "document": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else 999,
            })
        return parsed
