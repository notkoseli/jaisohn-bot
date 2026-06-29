"""
Document ingestion pipeline. Supports PDF, DOCX, and plain text files.
Usage:
    python ingest.py path/to/document.pdf
    python ingest.py documents/            # ingest entire folder
"""

import os
import sys
import uuid
import textwrap
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = "jaisohn_documents"
CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 150     # overlap between chunks


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


def _chunk_text(text: str, source: str) -> list[str]:
    text = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _extract_pdf(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


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


def ingest_file(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    if ext not in EXTRACTORS:
        return {"status": "skipped", "reason": f"Unsupported file type: {ext}", "path": path}

    try:
        text = EXTRACTORS[ext](path)
    except Exception as e:
        return {"status": "error", "reason": str(e), "path": path}

    if not text.strip():
        return {"status": "skipped", "reason": "Empty document", "path": path}

    source_name = os.path.basename(path)
    chunks = _chunk_text(text, source_name)
    doc_id = str(uuid.uuid4())

    collection = _get_collection()
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": source_name, "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]

    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    return {"status": "ok", "source": source_name, "doc_id": doc_id, "chunks": len(chunks)}


def ingest_path(path: str) -> list[dict]:
    results = []
    if os.path.isdir(path):
        for fname in sorted(os.listdir(path)):
            fpath = os.path.join(path, fname)
            if os.path.isfile(fpath):
                r = ingest_file(fpath)
                results.append(r)
                print(f"  {r['status'].upper():8s} {fname}" + (f" ({r.get('chunks', '')} chunks)" if r["status"] == "ok" else f" — {r.get('reason', '')}"))
    elif os.path.isfile(path):
        r = ingest_file(path)
        results.append(r)
        print(f"  {r['status'].upper():8s} {os.path.basename(path)}" + (f" ({r.get('chunks', '')} chunks)" if r["status"] == "ok" else f" — {r.get('reason', '')}"))
    else:
        print(f"Path not found: {path}", file=sys.stderr)
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for arg in sys.argv[1:]:
        print(f"\nIngesting: {arg}")
        ingest_path(arg)
    print("\nDone.")
