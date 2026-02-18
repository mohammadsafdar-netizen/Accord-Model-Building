"""
Chat engine for the Insurance Knowledge Bot.

Handles prompt building, RAG context injection, and LLM streaming via Ollama.
"""

from __future__ import annotations

from typing import Any, Generator, Optional

import ollama

from knowledge.constants import OLLAMA_MODEL
from knowledge.knowledge_store import InsuranceKnowledgeStore

SYSTEM_PROMPT = """You are an expert insurance assistant for agents and underwriters.
You help with ACORD form filling, coverage questions, underwriting guidance, and insurance terminology.
Use the provided knowledge context to give accurate, specific answers.
If the context doesn't contain enough information, say so honestly.
Keep answers concise and professional. Use industry terminology appropriately."""


def build_prompt(
    query: str,
    context: str,
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Build messages list for Ollama chat API."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add context as a system message if available
    if context:
        messages.append({
            "role": "system",
            "content": f"Use this knowledge to answer:\n{context}",
        })

    # Add conversation history (last 10 messages)
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current query
    messages.append({"role": "user", "content": query})
    return messages


def generate_response_streaming(
    query: str,
    knowledge_store: Optional[InsuranceKnowledgeStore] = None,
    use_rag: bool = True,
    n_results: int = 5,
    temperature: float = 0.3,
    chat_history: Optional[list[dict[str, str]]] = None,
    model: str = OLLAMA_MODEL,
    collections: Optional[list[str]] = None,
) -> Generator[str, None, None]:
    """
    Generate a streaming response using RAG + Ollama.

    Args:
        query: User's question
        knowledge_store: InsuranceKnowledgeStore instance
        use_rag: Whether to retrieve context
        n_results: Number of RAG results per collection
        temperature: LLM temperature
        chat_history: Previous conversation messages
        model: Ollama model name
        collections: Which collections to search (None = all)

    Yields:
        Response text chunks
    """
    history = chat_history or []
    context = ""

    # RAG retrieval
    if use_rag and knowledge_store:
        results = knowledge_store.query_all(
            query, n_results=n_results, collections=collections
        )
        context = knowledge_store.format_context(results, max_chars=3000)

    # Build prompt
    messages = build_prompt(query, context, history)

    # Stream from Ollama
    try:
        stream = ollama.chat(
            model=model,
            messages=messages,
            stream=True,
            options={"temperature": temperature},
        )
        for chunk in stream:
            if isinstance(chunk, dict) and "message" in chunk:
                content = chunk["message"].get("content", "")
                if content:
                    yield content
    except Exception as e:
        yield f"Error communicating with Ollama: {e}"


def generate_response(
    query: str,
    knowledge_store: Optional[InsuranceKnowledgeStore] = None,
    use_rag: bool = True,
    n_results: int = 5,
    temperature: float = 0.3,
    chat_history: Optional[list[dict[str, str]]] = None,
    model: str = OLLAMA_MODEL,
) -> str:
    """Non-streaming version — returns full response as string."""
    chunks = list(generate_response_streaming(
        query=query,
        knowledge_store=knowledge_store,
        use_rag=use_rag,
        n_results=n_results,
        temperature=temperature,
        chat_history=chat_history,
        model=model,
    ))
    return "".join(chunks)
