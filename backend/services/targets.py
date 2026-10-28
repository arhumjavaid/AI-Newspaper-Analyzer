"""Finding the client in text: alias matching and target-sentence selection.

Target-dependent sentiment needs the sentences that are actually ABOUT the client,
not the whole article (a story can be gloomy overall yet praise the client, or the
reverse). We take every sentence that names the client, plus the sentence right
after it when that one refers back to the client ("The utility said...", "It
added..."), a light rule-based stand-in for coreference resolution.
"""
from __future__ import annotations

import re

import config


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


ALIAS_PATTERNS = _build_alias_patterns()

# Sentence openers that point back to the client mentioned just before.
_COREF = re.compile(
    r"^\W*(it|its|the (power )?(utility|company|firm|power company|power supply company)|"
    r"the spokesperson|(the |a )?spokes(man|person|woman)|he|she)\b",
    re.IGNORECASE,
)


def mentions_client(text: str) -> bool:
    return any(p.search(text or "") for p in ALIAS_PATTERNS)


def target_sentence_ids(sentences: list[str]) -> list[int]:
    """Indices of sentences about the client (named, or referring back to it)."""
    ids: list[int] = []
    for i, s in enumerate(sentences):
        if mentions_client(s):
            ids.append(i)
        elif ids and ids[-1] == i - 1 and _COREF.match(s):
            ids.append(i)
    return ids
