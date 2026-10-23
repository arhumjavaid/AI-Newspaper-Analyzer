"""JSON-file storage layer.

This is the single swap-point for persistence. The rest of the app calls these
functions and never touches the filesystem directly, so moving to SQLite/Postgres
later means rewriting only this module.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import INDEX_FILE, UPLOADS_DIR


def _ensure_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("[]", encoding="utf-8")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def save_upload(upload_id: str, analysis: dict) -> None:
    """Persist one newspaper's full analysis and append its summary to the index."""
    _ensure_dirs()
    (UPLOADS_DIR / f"{upload_id}.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = {
        "id": upload_id,
        "filename": analysis.get("filename"),
        "uploaded_at": analysis.get("uploaded_at"),
        "publication_date": analysis.get("publication_date"),
        "reputation_index": analysis.get("metrics", {}).get("reputation_index"),
        "article_count": len(analysis.get("articles", [])),
        "sentiment_distribution": analysis.get("metrics", {}).get(
            "sentiment_distribution", {}
        ),
        "crisis_count": len(analysis.get("metrics", {}).get("crisis_alerts", [])),
    }

    index = _read_json(INDEX_FILE, [])
    index = [row for row in index if row.get("id") != upload_id]  # de-dupe
    index.append(summary)
    INDEX_FILE.write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def list_uploads() -> list[dict]:
    """All upload summaries, newest first."""
    _ensure_dirs()
    index = _read_json(INDEX_FILE, [])
    return sorted(index, key=lambda r: r.get("uploaded_at", ""), reverse=True)


def delete_upload(upload_id: str) -> bool:
    """Remove one upload's analysis file and its index entry. Returns True if it existed."""
    _ensure_dirs()
    path = UPLOADS_DIR / f"{upload_id}.json"
    existed = path.exists()
    if existed:
        path.unlink()

    index = _read_json(INDEX_FILE, [])
    new_index = [row for row in index if row.get("id") != upload_id]
    if len(new_index) != len(index):
        existed = True
        INDEX_FILE.write_text(
            json.dumps(new_index, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return existed


def get_upload(upload_id: str) -> dict | None:
    """Full analysis for one upload, or None if missing."""
    path = UPLOADS_DIR / f"{upload_id}.json"
    if not path.exists():
        return None
    return _read_json(path, None)


def get_trends() -> list[dict]:
    """Time series (oldest first) for the dashboard trend line."""
    index = _read_json(INDEX_FILE, [])
    rows = [
        {
            "id": r.get("id"),
            "date": r.get("publication_date") or r.get("uploaded_at"),
            "reputation_index": r.get("reputation_index"),
            "sentiment_distribution": r.get("sentiment_distribution", {}),
            "article_count": r.get("article_count", 0),
        }
        for r in index
    ]
    return sorted(rows, key=lambda r: r.get("date") or "")
