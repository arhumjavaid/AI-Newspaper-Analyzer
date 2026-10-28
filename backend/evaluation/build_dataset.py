"""Clean the scraped articles and attach gold labels -> dataset.jsonl.

Usage (from backend/):  python evaluation/build_dataset.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from labels import LABELS

HERE = Path(__file__).resolve().parent
MIN_WORDS = 60

# Site boilerplate that the scraper's <p> filter lets through.
_BOILERPLATE = [
    re.compile(r"^Subscribing is the best way to get our best stories immediately\.\s*"),
    re.compile(r"\s*See more ProPakistani stories.*$", re.S),
]


def clean(body: str) -> str:
    for pat in _BOILERPLATE:
        body = pat.sub("", body)
    return body.strip()


def main() -> None:
    rows = [json.loads(line) for line in (HERE / "articles_raw.jsonl").open(encoding="utf-8")]
    rows = [r for r in rows if len(r["body"].split()) >= MIN_WORDS]
    if len(rows) != len(LABELS):
        raise SystemExit(f"{len(rows)} articles but {len(LABELS)} labels")

    with (HERE / "dataset.jsonl").open("w", encoding="utf-8") as out:
        for idx, r in enumerate(rows):
            label, group, reason = LABELS[idx]
            out.write(
                json.dumps(
                    {
                        "id": idx,
                        "url": r["url"],
                        "source": r["url"].split("/")[2].replace("www.", ""),
                        "headline": r["headline"],
                        "body": clean(r["body"]),
                        "label": label,
                        "group": group,
                        "label_reason": reason,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    counts = {l: sum(1 for v in LABELS.values() if v[0] == l) for l in ("positive", "neutral", "negative")}
    print(f"wrote {len(rows)} articles, {len({v[1] for v in LABELS.values()})} stories: {counts}")


if __name__ == "__main__":
    main()
