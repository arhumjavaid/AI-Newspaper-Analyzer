"""Evaluate the NLP engine, its ablations, simpler baselines and the Gemini benchmark.

Every trained model is scored with NESTED cross-validation:
  outer 5-fold StratifiedGroupKFold -> the reported out-of-fold predictions
  inner 3-fold StratifiedGroupKFold -> picks the hyperparameter (C / alpha)
so no hyperparameter is ever chosen by looking at the fold it is tested on, and
"group" keeps near-duplicate stories in the same fold (no leakage).

Writes results.json + RESULTS.md and saves the NLP engine, refit on all articles, to
backend/models/sentiment_engine.joblib (the model the app runs on).

Usage (from backend/):  python evaluation/evaluate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import LinearSVC

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from services import nlp, sentiment  # noqa: E402

LABELS = sentiment.LABELS
SEED = 42
C_GRID = {"clf__C": [0.1, 0.3, 1, 3, 10]}
# The shipped engine is whichever LogReg configuration scores the best nested-CV
# macro-F1 (rule fixed before the run; the selection effect is noted in README.md).
LOGREG_PREFIX = "LogReg,"
GEMINI = "Gemini (LLM benchmark, zero-shot)"


# --- Metrics -----------------------------------------------------------------------------

def metrics(gold: list[str], pred: list[str]) -> dict:
    p, r, f, s = precision_recall_fscore_support(gold, pred, labels=LABELS, zero_division=0)
    macro = precision_recall_fscore_support(gold, pred, labels=LABELS, average="macro", zero_division=0)
    return {
        "accuracy": round(accuracy_score(gold, pred), 3),
        "macro_precision": round(macro[0], 3),
        "macro_recall": round(macro[1], 3),
        "macro_f1": round(macro[2], 3),
        "cohen_kappa": round(cohen_kappa_score(gold, pred, labels=LABELS), 3),
        "per_class": {
            l: {"precision": round(p[i], 3), "recall": round(r[i], 3), "f1": round(f[i], 3), "support": int(s[i])}
            for i, l in enumerate(LABELS)
        },
        # rows = gold, columns = predicted. An off-label prediction (Gemini's
        # "not_detected") counts as wrong above but has no column here.
        "confusion_matrix": confusion_matrix(gold, pred, labels=LABELS).tolist(),
    }


# --- Models ------------------------------------------------------------------------------

def tfidf_only(clf):
    return make_pipeline(
        FunctionTransformer(sentiment.select_terms),
        TfidfVectorizer(analyzer=nlp.identity, sublinear_tf=True, min_df=2),
        clf,
    )


def trained_models() -> dict[str, tuple]:
    """name -> (estimator, hyperparameter grid). The LogReg rows are a 2x2(+1) ablation:
    with/without target terms x with/without domain-VADER features, plus stock VADER."""
    return {
        "Naive Bayes, TF-IDF": (tfidf_only(MultinomialNB()), {"multinomialnb__alpha": [0.1, 0.3, 0.5, 1.0]}),
        "Linear SVM, TF-IDF": (
            tfidf_only(LinearSVC(class_weight="balanced", random_state=SEED)),
            {"linearsvc__C": [0.1, 0.3, 1, 3, 10]},
        ),
        "LogReg, TF-IDF": (sentiment.build_model(with_target_terms=False, lex_keys=()), C_GRID),
        "LogReg, TF-IDF + domain VADER": (sentiment.build_model(with_target_terms=False), C_GRID),
        "LogReg, TF-IDF + target terms": (sentiment.build_model(with_target_terms=True, lex_keys=()), C_GRID),
        "LogReg, TF-IDF + target terms + stock VADER": (
            sentiment.build_model(with_target_terms=True, lex_keys=("lex_stock_doc",)),
            C_GRID,
        ),
        "LogReg, TF-IDF + target terms + domain VADER": (sentiment.build_model(), C_GRID),
    }


def nested_oof(estimator, grid, X, y, groups) -> tuple[list[str], list]:
    """Out-of-fold predictions with the hyperparameter chosen inside each training fold."""
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    pred: list = [None] * len(y)
    chosen = []
    for train, test in outer.split(X, y, groups):
        inner = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED)
        search = GridSearchCV(estimator, grid, cv=inner, scoring="f1_macro")
        search.fit([X[i] for i in train], [y[i] for i in train], groups=[groups[i] for i in train])
        chosen.append(next(iter(search.best_params_.values())))
        for i, p in zip(test, search.predict([X[i] for i in test])):
            pred[i] = p
    return pred, chosen


def review_flag_stats(gold, engine_pred, llm) -> dict:
    """Does the needs-review rule (engine vs Gemini disagreement) find the engine's errors?

    Only the disagreement rule is measured; the confidence rule needs the shipped
    model's probabilities, which are not out-of-fold.
    """
    flagged = [e != l for e, l in zip(engine_pred, llm)]
    wrong = [e != g for e, g in zip(engine_pred, gold)]
    n, n_flag, n_err = len(gold), sum(flagged), sum(wrong)
    caught = sum(f and w for f, w in zip(flagged, wrong))
    return {
        "articles": n,
        "flagged": n_flag,
        "engine_errors": n_err,
        "errors_caught": caught,
        "error_rate_flagged": round(caught / n_flag, 3) if n_flag else None,
        "error_rate_unflagged": round((n_err - caught) / (n - n_flag), 3) if n > n_flag else None,
    }


def top_engine_features(model, k: int = 12) -> dict[str, list[str]]:
    union = model.named_steps["features"]
    names: list[str] = []
    for name, part in union.transformer_list:
        if name == "tfidf":
            names += list(part[-1].get_feature_names_out())
        else:
            names += [n for key in part[0].kw_args["keys"] for n in sentiment.LEX_NAMES[key]]
    clf = model.named_steps["clf"]
    return {cls: [names[i] for i in clf.coef_[j].argsort()[::-1][:k]] for j, cls in enumerate(clf.classes_)}


# --- Main --------------------------------------------------------------------------------

def main() -> None:
    rows = [json.loads(line) for line in (HERE / "dataset.jsonl").open(encoding="utf-8")]
    gold = [r["label"] for r in rows]
    groups = [r["group"] for r in rows]
    # Headline + body: what the app's engine analyses, and what Gemini was given.
    X = [sentiment.featurize(f"{r['headline']}. {r['body']}") for r in rows]
    print(f"featurized {len(X)} articles")

    results: dict[str, dict] = {}
    notes: dict[str, str] = {}
    oof: dict[str, list[str]] = {}

    base: list = [None] * len(gold)
    for train, test in StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, gold, groups):
        d = DummyClassifier(strategy="most_frequent").fit([[0]] * len(train), [gold[i] for i in train])
        for i in test:
            base[i] = d.predict([[0]])[0]
    results["Majority-class baseline"] = metrics(gold, base)

    rules = {
        "VADER, stock lexicon, whole article": [sentiment.vader_label(x["lex_stock_doc"][0]) for x in X],
        "VADER + domain lexicon, whole article": [sentiment.vader_label(x["lex_domain_doc"][0]) for x in X],
        "VADER + domain lexicon, target sentences": [sentiment.vader_label(x["lex_domain_target"][0]) for x in X],
    }
    for name, pred in rules.items():
        results[name] = metrics(gold, pred)
        notes[name] = "rule-based, no training"

    for name, (est, grid) in trained_models().items():
        pred, chosen = nested_oof(est, grid, X, gold, groups)
        oof[name] = pred
        results[name] = metrics(gold, pred)
        notes[name] = f"nested CV; hyperparameter chosen per outer fold: {chosen}"
        print(f"{name:58s} macroF1={results[name]['macro_f1']:.3f}")

    cache = json.loads((HERE / "llm_predictions.json").read_text(encoding="utf-8"))
    raw = [cache.get(str(r["id"]), {}).get("label", "missing") for r in rows]
    llm = ["neutral" if p == "mixed" else p for p in raw]
    results[GEMINI] = metrics(gold, llm)
    notes[GEMINI] = (
        f"{raw.count('mixed')} 'mixed' folded into neutral; "
        f"{raw.count('not_detected')} not detected as relevant (counted wrong)"
    )

    engine = max((n for n in oof if n.startswith(LOGREG_PREFIX)), key=lambda n: results[n]["macro_f1"])
    engine_pred = oof[engine]
    errors = [
        {"id": r["id"], "headline": r["headline"], "gold": g, "engine": e, "gemini": raw[i],
         "target_sentences": len(X[i]["target_ids"]), "reason": r["label_reason"]}
        for i, (r, g, e) in enumerate(zip(rows, gold, engine_pred))
        if g != e
    ]

    # Refit the engine on all articles (C chosen by grouped CV) and ship it.
    est, grid = trained_models()[engine]
    search = GridSearchCV(est, grid, cv=StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED),
                          scoring="f1_macro")
    search.fit(X, gold, groups=groups)
    best_c = search.best_params_["clf__C"]
    sentiment.MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(
        {
            "pipeline": search.best_estimator_,
            "model": engine,
            "C": best_c,
            "cv_macro_f1": results[engine]["macro_f1"],
            "cv_accuracy": results[engine]["accuracy"],
            "n_train": len(rows),
        },
        sentiment.MODEL_PATH,
    )

    summary = {
        "n_articles": len(rows),
        "n_stories": len(set(groups)),
        "label_counts": {l: gold.count(l) for l in LABELS},
        "results": results,
        "notes": notes,
        "review_flag": review_flag_stats(gold, engine_pred, llm),
        "engine_errors": errors,
        "engine_name": engine,
        "engine_C": best_c,
        "engine_top_features": top_engine_features(search.best_estimator_),
    }
    (HERE / "results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (HERE / "RESULTS.md").write_text(render_markdown(summary), encoding="utf-8")

    print()
    for name, m in results.items():
        print(f"{name:58s} acc={m['accuracy']:.3f} macroF1={m['macro_f1']:.3f} kappa={m['cohen_kappa']:.3f}")
    print("review flag:", summary["review_flag"])
    print(f"shipped engine: {engine} (C={best_c}) -> {sentiment.MODEL_PATH}")


# --- Report -------------------------------------------------------------------------------

def _row(name: str, m: dict) -> str:
    return (
        f"| {name} | {m['accuracy']:.3f} | {m['macro_precision']:.3f} | {m['macro_recall']:.3f} "
        f"| **{m['macro_f1']:.3f}** | {m['cohen_kappa']:.3f} |"
    )


def render_markdown(s: dict) -> str:
    R = s["results"]
    E = s["engine_name"]
    head = ["| Method | Accuracy | Macro P | Macro R | Macro F1 | Cohen's κ |", "|---|---|---|---|---|---|"]
    lines = [
        "# Sentiment evaluation results",
        "",
        f"{s['n_articles']} real K-Electric news articles ({s['n_stories']} distinct stories) from Dawn, "
        f"ARY News, Aaj News, Business Recorder and ProPakistani. Gold labels: {s['label_counts']}. "
        "Generated by `evaluate.py`; method and caveats in README.md, error analysis in ERROR_ANALYSIS.md.",
        "",
        "## Main results",
        "",
        *head,
    ]
    for name in ("Majority-class baseline", "VADER, stock lexicon, whole article", "Naive Bayes, TF-IDF",
                 "Linear SVM, TF-IDF", E, GEMINI):
        lines.append(_row(f"**NLP engine (shipped):** {name}" if name == E else name, R[name]))

    lines += ["", "## Ablation: what each part of the NLP engine adds", "",
              "Lexicon methods (no training), each row adds one idea:", "", *head]
    for name in ("VADER, stock lexicon, whole article", "VADER + domain lexicon, whole article",
                 "VADER + domain lexicon, target sentences"):
        lines.append(_row(name, R[name]))
    lines += ["", "Trained logistic regression, each row adds one feature group:", "", *head]
    for name in [n for n in R if n.startswith(LOGREG_PREFIX)]:
        lines.append(_row(name, R[name]))

    lines += ["", "## Per-class F1", "", "| Method | Positive | Neutral | Negative |", "|---|---|---|---|"]
    for name, m in R.items():
        pc = m["per_class"]
        lines.append(f"| {name} | {pc['positive']['f1']:.3f} | {pc['neutral']['f1']:.3f} | {pc['negative']['f1']:.3f} |")

    lines += ["", "## Confusion matrices (rows = gold, columns = predicted)", ""]
    for name in ("VADER, stock lexicon, whole article", E, GEMINI):
        cm = R[name]["confusion_matrix"]
        lines += [f"**{name}**", "", "| gold \\ pred | positive | neutral | negative |", "|---|---|---|---|"]
        for label, row in zip(LABELS, cm):
            lines.append(f"| {label} | {row[0]} | {row[1]} | {row[2]} |")
        lines += ["", f"_{s['notes'][name]}_", ""]

    rf = s["review_flag"]
    lines += [
        "## Does the \"needs review\" flag catch the engine's mistakes?",
        "",
        "The app flags an article when the NLP engine and the Gemini benchmark disagree "
        "(engine predictions here are out-of-fold).",
        "",
        f"- Flagged: {rf['flagged']} of {rf['articles']} articles; caught {rf['errors_caught']} "
        f"of the engine's {rf['engine_errors']} errors",
        f"- Engine error rate on flagged articles: **{rf['error_rate_flagged']:.0%}**",
        f"- Engine error rate when engine and Gemini agree: **{rf['error_rate_unflagged']:.0%}**",
        "",
        f"## Shipped engine: {E} (C = {s['engine_C']}, refit on all {s['n_articles']} articles): most indicative features",
        "",
        "`t:` = term inside a sentence about the client; `dvader_*` = domain-VADER score.",
        "",
    ]
    for cls, feats in s["engine_top_features"].items():
        lines.append(f"- **{cls}**: {', '.join(f'`{f}`' for f in feats)}")

    lines += ["", f"## Engine errors ({len(s['engine_errors'])}, out-of-fold)", "",
              "| id | Headline | Gold | Engine | Gemini | KE sentences |", "|---|---|---|---|---|---|"]
    for e in s["engine_errors"]:
        lines.append(f"| {e['id']} | {e['headline'][:70]} | {e['gold']} | {e['engine']} | {e['gemini']} "
                     f"| {e['target_sentences']} |")
    lines += ["", "## Hyperparameters chosen by the inner CV", ""]
    lines += [f"- {name}: {note}" for name, note in s["notes"].items() if "nested" in note]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
