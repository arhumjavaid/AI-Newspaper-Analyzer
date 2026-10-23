"""Turn raw per-article analysis into the sellable PR metrics shown on the dashboard.

Computes: Reputation Index (0-100), sentiment distribution, Share of Voice,
AVE (Advertising Value Equivalent) estimate, top topics, and crisis alerts.
"""
from __future__ import annotations

from collections import Counter

from config import (
    AVE_BASE_USD,
    AVE_PROMINENCE_MULTIPLIER,
    CLIENT_ALIASES,
    CLIENT_NAME,
)

# How much each prominence level weights an article when scoring reputation.
_PROMINENCE_WEIGHT = {
    "front_page": 3.0,
    "prominent": 2.0,
    "standard": 1.0,
    "minor": 0.5,
}


def _reputation_index(articles: list[dict]) -> int:
    """Prominence-weighted average sentiment mapped from [-100,100] to [0,100]."""
    if not articles:
        return 50  # neutral baseline when there is no coverage
    total_w = 0.0
    acc = 0.0
    for a in articles:
        w = _PROMINENCE_WEIGHT.get(a["prominence"], 1.0)
        acc += a["sentiment_score"] * w
        total_w += w
    avg = acc / total_w if total_w else 0.0
    return round((avg + 100) / 2)


def _sentiment_distribution(articles: list[dict]) -> dict[str, int]:
    dist = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    for a in articles:
        dist[a["sentiment_label"]] = dist.get(a["sentiment_label"], 0) + 1
    return dist


def _share_of_voice(articles: list[dict]) -> list[dict]:
    """Mentions of the client vs other named entities across all articles."""
    counter: Counter[str] = Counter()
    client_lower = {CLIENT_NAME.lower(), *(a.lower() for a in CLIENT_ALIASES)}
    client_mentions = 0
    for a in articles:
        client_mentions += 1  # every article here is about the client
        for ent in a["entities"]:
            if ent.lower() in client_lower:
                continue
            counter[ent] += 1
    rows = [{"name": CLIENT_NAME, "mentions": client_mentions, "is_client": True}]
    for name, count in counter.most_common(6):
        rows.append({"name": name, "mentions": count, "is_client": False})
    return rows


def _ave_estimate(articles: list[dict]) -> float:
    total = 0.0
    for a in articles:
        total += AVE_BASE_USD * AVE_PROMINENCE_MULTIPLIER.get(a["prominence"], 1.0)
    return round(total, 2)


def _top_topics(articles: list[dict], limit: int = 8) -> list[dict]:
    counter: Counter[str] = Counter()
    for a in articles:
        for t in a["topics"]:
            counter[t.lower()] += 1
    return [{"topic": t, "count": c} for t, c in counter.most_common(limit)]


def risk_level(article: dict) -> str:
    """Four-tier PR risk classification used for badges and filtering.

    critical → negative AND high-prominence (or very low score): needs response.
    negative → unfavourable but not urgent.
    watch    → neutral or mixed coverage worth monitoring.
    positive → favourable coverage.
    """
    label = article.get("sentiment_label", "neutral")
    if label == "negative":
        if article.get("prominence") in ("front_page", "prominent") or article.get(
            "sentiment_score", 0
        ) <= -50:
            return "critical"
        return "negative"
    if label == "positive":
        return "positive"
    return "watch"


def annotate_risk(articles: list[dict]) -> list[dict]:
    """Attach a `risk_level` to each article in place; return the same list."""
    for a in articles:
        a["risk_level"] = risk_level(a)
    return articles


def _risk_distribution(articles: list[dict]) -> dict[str, int]:
    dist = {"critical": 0, "negative": 0, "watch": 0, "positive": 0}
    for a in articles:
        dist[risk_level(a)] += 1
    return dist


def _entity_insights(articles: list[dict], limit: int = 8) -> dict[str, list[dict]]:
    """Aggregate named people / locations / organisations across all articles."""
    buckets = {"people": Counter(), "locations": Counter(), "organisations": Counter()}
    for a in articles:
        for key in buckets:
            for name in a.get(key, []) or []:
                buckets[key][name] += 1
    return {
        key: [{"name": n, "count": c} for n, c in counter.most_common(limit)]
        for key, counter in buckets.items()
    }


def _crisis_alerts(articles: list[dict]) -> list[dict]:
    """Negative + high-prominence articles needing an urgent response."""
    alerts = []
    for a in articles:
        if a["sentiment_label"] == "negative" and (
            a["prominence"] in ("front_page", "prominent") or a["sentiment_score"] <= -50
        ):
            alerts.append(
                {
                    "headline": a["headline"],
                    "page": a["page"],
                    "prominence": a["prominence"],
                    "sentiment_score": a["sentiment_score"],
                    "tone_tags": a["tone_tags"],
                    "key_quote": a["key_quote"],
                    "suggested_response": a["suggested_response"],
                }
            )
    # Most damaging first.
    return sorted(alerts, key=lambda x: x["sentiment_score"])


def build_metrics(articles: list[dict]) -> dict:
    return {
        "reputation_index": _reputation_index(articles),
        "sentiment_distribution": _sentiment_distribution(articles),
        "share_of_voice": _share_of_voice(articles),
        "ave_estimate_usd": _ave_estimate(articles),
        "top_topics": _top_topics(articles),
        "risk_distribution": _risk_distribution(articles),
        "entity_insights": _entity_insights(articles),
        "crisis_alerts": _crisis_alerts(articles),
        "average_sentiment": (
            round(sum(a["sentiment_score"] for a in articles) / len(articles))
            if articles
            else 0
        ),
    }
