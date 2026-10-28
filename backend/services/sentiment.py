"""Target-dependent sentiment engine: the sentiment the dashboard runs on.

Features for one article (`featurize`):
  - terms         : lemma unigrams + bigrams of the whole article (from services.nlp)
  - target terms  : the same, from the sentences about the client only, prefixed
                    "t:" so "t:fail" (the client failed) is a different feature
                    from "fail" (anything failed)
  - lexicon scores: VADER with the domain lexicon, on the whole article and on the
                    target sentences; plus stock VADER for the ablation study

A logistic-regression model over these (`build_model`) is trained and evaluated by
evaluation/evaluate.py and saved to models/sentiment_engine.joblib. If no model has
been trained yet, `predict` falls back to the rule: domain VADER on target sentences.
"""
from __future__ import annotations

import nltk
import numpy as np
from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline, make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

import joblib

from config import BASE_DIR
from services import nlp
from services.lexicons import DOMAIN_VALENCE
from services.targets import target_sentence_ids

MODEL_PATH = BASE_DIR / "models" / "sentiment_engine.joblib"
LABELS = ["positive", "neutral", "negative"]
# Thresholds recommended by VADER's authors.
VADER_POS, VADER_NEG = 0.05, -0.05

_domain_vader: SentimentIntensityAnalyzer | None = None
_bundle: dict | None = None
_bundle_loaded = False


def domain_vader() -> SentimentIntensityAnalyzer:
    """VADER with the power-sector lexicon merged in (domain adaptation)."""
    global _domain_vader
    if _domain_vader is None:
        nlp._ensure_ready()
        _domain_vader = SentimentIntensityAnalyzer()
        _domain_vader.lexicon.update(DOMAIN_VALENCE)
    return _domain_vader


def vader_label(compound: float) -> str:
    if compound >= VADER_POS:
        return "positive"
    if compound <= VADER_NEG:
        return "negative"
    return "neutral"


# --- Features ----------------------------------------------------------------------------

def featurize(text: str, sent_lemmas: list[list[str]] | None = None) -> dict:
    """Everything the model needs from one article, plus the target sentences."""
    nlp._ensure_ready()
    sentences = nltk.sent_tokenize(nlp.clean_text(text))
    if sent_lemmas is None:
        _, sent_lemmas = nlp.analyze_text(text)
    target_ids = target_sentence_ids(sentences)
    target_text = " ".join(sentences[i] for i in target_ids)
    doc_terms = nlp.terms(sent_lemmas)
    target_terms = ["t:" + t for t in nlp.terms([sent_lemmas[i] for i in target_ids if i < len(sent_lemmas)])]

    dv = domain_vader()
    doc_d = dv.polarity_scores(text)
    # No sentence names the client (implicit coverage): the whole article is the target.
    tgt_d = dv.polarity_scores(target_text) if target_text else doc_d
    doc_s = nlp._vader.polarity_scores(text)
    return {
        "terms": doc_terms,
        "target_terms": target_terms,
        "lex_stock_doc": [doc_s["compound"], doc_s["pos"], doc_s["neg"]],
        "lex_domain_doc": [doc_d["compound"], doc_d["pos"], doc_d["neg"]],
        "lex_domain_target": [tgt_d["compound"], tgt_d["pos"], tgt_d["neg"], float(bool(target_ids))],
        "sentences": sentences,
        "target_ids": target_ids,
    }


# Module-level selectors so trained pipelines can be pickled.
def select_terms(X: list[dict], with_target: bool = False) -> list[list[str]]:
    return [x["terms"] + (x["target_terms"] if with_target else []) for x in X]


def select_lex(X: list[dict], keys: tuple[str, ...] = ()) -> np.ndarray:
    return np.array([[v for k in keys for v in x[k]] for x in X])


LEX_NAMES = {
    "lex_stock_doc": ["vader_doc_compound", "vader_doc_pos", "vader_doc_neg"],
    "lex_domain_doc": ["dvader_doc_compound", "dvader_doc_pos", "dvader_doc_neg"],
    "lex_domain_target": ["dvader_target_compound", "dvader_target_pos", "dvader_target_neg", "has_target"],
}


def build_model(with_target_terms: bool = True, lex_keys: tuple[str, ...] = ("lex_domain_doc", "lex_domain_target"),
                C: float = 1.0) -> Pipeline:
    """TF-IDF (+ target terms) and lexicon scores -> logistic regression."""
    parts = [(
        "tfidf",
        make_pipeline(
            FunctionTransformer(select_terms, kw_args={"with_target": with_target_terms}),
            TfidfVectorizer(analyzer=nlp.identity, sublinear_tf=True, min_df=2),
        ),
    )]
    if lex_keys:
        parts.append((
            "lex",
            make_pipeline(FunctionTransformer(select_lex, kw_args={"keys": tuple(lex_keys)}), StandardScaler()),
        ))
    return Pipeline([
        ("features", FeatureUnion(parts)),
        ("clf", LogisticRegression(C=C, max_iter=3000, class_weight="balanced", random_state=42)),
    ])


# --- Prediction ----------------------------------------------------------------------------

def _load() -> dict | None:
    global _bundle, _bundle_loaded
    if not _bundle_loaded:
        _bundle_loaded = True
        if MODEL_PATH.exists():
            _bundle = joblib.load(MODEL_PATH)
    return _bundle


def info() -> dict:
    b = _load()
    if not b:
        return {"model": "Rule: domain VADER on target sentences (no trained model found)"}
    return {k: b[k] for k in ("model", "cv_macro_f1", "cv_accuracy", "n_train", "C")}


def _explain(model: Pipeline, x: dict, class_idx: int, k: int = 5) -> list[dict]:
    """Features that pushed the prediction toward the chosen class (coef x value)."""
    union: FeatureUnion = model.named_steps["features"]
    row = union.transform([x])
    row = row.toarray()[0] if hasattr(row, "toarray") else np.asarray(row)[0]
    names: list[str] = []
    for name, part in union.transformer_list:
        if name == "tfidf":
            names += list(part[-1].get_feature_names_out())
        else:
            keys = part[0].kw_args["keys"]
            names += [n for key in keys for n in LEX_NAMES[key]]
    contrib = row * model.named_steps["clf"].coef_[class_idx]
    top = contrib.argsort()[::-1][:k]
    return [{"feature": names[i], "weight": round(float(contrib[i]), 3)} for i in top if contrib[i] > 0]


def predict(x: dict) -> dict:
    """Label, -100..100 score, confidence and an explanation for one featurized article."""
    tgt = x["lex_domain_target"][0]
    bundle = _load()
    if not bundle:
        return {
            "label": vader_label(tgt),
            "score": round(tgt * 100),
            "confidence": round(min(1.0, 0.5 + abs(tgt) / 2), 3),
            "method": "rule",
            "why": [],
        }
    model: Pipeline = bundle["pipeline"]
    probs = model.predict_proba([x])[0]
    classes = list(model.classes_)
    best = int(probs.argmax())
    p = dict(zip(classes, probs))
    return {
        "label": classes[best],
        "score": round((p.get("positive", 0) - p.get("negative", 0)) * 100),
        "confidence": round(float(probs[best]), 3),
        "probabilities": {c: round(float(v), 3) for c, v in p.items()},
        "method": "model",
        "why": _explain(model, x, best),
    }
