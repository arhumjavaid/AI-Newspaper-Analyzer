# AI Newspaper Analyzer

Newspaper sentiment intelligence for PR teams. Upload a
newspaper PDF; an LLM (via OpenRouter) finds every article mentioning the client
(**K-Electric / KE**), scores sentiment & tone, and a dashboard presents it as PR
intelligence: reputation index, share of voice, AVE, topics, and crisis alerts.

## Stack
- **Backend:** FastAPI + PyMuPDF (hybrid text/scanned PDF extraction) + OpenRouter
- **Frontend:** React (Vite) + Recharts
- **Storage:** JSON files (swap-point isolated in `backend/storage.py`)

## Setup

### 1. Add your OpenRouter key
Edit `.env` in the project root and paste your key:
```
OPENROUTER_API_KEY=sk-or-...
MODEL=google/gemini-2.0-flash-001
```
(Get a key at https://openrouter.ai/keys — Gemini Flash is cheap and supports vision.)

### 2. Backend
```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Open http://localhost:5173 and drop in a newspaper PDF.

## How it works
1. **Extract** (`pipeline/extract.py`): per page, use selectable text if present;
   otherwise render the page to an image for the vision model. (No poppler needed.)
2. **Analyze** (`pipeline/analyze.py`): the Jinja prompt in `prompts/client_context.j2`
   injects the client context + a strict JSON schema; OpenRouter returns one record
   per relevant article (sentiment score/label, tone tags, prominence, key quote,
   entities, topics, suggested response).
3. **Aggregate** (`pipeline/aggregate.py`): reputation index, sentiment distribution,
   share of voice, AVE estimate, top topics, crisis alerts.
4. **Store** (`storage.py`): one JSON per upload + an index that powers the trend line.

## Changing the client
Everything is in `.env` — `CLIENT_NAME`, `CLIENT_ALIASES`, `CLIENT_DESCRIPTION`.
No code change needed to monitor a different client.

## Testing without a key
```bash
cd backend
../.venv/bin/python make_sample_pdf.py   # creates sample_newspaper.pdf
../.venv/bin/python test_flow.py         # mocks the LLM, exercises the full flow
```

## API
| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | status + whether a key is configured |
| POST | `/api/upload` | upload a PDF, returns full analysis |
| GET  | `/api/uploads` | list past analyses |
| GET  | `/api/uploads/{id}` | one full analysis |
| GET  | `/api/trends` | reputation time series |
