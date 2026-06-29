import os
import voyageai
from pinecone import Pinecone
import anthropic

PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME", "jaisohn")
VOYAGE_MODEL = "voyage-3"
TOP_K = 6
CHUNKS_NS = "chunks"
MANIFEST_NS = "manifest"

SYSTEM_PROMPT = """You are the official AI assistant for the Philip Jaisohn Memorial Foundation. \
You help visitors, researchers, and community members learn about Dr. Philip Jaisohn (서재필, \
Seo Jae-pil), a pioneering Korean-American independence activist, physician, journalist, and \
democratic reformer who lived from 1864 to 1951.

You answer questions accurately and respectfully, drawing on the provided source documents. \
When the answer is found in the documents, cite the relevant detail. When information is not \
available in your context, say so honestly rather than speculating.

Speak warmly and accessibly — you serve museum visitors, students, and scholars alike. \
Keep answers concise unless the user asks for more depth."""


def _index():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    return pc.Index(PINECONE_INDEX)


def _embed_query(text: str) -> list[float]:
    vo = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    return vo.embed([text], model=VOYAGE_MODEL, input_type="query").embeddings[0]


def retrieve_context(query: str) -> list[dict]:
    try:
        vector = _embed_query(query)
        results = _index().query(
            vector=vector,
            top_k=TOP_K,
            namespace=CHUNKS_NS,
            include_metadata=True,
        )
        chunks = []
        for match in results.matches:
            if match.score > 0.3:
                chunks.append({
                    "text": match.metadata.get("text", ""),
                    "source": match.metadata.get("source", "unknown"),
                    "score": match.score,
                })
        return chunks
    except Exception:
        return []


def chat(messages: list[dict]) -> str:
    user_query = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    chunks = retrieve_context(user_query)

    system = SYSTEM_PROMPT
    if chunks:
        parts = [f"[Source {i}: {c['source']}]\n{c['text']}" for i, c in enumerate(chunks, 1)]
        system += (
            "\n\n## Relevant source material\n\n"
            + "\n\n---\n\n".join(parts)
            + "\n\n## End of source material\n\nUse the source material above to inform your answer."
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
    try:
        idx = _index()
        docs = {}
        for id_batch in idx.list(namespace=MANIFEST_NS):
            fetched = idx.fetch(ids=id_batch, namespace=MANIFEST_NS)
            for vec_id, vec in fetched.vectors.items():
                meta = vec.metadata
                doc_id = meta.get("doc_id", vec_id)
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "source": meta.get("source", "unknown"),
                    "chunk_count": int(meta.get("chunk_count", 0)),
                }
        return list(docs.values())
    except Exception:
        return []


def delete_document(doc_id: str) -> int:
    idx = _index()
    # Delete all chunk vectors
    chunk_ids = []
    for id_batch in idx.list(prefix=f"{doc_id}_", namespace=CHUNKS_NS):
        chunk_ids.extend(id_batch)
    if chunk_ids:
        idx.delete(ids=chunk_ids, namespace=CHUNKS_NS)
    # Delete manifest entry
    idx.delete(ids=[doc_id], namespace=MANIFEST_NS)
    return len(chunk_ids)
