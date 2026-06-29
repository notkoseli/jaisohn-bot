import os
import uuid
import chromadb
from chromadb.utils import embedding_functions
import anthropic

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = "jaisohn_documents"
TOP_K = 6

SYSTEM_PROMPT = """You are the official AI assistant for the Philip Jaisohn Memorial Foundation. \
You help visitors, researchers, and community members learn about Dr. Philip Jaisohn (서재필, \
Seo Jae-pil), a pioneering Korean-American independence activist, physician, journalist, and \
democratic reformer who lived from 1864 to 1951.

You answer questions accurately and respectfully, drawing on the provided source documents. \
When the answer is found in the documents, cite the relevant detail. When information is not \
available in your context, say so honestly rather than speculating.

Speak warmly and accessibly — you serve museum visitors, students, and scholars alike. \
Keep answers concise unless the user asks for more depth."""


def _get_collection():
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_context(query: str, n_results: int = TOP_K) -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        return []
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist < 1.0:  # cosine distance filter
            chunks.append({"text": doc, "source": meta.get("source", "unknown"), "distance": dist})
    return chunks


def chat(messages: list[dict]) -> str:
    user_query = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    chunks = retrieve_context(user_query)

    context_block = ""
    if chunks:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Source {i}: {chunk['source']}]\n{chunk['text']}")
        context_block = "\n\n---\n\n".join(context_parts)

    system = SYSTEM_PROMPT
    if context_block:
        system += (
            "\n\n## Relevant source material\n\n"
            + context_block
            + "\n\n## End of source material\n\n"
            "Use the source material above to inform your answer."
        )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def list_sources() -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        return []
    result = collection.get(include=["metadatas"])
    seen = {}
    for meta in result["metadatas"]:
        source = meta.get("source", "unknown")
        doc_id = meta.get("doc_id", "")
        if doc_id and doc_id not in seen:
            seen[doc_id] = {
                "doc_id": doc_id,
                "source": source,
                "chunk_count": 0,
            }
        if doc_id in seen:
            seen[doc_id]["chunk_count"] += 1
    return list(seen.values())


def delete_document(doc_id: str) -> int:
    collection = _get_collection()
    result = collection.get(where={"doc_id": doc_id})
    ids = result["ids"]
    if ids:
        collection.delete(ids=ids)
    return len(ids)
