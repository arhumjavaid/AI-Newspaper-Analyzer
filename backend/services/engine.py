"""The NLP engine: turns extracted articles into the analysis the dashboard shows.

Gemini's job ends at extraction (article text, headline, page, prominence). Every
analytical field below is produced here by our own pipeline:

  sentiment_label / score / confidence  <- services.sentiment (trained model)
  topics, clusters                      <- topic lexicon
  tone_tags                             <- tone cue lexicon
  key_quote                             <- most polar sentence about the client
  summary                               <- extractive summary (services.nlp)
  people / locations / organisations    <- NLTK NER + gazetteer correction
  relevance                             <- alias matching (services.targets)
  executive_summary                     <- template text generated from the metrics

Gemini's own judgements are kept under article["llm"] only as a benchmark.
"""
from __future__ import annotations

import re
from collections import Counter

from nltk.corpus import wordnet

import config
from services import nlp, sentiment
from services.lexicons import (
    GAZETTEER_LOCATIONS,
    GAZETTEER_ORGANISATIONS,
    LOCATION_SUFFIXES,
    TONE_CUES,
    TOPIC_CUES,
)
from services.targets import mentions_client

# Fields Gemini returns that are analysis rather than extraction.
_LLM_FIELDS = (
    "sentiment_label", "sentiment_score", "confidence", "tone_tags", "topics", "summary",
    "key_quote", "people", "locations", "organisations", "entities", "relevance",
)
_CLIENT_NAMES = {config.CLIENT_NAME.lower(), *(a.lower() for a in config.CLIENT_ALIASES)}
# Everything happens in Karachi; listing the city itself as an "affected area" is noise.
_TOO_BROAD = {"karachi", "pakistan"}


