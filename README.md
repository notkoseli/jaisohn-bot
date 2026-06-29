# Philip Jaisohn AI Chatbot

An AI-powered chatbot for the Philip Jaisohn Memorial Foundation that answers questions about Dr. Philip Jaisohn's life, history, and legacy. Built with a RAG (Retrieval-Augmented Generation) pipeline so you can feed it documents and the chatbot answers from them accurately.

## Features

- **Chat interface** — conversational Q&A about Philip Jaisohn
- **Document ingestion** — upload PDFs, Word docs, and text files via drag-and-drop
- **Knowledge base management** — view and remove indexed documents
- **RAG pipeline** — answers are grounded in your uploaded source material
- **Claude AI** — powered by Anthropic's Claude Haiku model

## Prerequisites — API Keys

You need three API keys (all have free tiers):

| Service | Purpose | Sign up |
|---|---|---|
| **Anthropic** | Claude AI responses | console.anthropic.com |
| **Voyage AI** | Document embeddings | dash.voyageai.com |
| **Pinecone** | Vector database | app.pinecone.io |

## Deployment (Vercel)

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) → **New Project** → import the repo
3. Under **Environment Variables**, add:
   - `ANTHROPIC_API_KEY`
   - `VOYAGE_API_KEY`
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX_NAME` = `jaisohn`
4. Click **Deploy**

The Pinecone index is created automatically on first document upload.

## Deployment (Railway / Render)

`Dockerfile`, `railway.json`, and `render.yaml` are also included if you prefer those platforms. No code changes needed — just add the same three environment variables.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in all three API keys in .env

python app.py
# Open http://localhost:5000
```

## Adding Documents

### Via the web UI (easiest)
1. Click **Documents** in the sidebar
2. Drag and drop files onto the upload zone, or click to browse
3. Supported formats: **PDF, DOCX, DOC, TXT, MD**

### Via the command line (bulk ingestion)
```bash
python ingest.py documents/          # ingest entire folder
python ingest.py path/to/file.pdf   # single file
```

## How It Works

1. **Ingestion** — documents are chunked and embedded via Voyage AI's `voyage-3` model, then stored in Pinecone
2. **Retrieval** — the user's question is embedded and the closest chunks are retrieved from Pinecone using cosine similarity
3. **Generation** — retrieved chunks are injected into Claude's context and it generates a grounded answer

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Anthropic API key |
| `VOYAGE_API_KEY` | yes | Voyage AI API key for embeddings |
| `PINECONE_API_KEY` | yes | Pinecone API key |
| `PINECONE_INDEX_NAME` | yes (default: `jaisohn`) | Pinecone index name |
| `PORT` | no (default: `5000`) | Server port |
| `FLASK_DEBUG` | no (default: `false`) | Enable debug mode |
