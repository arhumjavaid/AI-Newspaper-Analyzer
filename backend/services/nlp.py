"""Classic NLP pass over each article, run locally with NLTK + scikit-learn.

The LLM finds the articles and returns their body text; this module then applies
the basic NLP pipeline to that text so the analysis is not a black box:

  cleaning -> sentence/word tokenization -> stopword removal -> stemming and
  lemmatization -> POS tagging -> named-entity recognition -> VADER lexicon
  sentiment -> n-grams -> TF-IDF keywords -> frequency-based extractive summary.

services/engine.py runs this on every article and builds the dashboard's analysis
from it; the results are attached to each article under the "nlp" key.
"""
from __future__ import annotations

import re
from collections import Counter

import nltk
from nltk.chunk import ne_chunker
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.stem import PorterStemmer, WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer

from config import BASE_DIR

# Corpora live inside the project so the app works offline once downloaded.
_NLTK_DIR = BASE_DIR / "nltk_data"
_NLTK_RESOURCES = {
    "tokenizers/punkt_tab": "punkt_tab",
    "corpora/stopwords": "stopwords",
    "corpora/wordnet": "wordnet",
    "corpora/omw-1.4": "omw-1.4",
    "taggers/averaged_perceptron_tagger_eng": "averaged_perceptron_tagger_eng",
    "chunkers/maxent_ne_chunker_tab": "maxent_ne_chunker_tab",
    "corpora/words": "words",
    "sentiment/vader_lexicon.zip": "vader_lexicon",
}

# Newspaper filler words that carry no meaning for keywords.
_EXTRA_STOPWORDS = {"said", "says", "also", "would", "could", "mr", "ms", "per", "one"}

# VADER compound thresholds recommended by its authors.
_VADER_POS = 0.05
_VADER_NEG = -0.05

# A "word": letters, optionally hyphenated (keeps "load-shedding", "k-electric").
_WORD = re.compile(r"[a-z]+(?:-[a-z]+)*")

_ready = False
_stopwords: set[str] = set()
_stemmer = PorterStemmer()
_lemmatizer = WordNetLemmatizer()
_vader: SentimentIntensityAnalyzer | None = None
# nltk.ne_chunk() reloads the MaxEnt model from disk on every call, so keep one.
_ne_chunker = None


def _ensure_ready() -> None:
    """Point NLTK at the project data dir and download anything missing (once)."""
    global _ready, _stopwords, _vader, _ne_chunker
    if _ready:
        return
    _NLTK_DIR.mkdir(parents=True, exist_ok=True)
    if str(_NLTK_DIR) not in nltk.data.path:
        nltk.data.path.insert(0, str(_NLTK_DIR))
    for path, package in _NLTK_RESOURCES.items():
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(package, download_dir=str(_NLTK_DIR), quiet=True)
    _stopwords = set(stopwords.words("english")) | _EXTRA_STOPWORDS
    _vader = SentimentIntensityAnalyzer()
    _ne_chunker = ne_chunker()
    _ready = True


# --- 1. Cleaning ----------------------------------------------------------------

def clean_text(text: str) -> str:
    """Repair line-break hyphenation, drop the dateline and collapse whitespace.

    Case is kept because the POS tagger and NER rely on capitalisation.
    """
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text or "")  # "elec-\ntricity"
    text = re.sub(r"^\s*[A-Z][A-Z .]{2,30}[.:\-—]+\s+", "", text)  # "KARACHI: "
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# --- 2-4. Tokenization, stopwords, stemming, lemmatization -----------------------

def _wordnet_pos(tag: str) -> str:
    """Map a Penn Treebank tag to the WordNet POS the lemmatizer expects."""
    if tag.startswith("J"):
        return "a"
    if tag.startswith("V"):
        return "v"
    if tag.startswith("R"):
        return "r"
    return "n"


def _content_lemmas(tagged: list[tuple[str, str]]) -> list[str]:
    """Lowercased, alphabetic, non-stopword tokens reduced to their lemma."""
    out = []
    for word, tag in tagged:
        w = word.lower()
        if not _WORD.fullmatch(w) or len(w) < 2 or w in _stopwords:
            continue
        out.append(_lemmatizer.lemmatize(w, _wordnet_pos(tag)))
    return out


# --- 5. POS tagging ----------------------------------------------------------------

def _coarse_pos(tag: str) -> str:
    if tag.startswith("NN"):
        return "NOUN"
    if tag.startswith("VB"):
        return "VERB"
    if tag.startswith("JJ"):
        return "ADJ"
    if tag.startswith("RB"):
        return "ADV"
    if tag in ("PRP", "PRP$", "WP", "WP$"):
        return "PRON"
    return "OTHER"


# --- 6. Named-entity recognition -----------------------------------------------------

_NE_BUCKETS = {
    "PERSON": "people",
    "GPE": "locations",
    "LOCATION": "locations",
    "FACILITY": "locations",
    "ORGANIZATION": "organisations",
}


def _named_entities(tagged_sents: list[list[tuple[str, str]]]) -> dict[str, list[str]]:
    found: dict[str, Counter] = {b: Counter() for b in set(_NE_BUCKETS.values())}
    for tagged in tagged_sents:
        for node in _ne_chunker.parse(tagged):
            if hasattr(node, "label") and node.label() in _NE_BUCKETS:
                name = " ".join(word for word, _ in node.leaves())
                found[_NE_BUCKETS[node.label()]][name] += 1
    return {bucket: [n for n, _ in c.most_common(8)] for bucket, c in found.items()}


# --- 7. Lexicon sentiment ------------------------------------------------------------

