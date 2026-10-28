"""Run the app's real Gemini pipeline on every evaluation article and cache the output.

Each article is sent exactly as the /api/analyze-text endpoint would send it, so this
measures the production prompt, model, cleaning and relevance guard together.
Results are cached in llm_predictions.json; re-running only fills in missing ids.

Usage (from backend/):  python evaluation/run_llm.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from pipeline.analyze import AnalysisError, analyze_pages  # noqa: E402
from pipeline.extract import PageContent  # noqa: E402

CACHE = HERE / "llm_predictions.json"


def main() -> None:
    rows = [json.loads(line) for line in (HERE / "dataset.jsonl").open(encoding="utf-8")]
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    for r in rows:
        key = str(r["id"])
        if key in cache and "error" not in cache[key]:
            continue
        page = PageContent(page_number=1, kind="text", text=f"{r['headline']}\n\n{r['body']}")
        try:
            result = analyze_pages([page])
        except AnalysisError as exc:
            cache[key] = {"error": str(exc)[:300]}
            print(f"[{key}] ERROR {str(exc)[:120]}")
        else:
            arts = result["articles"]
            # One article in, so normally one out; if the model splits it, keep the
            # most confident record.
            best = max(arts, key=lambda a: a["confidence"]) if arts else None
            cache[key] = {
                "label": best["sentiment_label"] if best else "not_detected",
                "score": best["sentiment_score"] if best else None,
                "confidence": best["confidence"] if best else None,
                "relevance": best["relevance"] if best else None,
                "n_articles": len(arts),
                "model": result["model"],
            }
            print(f"[{key}] {cache[key]['label']:>12}  gold={r['label']}")
        CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        time.sleep(1)  # stay well under the free-tier rate limit

    errors = sum(1 for v in cache.values() if "error" in v)
    print(f"done: {len(cache)} cached, {errors} errors")


if __name__ == "__main__":
    main()