def _gazetteer_pattern(name: str) -> re.Pattern:
    # Single tokens ("SITE", "Hub") are case-sensitive so ordinary words don't match.
    flags = re.IGNORECASE if " " in name or "-" in name else 0
    return re.compile(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", flags)


_GAZ_LOC = [(n, _gazetteer_pattern(n)) for n in GAZETTEER_LOCATIONS]
_GAZ_ORG = [(n, _gazetteer_pattern(n)) for n in GAZETTEER_ORGANISATIONS]
_GAZ_LOC_LOWER = {n.lower() for n in GAZETTEER_LOCATIONS}
_GAZ_ORG_LOWER = {n.lower() for n in GAZETTEER_ORGANISATIONS}


def _dedupe(names: list[str]) -> list[str]:
    seen, out = set(), []
    for n in names:
        key = n.lower()
        if key not in seen and len(n) > 1:
            seen.add(key)
            out.append(n)
    return out


def _common_word(name: str) -> bool:
    """A single capitalised dictionary word ("Power" opening a headline), not a name.

    NLTK's chunker leans on capitalisation, so sentence-initial common nouns become
    false entities. Real names here (Lyari, NEPRA, Munir) are not WordNet words.
    """
    return " " not in name and "-" not in name and bool(wordnet.synsets(name.lower()))


def entities(text: str, ner: dict[str, list[str]]) -> dict[str, list[str]]:
    """NLTK NER output, corrected and extended with the gazetteer."""
    known = _GAZ_LOC_LOWER | _GAZ_ORG_LOWER
    ner = {k: [n for n in v if n.lower() in known or not _common_word(n)] for k, v in ner.items()}
    people = list(ner.get("people", []))
    locations = [n for n, p in _GAZ_LOC if p.search(text)]
    orgs = [n for n, p in _GAZ_ORG if p.search(text)]
    # Re-file NLTK entities the gazetteer knows better (e.g. "Karachi" tagged ORGANIZATION).
    for bucket in ("locations", "organisations"):
        for name in ner.get(bucket, []):
            low = name.lower()
            if low in _GAZ_LOC_LOWER or low.endswith(LOCATION_SUFFIXES):
                locations.append(name)
            elif low in _GAZ_ORG_LOWER:
                orgs.append(name)
            elif bucket == "locations":
                locations.append(name)
            else:
                orgs.append(name)
    locations += [p for p in people if p.lower().endswith(LOCATION_SUFFIXES)]
    people = [
        p for p in people
        if p.lower() not in _GAZ_LOC_LOWER | _GAZ_ORG_LOWER and not p.lower().endswith(LOCATION_SUFFIXES)
    ]
    return {
        "people": _dedupe([p for p in people if p.lower() not in _CLIENT_NAMES]),
        "locations": _dedupe([l for l in locations if l.lower() not in _TOO_BROAD]),
        "organisations": _dedupe([o for o in orgs if o.lower() not in _CLIENT_NAMES]),
    }


def _cue_hits(text: str, cues: dict[str, list[str]]) -> Counter:
    low = f" {text.lower()} "
    return Counter({name: sum(low.count(c) for c in words) for name, words in cues.items()})


def topics(text: str, limit: int = 3) -> list[str]:
    hits = _cue_hits(text, TOPIC_CUES)
    return [t for t, n in hits.most_common(limit) if n > 0]


def tones(text: str) -> list[str]:
    hits = _cue_hits(text, TONE_CUES)
    found = [t for t, n in hits.most_common() if n > 0]
    return found or ["factual"]


def key_sentence(feats: dict) -> str:
    """The sentence about the client with the strongest (domain) VADER polarity."""
    sents = feats["sentences"]
    pool = [sents[i] for i in feats["target_ids"]] or sents
    if not pool:
        return ""
    dv = sentiment.domain_vader()
    return max(pool, key=lambda s: abs(dv.polarity_scores(s)["compound"]))


def analyze_article(a: dict) -> tuple[dict, list[str]]:
    """Run the engine on one article in place. Returns (article, its TF-IDF terms)."""
    a["llm"] = {k: a.get(k) for k in _LLM_FIELDS}
    body, source = nlp.article_source_text(a)
    # The headline carries the paper's framing ("KE admits...", "KE grilled..."), so it
    # is part of the analysed text, the same input the Gemini benchmark sees.
    headline = (a.get("headline") or "").strip()
    text = f"{headline}. {body}" if headline and source == "body" else body
    result, sent_lemmas = nlp.analyze_text(text)
    feats = sentiment.featurize(text, sent_lemmas)
    pred = sentiment.predict(feats)
    full_text = text

    result["source"] = source
    result["engine"] = {
        **pred,
        "target_sentences": len(feats["target_ids"]),
        "target_vader": feats["lex_domain_target"][0],
    }
    ents = entities(text, result["entities"])
    a.update(
        {
            "sentiment_label": pred["label"],
            "sentiment_score": pred["score"],
            "confidence": pred["confidence"],
            "topics": topics(full_text),
            "tone_tags": tones(text),
            "key_quote": key_sentence(feats),
            "summary": result["extractive_summary"],
            **ents,
            "entities": _dedupe(ents["organisations"] + ents["people"]),
            "relevance": "explicit" if mentions_client(full_text) else "implicit",
            "nlp": result,
        }
    )
    a["clusters"] = a["topics"]
    return a, nlp.terms(sent_lemmas)


def analyze_articles(articles: list[dict]) -> list[dict]:
    """Run the engine on every article, then TF-IDF keywords across the day's articles."""
    docs = [analyze_article(a)[1] for a in articles]
    for a, keywords in zip(articles, nlp.tfidf_keywords(docs)):
        a["nlp"]["keywords"] = keywords
    return articles


# --- Executive summary (template-based text generation) ---------------------------------

def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def executive_summary(articles: list[dict], metrics: dict) -> str | None:
    """A 2-3 sentence briefing written from the computed metrics, not by an LLM."""
    if not articles:
        return None
    n = len(articles)
    dist = metrics["sentiment_distribution"]
    rep = metrics["reputation_index"]
    tenor = "favourable" if rep >= 66 else "mixed" if rep >= 40 else "unfavourable"
    parts = []
    for label in ("negative", "positive", "neutral"):
        if dist.get(label):
            parts.append(f"{dist[label]} {label}")
    noun = "article" if n == 1 else "articles"
    s1 = f"Today's coverage of {config.CLIENT_NAME} is {tenor} overall ({n} {noun}: {_join(parts)}; reputation index {rep}/100)."

    topic_counts = Counter(t for a in articles for t in a.get("topics", []))
    s2 = ""
    if topic_counts:
        s2 = f" The main themes are {_join([t for t, _ in topic_counts.most_common(3)])}."

    alerts = metrics.get("crisis_alerts", [])
    if alerts:
        worst = alerts[0]
        where = (worst.get("prominence") or "").replace("_", " ")
        more = f", one of {len(alerts)} items needing an urgent response" if len(alerts) > 1 else ""
        s3 = f" Most damaging: “{worst['headline']}” ({where}{more})."
    else:
        best = max(articles, key=lambda a: a["sentiment_score"])
        s3 = f" No item needs an urgent response; the most favourable is “{best['headline']}”." if best["sentiment_score"] > 0 else " No item needs an urgent response."
    return s1 + s2 + s3


def info() -> dict:
    return sentiment.info()
