"""FastAPI app: upload a newspaper PDF, analyse it, serve results to the dashboard."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import storage
from pipeline.aggregate import annotate_risk, build_metrics
from pipeline.analyze import AnalysisError, analyze_pages
from pipeline.extract import PageContent, extract_pages

app = FastAPI(title="AI Newspaper Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo: open. Lock down for production.
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "configured": config.is_configured(),
        "model": config.MODEL,
        "client": config.CLIENT_NAME,
    }


class TextInput(BaseModel):
    text: str
    source_name: str | None = None


def _analyze_and_store(pages: list[PageContent], source_name: str) -> dict:
    """Shared pipeline tail: analyse pages, aggregate, persist, return analysis."""
    try:
        result = analyze_pages(pages)
    except AnalysisError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    articles = annotate_risk(result["articles"])
    upload_id = uuid.uuid4().hex[:12]
    analysis = {
        "id": upload_id,
        "filename": source_name,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "publication_name": result.get("publication_name"),
        "publication_date": result.get("publication_date"),
        "executive_summary": result.get("executive_summary"),
        "model": result.get("model"),
        "page_count": len(pages),
        "pages_as_image": sum(1 for p in pages if p.kind == "image"),
        "filtered_out": result.get("filtered_out", 0),
        "articles": articles,
        "metrics": build_metrics(articles),
    }
    storage.save_upload(upload_id, analysis)
    return analysis


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        pages = extract_pages(pdf_bytes)
    except Exception as exc:  # noqa: BLE001 — surface any PDF parse failure
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {exc}")

    if not pages:
        raise HTTPException(status_code=400, detail="No readable pages found in PDF.")

    return _analyze_and_store(pages, file.filename)


@app.post("/api/analyze-text")
def analyze_text(body: TextInput) -> dict:
    """Analyse pasted article text directly — no PDF needed."""
    text = (body.text or "").strip()
    if len(text) < 40:
        raise HTTPException(
            status_code=400,
            detail="Please paste at least a few sentences of article text.",
        )
    pages = [PageContent(page_number=1, kind="text", text=text)]
    source_name = (body.source_name or "").strip() or "Pasted text"
    return _analyze_and_store(pages, source_name)


@app.get("/api/uploads")
def list_uploads() -> list[dict]:
    return storage.list_uploads()


@app.get("/api/uploads/{upload_id}")
def get_upload(upload_id: str) -> dict:
    data = storage.get_upload(upload_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return data


@app.delete("/api/uploads/{upload_id}")
def delete_upload(upload_id: str) -> dict:
    if not storage.delete_upload(upload_id):
        raise HTTPException(status_code=404, detail="Upload not found.")
    return {"status": "deleted", "id": upload_id}


@app.get("/api/trends")
def trends() -> list[dict]:
    return storage.get_trends()
