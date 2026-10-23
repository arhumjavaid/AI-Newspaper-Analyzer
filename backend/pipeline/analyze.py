"""Call the Gemini API (Vertex AI) with the extracted pages and parse a structured result.

Builds the analyst prompt from the Jinja template (client context + output
schema), sends text pages as text and scanned pages as images, and returns the
parsed JSON (publication metadata + list of article dicts).
"""
from __future__ import annotations

import json
import re
import time

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

import config
from pipeline.extract import PageContent

_PROMPTS_DIR = config.BASE_DIR / "prompts"
_env = Environment(
    loader=FileSystemLoader(_PROMPTS_DIR),
    autoescape=select_autoescape(enabled_extensions=()),
)

_ALLOWED_TONES = {"taunt", "sarcasm", "alarmist", "accusatory", "praise", "factual"}
_ALLOWED_LABELS = {"positive", "negative", "neutral", "mixed"}
_ALLOWED_PROMINENCE = {"front_page", "prominent", "standard", "minor"}


def _build_alias_patterns() -> list[re.Pattern]:
    """Word-boundary matchers for each client alias.

    Short aliases (e.g. "KE") are matched case-sensitively so they don't fire on
    substrings like 'marKEt'; longer aliases are case-insensitive.
    """
    patterns = []
    aliases = {config.CLIENT_NAME, *config.CLIENT_ALIASES}
    for alias in aliases:
        alias = alias.strip()
        if not alias:
            continue
        # strip a trailing "(...)" e.g. "K-Electric (KE)" -> "K-Electric"
        core = re.sub(r"\s*\(.*?\)\s*", "", alias).strip() or alias
        body = re.escape(core)
        pat = rf"(?<![A-Za-z]){body}(?![A-Za-z])"
        flags = 0 if len(core) <= 3 else re.IGNORECASE
        patterns.append(re.compile(pat, flags))
    return patterns


_ALIAS_PATTERNS = _build_alias_patterns()


# Keywords that mark the client's electricity domain. Used to validate "implicit"
# relevance so unrelated-domain stories (water/gas/roads) can't slip through.
_DOMAIN_KEYWORDS = re.compile(
    r"electric|power|load[\s-]?shed|tariff|\bgrid\b|feeder|outage|\bkesc\b|"
    r"power\s*supply|kilowatt|megawatt|\bmw\b|transformer|powerhouse|"
    r"electricity\s*bill|power\s*break",
    re.IGNORECASE,
)


def _entity_strings(article: dict) -> list[str]:
    """All named-entity strings across typed and legacy flat fields."""
    out: list[str] = []
    for key in ("entities", "people", "locations", "organisations"):
        out.extend(article.get(key, []) or [])
    return out


def _article_text(article: dict) -> str:
    return " ".join(
        [
            article.get("headline", ""),
            article.get("client_mention", ""),
            article.get("summary", ""),
            article.get("key_quote", ""),
            " ".join(_entity_strings(article)),
            " ".join(article.get("topics", []) or []),
        ]
    )


def _mentions_client(article: dict) -> bool:
    """True if any client alias appears in the article's textual fields."""
    haystack = _article_text(article)
    return any(p.search(haystack) for p in _ALIAS_PATTERNS)


def _is_electricity_domain(article: dict) -> bool:
    """True if the article clearly concerns the client's electricity domain."""
    return bool(_DOMAIN_KEYWORDS.search(_article_text(article)))


def _is_relevant(article: dict) -> bool:
    """Relevance guard.

    - explicit (client named): keep.
    - implicit (unnamed): keep only if it really is about electricity, so
      water/gas/road stories misclassified as implicit are still excluded.
    """
    if article.get("relevance") == "explicit" or _mentions_client(article):
        return True
    return article.get("relevance") == "implicit" and _is_electricity_domain(article)


class AnalysisError(RuntimeError):
    pass


def _render_system_prompt() -> str:
    template = _env.get_template("client_context.j2")
    return template.render(
        client_name=config.CLIENT_NAME,
        client_aliases=config.CLIENT_ALIASES,
        client_description=config.CLIENT_DESCRIPTION,
    )


def _build_user_parts(pages: list[PageContent]) -> list[dict]:
    """Vertex AI parts array: text parts for text pages, inlineData for scans."""
    parts: list[dict] = [
        {
            "text": (
                "Here are the newspaper pages. Analyse them per your instructions "
                "and return ONLY the JSON object."
            )
        }
    ]
    for page in pages:
        if page.kind == "text":
            parts.append(
                {"text": f"\n===== PAGE {page.page_number} (text) =====\n{page.text}"}
            )
        else:
            parts.append({"text": f"\n===== PAGE {page.page_number} (image) ====="})
            parts.append(
                {
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": page.image_b64,
                    }
                }
            )
    return parts


def _extract_json(raw: str) -> dict:
    """Parse model output, tolerating stray markdown fences or prose."""
    raw = raw.strip()
    # Strip ```json ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last resort: grab the outermost {...}.
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise AnalysisError("Model did not return valid JSON.")


def _clean_str_list(value) -> list[str]:
    """Trim, drop blanks, and de-duplicate (case-insensitive) a list of strings."""
    out: list[str] = []
    seen: set[str] = set()
    for item in value or []:
        s = str(item).strip()
        if not s or s.lower() in seen:
            continue
        seen.add(s.lower())
        out.append(s)
    return out