def vader_sentiment(text: str) -> dict:
    """VADER polarity, with the compound score also mapped to the app's -100..100 scale."""
    _ensure_ready()
    scores = _vader.polarity_scores(text)
    compound = scores["compound"]
    if compound >= _VADER_POS:
        label = "positive"
    elif compound <= _VADER_NEG:
        label = "negative"
    else:
        label = "neutral"
    return {
        "label": label,
        "compound": round(compound, 3),
        "score": round(compound * 100),
        "pos": round(scores["pos"], 3),
        "neg": round(scores["neg"], 3),
        "neu": round(scores["neu"], 3),
    }


# --- 8. N-grams ----------------------------------------------------------------------

def _bigrams(sent_lemmas: list[list[str]]) -> list[str]:
    """Adjacent content-word pairs, never spanning a sentence boundary."""
    return [" ".join(bg) for lemmas in sent_lemmas for bg in nltk.ngrams(lemmas, 2)]


def _top_bigrams(sent_lemmas: list[list[str]], limit: int = 5) -> list[dict]:
    counts = Counter(_bigrams(sent_lemmas))
    return [{"phrase": p, "count": c} for p, c in counts.most_common(limit) if c >= 2]


# --- 9. TF-IDF keywords ----------------------------------------------------------------

def terms(sent_lemmas: list[list[str]]) -> list[str]:
    """Unigrams + bigrams used as TF-IDF features."""
    return [l for lemmas in sent_lemmas for l in lemmas] + _bigrams(sent_lemmas)


def identity(doc: list[str]) -> list[str]:
    """TF-IDF analyzer for already-tokenised input (module-level so joblib can pickle it)."""
    return doc


def tfidf_keywords(docs: list[list[str]], limit: int = 6) -> list[list[dict]]:
    """Top TF-IDF terms per document, with the day's articles as the corpus."""
    if not any(docs):
        return [[] for _ in docs]
    vectorizer = TfidfVectorizer(analyzer=identity, sublinear_tf=True)
    matrix = vectorizer.fit_transform(docs)
    vocab = vectorizer.get_feature_names_out()
    out = []
    for row in matrix:
        row = row.toarray()[0]
        top = row.argsort()[::-1][:limit]
        out.append(
            [{"term": vocab[i], "score": round(float(row[i]), 3)} for i in top if row[i] > 0]
        )
    return out


# --- 10. Extractive summary --------------------------------------------------------------

def _extractive_summary(
    sentences: list[str], sent_lemmas: list[list[str]], n: int = 2
) -> str:
    """Pick the n sentences whose words are most frequent in the article."""
    if len(sentences) <= n:
        return " ".join(sentences)
    freq = Counter(l for lemmas in sent_lemmas for l in lemmas)
    if not freq:
        return " ".join(sentences[:n])
    top = max(freq.values())
    scored = []
    for i, lemmas in enumerate(sent_lemmas):
        if len(lemmas) < 4:  # skip fragments / bylines
            continue
        score = sum(freq[l] / top for l in lemmas) / len(lemmas) ** 0.5
        scored.append((score, i))
    best = sorted(i for _, i in sorted(scored, reverse=True)[:n])
    return " ".join(sentences[i] for i in best) or " ".join(sentences[:n])


# --- Pipeline ------------------------------------------------------------------------------

def article_source_text(article: dict) -> tuple[str, str]:
    """The text to analyse: the article body, else headline + summary."""
    body = (article.get("body") or "").strip()
    if body:
        return body, "body"
    fallback = ". ".join(
        s for s in (article.get("headline", ""), article.get("summary", "")) if s
    )
    return fallback, "summary"


def analyze_text(text: str) -> tuple[dict, list[list[str]]]:
    """Run steps 1-8 and 10 on one text. Returns (nlp result, per-sentence lemmas)."""
    _ensure_ready()
    text = clean_text(text)
    sentences = nltk.sent_tokenize(text)
    tokenized = [nltk.word_tokenize(s) for s in sentences]
    tagged_sents = [nltk.pos_tag(toks) for toks in tokenized]

    words = [w for toks in tokenized for w in toks if _WORD.fullmatch(w.lower())]
    sent_lemmas = [_content_lemmas(tagged) for tagged in tagged_sents]
    lemmas = [l for sl in sent_lemmas for l in sl]
    content_words = [w for w in words if w.lower() not in _stopwords and len(w) > 1]

    pos_counts = Counter(_coarse_pos(tag) for tagged in tagged_sents for _, tag in tagged)
    # Stem vs lemma side by side for the first few content words (a teaching aid).
    word_forms: list[dict] = []
    seen: set[str] = set()
    for word, tag in (pair for tagged in tagged_sents for pair in tagged):
        w = word.lower()
        if not _WORD.fullmatch(w) or len(w) < 2 or w in _stopwords or w in seen:
            continue
        seen.add(w)
        word_forms.append(
            {
                "word": w,
                "pos": tag,
                "stem": _stemmer.stem(w),
                "lemma": _lemmatizer.lemmatize(w, _wordnet_pos(tag)),
            }
        )
        if len(word_forms) == 8:
            break

    result = {
        "stats": {
            "sentences": len(sentences),
            "tokens": len(words),
            "content_tokens": len(content_words),
            "stopwords_removed": len(words) - len(content_words),
            "unique_lemmas": len(set(lemmas)),
        },
        "tokens_sample": (tokenized[0] if tokenized else [])[:12],
        "word_forms": word_forms,
        "pos_counts": {k: pos_counts.get(k, 0) for k in ("NOUN", "VERB", "ADJ", "ADV", "PRON", "OTHER")},
        "entities": _named_entities(tagged_sents),
        "vader": vader_sentiment(text),
        "bigrams": _top_bigrams(sent_lemmas),
        "extractive_summary": _extractive_summary(sentences, sent_lemmas),
    }
    return result, sent_lemmas
