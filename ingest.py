"""
Document ingestion pipeline. Supports PDF, DOCX, and plain text files.
Usage:
    python ingest.py path/to/document.pdf
    python ingest.py documents/            # ingest entire folder
"""

import os
import sys
import uuid
import voyageai
from pinecone import Pinecone, ServerlessSpec

PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME", "jaisohn")
VOYAGE_MODEL = "voyage-3"
EMBEDDING_DIM = 1024
CHUNKS_NS = "chunks"
MANIFEST_NS = "manifest"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
EMBED_BATCH = 96   # Voyage AI max batch size


def _get_index():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    existing = [i.name for i in pc.list_indexes()]
    if PINECONE_INDEX not in existing:
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"  Created Pinecone index '{PINECONE_INDEX}'")
    return pc.Index(PINECONE_INDEX)


def _embed(texts: list[str]) -> list[list[float]]:
    vo = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    all_embeddings = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        result = vo.embed(batch, model=VOYAGE_MODEL, input_type="document")
        all_embeddings.extend(result.embeddings)
    return all_embeddings


def _chunk_text(text: str) -> list[str]:
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        chunk = text[start:start + CHUNK_SIZE]
        if chunk.strip():
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _extract_pdf(path: str) -> str:
    from pypdf import PdfReader
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def _extract_docx(path: str) -> str:
    from docx import Document
    return "\n".join(p.text for p in Document(path).paragraphs)


def _extract_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".doc": _extract_docx,
    ".txt": _extract_txt,
    ".md": _extract_txt,
}


def ingest_file(path: str, original_name: str | None = None) -> dict:
    ext = os.path.splitext(path)[1].lower()
    if ext not in EXTRACTORS:
        return {"status": "skipped", "reason": f"Unsupported file type: {ext}", "path": path}

    try:
        text = EXTRACTORS[ext](path)
    except Exception as e:
        return {"status": "error", "reason": str(e), "path": path}

    if not text.strip():
        return {"status": "skipped", "reason": "Empty document", "path": path}

    source_name = original_name or os.path.basename(path)
    chunks = _chunk_text(text)
    doc_id = str(uuid.uuid4())

    embeddings = _embed(chunks)
    idx = _get_index()

    # Upsert chunks
    vectors = [
        {
            "id": f"{doc_id}_{i}",
            "values": emb,
            "metadata": {"text": chunk, "source": source_name, "doc_id": doc_id, "chunk_index": i},
        }
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ]
    # Upsert in batches of 100
    for i in range(0, len(vectors), 100):
        idx.upsert(vectors=vectors[i:i+100], namespace=CHUNKS_NS)

    # Upsert manifest entry (embed the filename for a valid vector)
    manifest_emb = _embed([source_name])[0]
    idx.upsert(
        vectors=[{
            "id": doc_id,
            "values": manifest_emb,
            "metadata": {"doc_id": doc_id, "source": source_name, "chunk_count": len(chunks)},
        }],
        namespace=MANIFEST_NS,
    )

    return {"status": "ok", "source": source_name, "doc_id": doc_id, "chunks": len(chunks)}


def ingest_path(path: str) -> list[dict]:
    results = []
    if os.path.isdir(path):
        for fname in sorted(os.listdir(path)):
            fpath = os.path.join(path, fname)
            if os.path.isfile(fpath):
                r = ingest_file(fpath)
                results.append(r)
                _print_result(r, fname)
    elif os.path.isfile(path):
        r = ingest_file(path)
        results.append(r)
        _print_result(r, os.path.basename(path))
    else:
        print(f"Path not found: {path}", file=sys.stderr)
    return results


def _print_result(r: dict, fname: str):
    suffix = f" ({r.get('chunks', '')} chunks)" if r["status"] == "ok" else f" — {r.get('reason', '')}"
    print(f"  {r['status'].upper():8s} {fname}{suffix}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    from dotenv import load_dotenv
    load_dotenv()
    for arg in sys.argv[1:]:
        print(f"\nIngesting: {arg}")
        ingest_path(arg)
    print("\nDone.")