def _clean_articles(articles: list) -> list[dict]:
    """Normalise/validate fields so downstream code can trust the shape."""
    cleaned: list[dict] = []
    for a in articles or []:
        if not isinstance(a, dict):
            continue
        label = str(a.get("sentiment_label", "neutral")).lower()
        if label not in _ALLOWED_LABELS:
            label = "neutral"
        prominence = str(a.get("prominence", "standard")).lower()
        if prominence not in _ALLOWED_PROMINENCE:
            prominence = "standard"
        try:
            score = int(round(float(a.get("sentiment_score", 0))))
        except (TypeError, ValueError):
            score = 0
        score = max(-100, min(100, score))
        tones = [t for t in (a.get("tone_tags") or []) if t in _ALLOWED_TONES]
        try:
            confidence = float(a.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))
        relevance = str(a.get("relevance", "")).lower()
        if relevance not in {"explicit", "implicit"}:
            relevance = "explicit" if _mentions_client(a) else "implicit"

        people = _clean_str_list(a.get("people"))
        locations = _clean_str_list(a.get("locations"))
        organisations = _clean_str_list(a.get("organisations"))
        # Legacy flat list (for Share of Voice): orgs + people, plus any raw
        # "entities" the model still emits, excluding the client itself.
        client_lower = {config.CLIENT_NAME.lower(), *(x.lower() for x in config.CLIENT_ALIASES)}
        entities = [
            e
            for e in _clean_str_list(
                organisations + people + (a.get("entities") or [])
            )
            if e.lower() not in client_lower
        ]

        cleaned.append(
            {
                "headline": str(a.get("headline", "Untitled")).strip(),
                "relevance": relevance,
                "client_mention": (a.get("client_mention") or "").strip(),
                "summary": str(a.get("summary", "")).strip(),
                "page": a.get("page"),
                "prominence": prominence,
                "sentiment_label": label,
                "sentiment_score": score,
                "tone_tags": tones,
                "key_quote": (a.get("key_quote") or "").strip(),
                "people": people,
                "locations": locations,
                "organisations": organisations,
                "entities": entities,
                "topics": [str(t).strip() for t in (a.get("topics") or []) if t],
                "confidence": round(confidence, 2),
                "suggested_response": (a.get("suggested_response") or None),
            }
        )
    return cleaned


_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Status codes worth retrying / failing over: rate limit + transient server errors
# (503 = "model is currently experiencing high demand").
_RETRYABLE = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3  # per model, before moving on to the backup


def _call_model(client: httpx.Client, model: str, payload: dict) -> httpx.Response:
    """POST to one model, retrying with backoff on transient errors.

    Returns the final response (caller inspects status_code). Only retries the
    same model on _RETRYABLE codes; any other status returns immediately.
    """
    url = f"{_GEMINI_BASE}/{model}:generateContent?key={config.GEMINI_API_KEY}"
    resp = None
    for attempt in range(_MAX_ATTEMPTS):
        resp = client.post(
            url, headers={"Content-Type": "application/json"}, json=payload
        )
        if resp.status_code == 200 or resp.status_code not in _RETRYABLE:
            return resp
        if attempt < _MAX_ATTEMPTS - 1:
            time.sleep(min(2 ** attempt, 8))  # 1s, 2s
    return resp


def analyze_pages(pages: list[PageContent]) -> dict:
    """Run the LLM analysis. Returns {publication_name, publication_date, articles}."""
    if not config.is_configured():
        raise AnalysisError(
            "GEMINI_API_KEY is not set. Add it to .env to run analysis."
        )

    payload = {
        "systemInstruction": {"parts": [{"text": _render_system_prompt()}]},
        "contents": [
            {"role": "user", "parts": _build_user_parts(pages)}
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    # Try the primary model first; on a transient/overload error, fail over to the
    # backup model so a demand spike doesn't break the request.
    models = [config.MODEL]
    if config.FALLBACK_MODEL and config.FALLBACK_MODEL != config.MODEL:
        models.append(config.FALLBACK_MODEL)

    resp = None
    used_model = config.MODEL
    try:
        with httpx.Client(timeout=180.0) as client:
            for model in models:
                resp = _call_model(client, model, payload)
                used_model = model
                if resp.status_code == 200:
                    break
                # Only fall back to the next model on transient/overload errors;
                # a 4xx (bad request, invalid key) won't be fixed by switching.
                if resp.status_code not in _RETRYABLE:
                    break
    except httpx.HTTPError as exc:
        raise AnalysisError(f"Network error calling Gemini API: {exc}") from exc

    if resp.status_code != 200:
        raise AnalysisError(
            f"Gemini API returned {resp.status_code}: {resp.text[:500]}"
        )

    data = resp.json()
    try:
        raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise AnalysisError(f"Unexpected Gemini API response: {data}") from exc

    parsed = _extract_json(raw_content)
    cleaned = _clean_articles(parsed.get("articles", []))
    # Relevance guard: keep explicit client mentions plus genuine electricity-domain
    # coverage (implicit), while excluding unrelated-domain false positives
    # (e.g. a water-crisis story misattributed to the client).
    relevant = [a for a in cleaned if _is_relevant(a)]
    summary = (parsed.get("executive_summary") or "").strip() or None
    if not relevant:
        # Don't let a stale summary describe coverage we filtered out.
        summary = None
    return {
        "publication_name": parsed.get("publication_name"),
        "publication_date": parsed.get("publication_date"),
        "executive_summary": summary,
        "articles": relevant,
        "filtered_out": len(cleaned) - len(relevant),
        "model": used_model,
    }
