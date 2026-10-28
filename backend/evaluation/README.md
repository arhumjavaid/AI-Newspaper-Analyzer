# Sentiment evaluation

The dashboard's sentiment comes from our own **NLP engine** (`services/engine.py`,
`services/sentiment.py`). Gemini only extracts the articles from the PDF, and its
zero-shot sentiment is kept as a **benchmark**. This folder measures how good the
engine is, which of its parts help, and how it compares with Gemini.

Numbers: **[RESULTS.md](RESULTS.md)** · why the engine fails where it does:
**[ERROR_ANALYSIS.md](ERROR_ANALYSIS.md)** · raw: `results.json`.

## Headline results (89 articles, nested cross-validation)

| Method | Accuracy | Macro F1 |
|---|---|---|
| Majority-class baseline | 0.371 | 0.180 |
| VADER, stock lexicon | 0.629 | 0.491 |
| VADER + domain lexicon + target sentences (rule-based) | 0.652 | 0.544 |
| Naive Bayes, TF-IDF | 0.629 | 0.583 |
| Linear SVM, TF-IDF | 0.719 | 0.708 |
| **NLP engine (shipped): LogReg, TF-IDF** | **0.730** | **0.718** |
| Gemini (LLM benchmark, zero-shot) | 0.775 | 0.755 |

- The engine gets within 0.04 macro-F1 of Gemini, with no API calls.
- **Review flag:** when the engine and Gemini agree, the engine is right 92% of the
  time. Flagging only their disagreements (29 of 89 articles) catches 19 of the
  engine's 24 errors.

## What the ablation shows

| Idea | Effect | Kept? |
|---|---|---|
| Domain lexicon added to VADER ("fine" is negative here, "load-shedding" exists) | rule-based F1 0.491 → 0.497 | yes, in the rule-based fallback and key-sentence selection |
| Target sentences (only sentences about the client) | rule-based F1 0.497 → 0.544 | yes, same |
| Headline included with the body | LogReg F1 0.665 → 0.718 | **yes** |
| Target-sentence terms as extra features (`t:` prefix) | LogReg F1 0.718 → 0.654 | no |
| VADER scores as extra features | LogReg F1 0.718 → 0.689 | no |

The linguistic ideas (domain adaptation, target-dependent sentiment) clearly help the
**lexicon** method. In the **trained** model they did not: with 89 articles, extra
feature groups add more noise than signal. That is an honest negative result, and the
shipped engine is the configuration that actually scored best.

## Dataset

- **89 articles, 73 distinct stories** (2015–2026) from Dawn, ARY News, Aaj News,
  Business Recorder and ProPakistani: load-shedding, tariffs, billing, electrocution
  deaths, NEPRA fines, protests, investments, CSR awards, CEO changes, financial results.
- Text = headline + the first ~180 words, scraped verbatim (`scrape.py`, `urls.txt`).
  Excerpts are kept for research and evaluation only.
- **Label = sentiment toward K-Electric** (positive / neutral / negative), the same
  definition as the LLM prompt. 33 positive, 25 neutral, 31 negative.
- `labels.py`: every label has a one-line reason and a **story group**. Near-duplicate
  reports of one event share a group.

### Who labelled the data — read this

The gold labels were produced by **Claude (Anthropic)**, a different model from the
Gemini model being benchmarked, after reading every article. They are
**AI-annotated, not human-annotated**:

- Scores measure agreement with a careful independent annotator, not with human truth.
- The trained engine learns this annotator's labelling policy.
- To upgrade to human labels: review `labels.py` (each row has its reason), then re-run
  `build_dataset.py` and `evaluate.py`. Two human annotators plus Cohen's κ between
  them would be the gold standard.

## Method

- **Nested cross-validation** for every trained model:
  - The **outer** 5-fold `StratifiedGroupKFold` produces the reported out-of-fold predictions.
  - An **inner** 3-fold grouped CV picks the hyperparameter (C or alpha) using only
    the outer training folds.
  - Groups keep every copy of a story in one fold, so there is no leakage between
    near-duplicates.
- **Engine selection rule**, fixed before the final run: ship the logistic-regression
  configuration with the best nested-CV macro-F1. Picking the best of 5 configurations
  on the same data slightly inflates the reported score of the winner. Treat 0.718 as
  an optimistic estimate.
- **Gemini** runs once per article through the real pipeline (`run_llm.py`, cached in
  `llm_predictions.json`). Its "mixed" label is folded into neutral. An article it drops
  as irrelevant counts as wrong.
- **Metrics:** accuracy, macro precision / recall / F1 (all classes weighted equally),
  Cohen's κ, per-class F1 and confusion matrices.
- **History:** the first version of the engine read only the article body, while Gemini
  saw headline + body. It scored 0.668 macro-F1 (`RESULTS_v1_body_only.md`). Error
  analysis showed the headline carries the paper's framing ("KE *admits*…"), so both
  now get the same input. This change was made after looking at the v1 results.

## Reproduce

```bash
cd backend
python evaluation/scrape.py evaluation/urls.txt evaluation/raw evaluation/articles_raw.jsonl  # optional: re-download
python evaluation/build_dataset.py   # clean + attach labels -> dataset.jsonl
python evaluation/run_llm.py         # Gemini benchmark (needs GEMINI_API_KEY; cached)
python evaluation/evaluate.py        # metrics -> RESULTS.md, results.json, models/sentiment_engine.joblib
```

## Limitations

- 89 articles is small. A few articles move a score by several points.
- Labels are AI-annotated (see above).
- Excerpts are the first ~180 words, so sentiment later in an article is missed.
- Bag-of-words cannot tell "load-shedding starts" from "load-shedding ends"
  (ERROR_ANALYSIS.md, category 1).
- English-language press only.
