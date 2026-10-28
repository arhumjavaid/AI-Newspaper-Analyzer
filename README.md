# AI Newspaper Analyzer

Newspaper sentiment intelligence for PR teams. Upload a newspaper PDF. Gemini
reads the pages (including scans) and extracts every article about the client
(**K-Electric / KE**). Our own **NLP engine** then does the analysis: sentiment,
topics, tone, entities, key sentences and the executive summary. A dashboard
presents the results as PR intelligence: reputation index, share of voice, AVE,
topics, crisis alerts. Gemini's own sentiment is kept only as a **benchmark** the
engine is checked against.

```
PDF ─► extract (PyMuPDF) ─► Gemini: article extraction ─► NLP engine (ours) ─► metrics ─► dashboard
                              (OCR, boundaries, page,       sentiment, topics,
                               prominence) + benchmark      tone, NER, summary
```

## Stack
- **Backend:** FastAPI + PyMuPDF (hybrid text/scanned PDF extraction) + Gemini API
- **NLP engine:** NLTK + scikit-learn (classic pipeline, domain lexicons, trained sentiment model)
- **Frontend:** React (Vite) + Recharts
- **Storage:** JSON files (swap-point isolated in `backend/storage.py`)

## Setup

### 1. Add your Gemini API key
Copy `.env.example` to `.env` in the project root and paste your key:
```
GEMINI_API_KEY=...
MODEL=gemini-3.5-flash-lite
FALLBACK_MODEL=gemini-3.5-flash
```
(Get a key at https://aistudio.google.com/apikey — Flash-Lite is cheap and supports vision.)

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
2. **Extract articles with Gemini** (`pipeline/analyze.py`): the Jinja prompt in
   `prompts/client_context.j2` asks for every relevant article's text, headline, page
   and prominence (layout). A rule-based relevance guard (alias regexes + domain
   keywords, `services/targets.py`) drops false positives. Gemini also returns its own
   sentiment, which is stored per article under `llm` as a benchmark only.
3. **NLP engine** (`services/engine.py`, runs locally). For each article (headline + body):
   - **Classic pipeline** (`services/nlp.py`): cleaning, sentence/word tokenization,
     stopword removal, Porter stemming vs WordNet lemmatization, POS tagging, NER,
     bigrams, TF-IDF keywords (the day's articles are the corpus), extractive summary
   - **Sentiment** (`services/sentiment.py`): a logistic-regression model on TF-IDF of
     lemmas + bigrams, trained and evaluated by `evaluation/` and saved in
     `models/sentiment_engine.joblib`. Each prediction comes with the features that
     drove it.
   - **Target-dependent analysis:** the sentences that name the client (plus a
     rule-based coreference step: "The utility said…") give the key sentence, scored
     with a **domain-adapted VADER** (`services/lexicons.py`, where "fine" is negative
     and "load-shedding" exists)
   - **Topics and tone** from domain cue lexicons
   - **Entities** from NLTK NER, corrected by a Karachi gazetteer and place-name
     suffix rules
   - **Executive summary** generated from the metrics with templates (no LLM)
4. **Aggregate** (`pipeline/aggregate.py`): reputation index, sentiment distribution,
   share of voice, AVE estimate, topics and clusters, crisis alerts, and the
   engine-vs-Gemini comparison (agreement, correlation, confusion matrix). Articles
   where the engine and Gemini disagree, or the engine is unsure, are flagged
   **Needs review** for a human.
5. **Store** (`storage.py`): one JSON per upload + an index that powers the trend line.

## Evaluation
`backend/evaluation/` evaluates the engine on 89 real K-Electric news articles
(73 stories, 5 Pakistani outlets) with labelled sentiment, using nested grouped
cross-validation:

| Method | Accuracy | Macro F1 |
|---|---|---|
| Majority-class baseline | 0.371 | 0.180 |
| VADER, stock lexicon | 0.629 | 0.491 |
| VADER + domain lexicon + target sentences | 0.652 | 0.544 |
| Linear SVM, TF-IDF | 0.719 | 0.708 |
| **NLP engine (shipped): LogReg, TF-IDF** | **0.730** | **0.718** |
| Gemini (LLM benchmark, zero-shot) | 0.775 | 0.755 |

When the engine and Gemini agree, the engine is right 92% of the time. Their
disagreements, which are flagged for review, catch 19 of the engine's 24 errors.
The folder also has an ablation study and an error analysis
([ERROR_ANALYSIS.md](backend/evaluation/ERROR_ANALYSIS.md)). Labels are
AI-annotated (by Claude, not Gemini), not human. Method and caveats:
[backend/evaluation/README.md](backend/evaluation/README.md).

## Changing the client
Everything is in `.env` — `CLIENT_NAME`, `CLIENT_ALIASES`, `CLIENT_DESCRIPTION`.
No code change needed to monitor a different client.

## Testing without a key
```bash
cd backend
../.venv/bin/python make_sample_pdf.py   # creates sample_newspaper.pdf
../.venv/bin/python test_flow.py         # mocks Gemini, exercises extraction -> engine -> metrics
```

## API
| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | status + whether a key is configured |
| POST | `/api/upload` | upload a PDF, returns full analysis |
| GET  | `/api/uploads` | list past analyses |
| GET  | `/api/uploads/{id}` | one full analysis |
| GET  | `/api/trends` | reputation time series |
