# Philip Jaisohn AI Chatbot

An AI-powered chatbot for the Philip Jaisohn Memorial Foundation that answers questions about Dr. Philip Jaisohn's life, history, and legacy. Built with a RAG (Retrieval-Augmented Generation) pipeline so you can feed it documents and the chatbot answers from them accurately.

## Features

- **Chat interface** — conversational Q&A about Philip Jaisohn
- **Document ingestion** — upload PDFs, Word docs, and text files via drag-and-drop
- **Knowledge base management** — view and remove indexed documents
- **RAG pipeline** — answers are grounded in your uploaded source material
- **Claude AI** — powered by Anthropic's Claude Haiku model

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

Get an API key at https://console.anthropic.com

### 3. Run the app

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## Adding Documents

### Via the web UI (easiest)
1. Click **Documents** in the sidebar
2. Drag and drop files onto the upload zone, or click to browse
3. Supported formats: **PDF, DOCX, DOC, TXT, MD**

### Via the command line (bulk ingestion)
```bash
# Single file
python ingest.py path/to/document.pdf

# Entire folder
python ingest.py documents/
```

Drop your documents into the `documents/` folder and run the command above to index them all at once.

## How It Works

1. **Ingestion** — documents are split into overlapping text chunks and embedded using `sentence-transformers/all-MiniLM-L6-v2`
2. **Retrieval** — when a user asks a question, the most relevant chunks are retrieved from ChromaDB using semantic similarity search
3. **Generation** — retrieved context is injected into the system prompt and Claude generates a grounded answer

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *required* | Your Anthropic API key |
| `PORT` | `5000` | Port to run the server on |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `CHROMA_PATH` | `./chroma_db` | Path to store the vector database |
