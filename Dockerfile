# ── Stage 1: build the React frontend ──────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: combined nginx + FastAPI runtime ───────────────────────────────
FROM python:3.12-slim

# System deps: nginx + supervisord to manage both processes
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# NLTK corpora (tokenizer, stopwords, WordNet, POS tagger, NER chunker, VADER)
RUN python -m nltk.downloader -d /app/backend/nltk_data \
    punkt_tab stopwords wordnet omw-1.4 averaged_perceptron_tagger_eng \
    maxent_ne_chunker_tab words vader_lexicon

# Copy backend source
COPY backend/ /app/backend/

# Copy built frontend into nginx root
COPY --from=build /app/dist /usr/share/nginx/html

# nginx config (proxy /api/ → uvicorn on 8000, serve SPA otherwise)
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

# supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

WORKDIR /app/backend
EXPOSE 8080
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
