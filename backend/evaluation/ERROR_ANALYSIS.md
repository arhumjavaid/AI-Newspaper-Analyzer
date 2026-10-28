# Error analysis

The shipped NLP engine (logistic regression on TF-IDF of headline + body lemmas and
bigrams) makes 24 errors on the 89 evaluation articles (out-of-fold predictions;
the full list is at the end of [RESULTS.md](RESULTS.md)). Gemini makes 20. They
overlap on only 10, and that overlap is what makes the needs-review flag work.

## 1. A positive action on a negative topic (7 errors)

| id | Headline | Gold | Engine |
|---|---|---|---|
| 2 | K-Electric ends temporary load shedding in Karachi | positive | negative |
| 32 | Power restored in many areas of Karachi after major outage | positive | negative |
| 59 | Power restored in most areas of Karachi after major outage | positive | negative |
| 84 | K-Electric Announces Relief for Karachi Consumers During Ashura | positive | negative |
| 60 | After major power breakdown, electricity supply to Karachi normalizes | neutral | negative |
| 33 | Power breakdown hits several areas … as transmission line trips | neutral | negative |
| 1 | K-Electric starts load shedding in exempted areas of Karachi | negative | positive |

These articles are full of the domain's most negative words (*load-shedding, outage,
breakdown*), but the event they report is the problem **ending** ("ends", "restored",
"suspended"). A bag-of-words model sees which words occur, not what happens to them,
so it cannot tell "load-shedding starts" from "load-shedding ends". Id 1 is the mirror
image: *exempted* carries positive weight, but here the exemption is being removed.
VADER's negation rule only flips sentiment after words like *not* or *never*, so it
does not help either. Fixing this needs event-level or compositional meaning:
dependency parsing ("ends" → object "load-shedding") or a model that reads word order.
Gemini also misses three of these (2 → mixed, 32 and 59 → neutral).

## 2. Hard-news negatives with rare vocabulary (5 errors)

| id | Headline | Gold | Engine |
|---|---|---|---|
| 26 | Nepra imposes Rs25m fine on K-Electric | negative | neutral |
| 27 | K-Electric fined Rs25m over 2023 blackout | negative | neutral |
| 36 | K-Electric seeks Rs3.84 per unit base tariff hike for seven years | negative | neutral |
| 43 | KE admits up to 10 hours of loadshedding in several areas | negative | neutral |
| 75 | K-Electric Posts Staggering Loss of Over Rs. 27 Billion in First Half | negative | neutral |

These are negative for the client but written in flat regulatory or financial
language. The words that matter (*fine, fined, penalty, staggering loss*) appear in
very few training articles. Ids 26, 27 and 51 report the same NEPRA fine and share a
story group, so grouped cross-validation keeps all three in the same test fold. When
the model is scored on them it has never seen "fined" in training. That is the
correct, leakage-free setup, and it shows the real cost of a small dataset. The
domain lexicon does mark *fine/fined* as negative, but lexicon features did not help
the trained model overall (see the ablation in RESULTS.md).

## 3. Where neutral ends (9 errors)

Ids 17, 56 (CEO reappointment, gold positive) vs 70 (interim CEO, gold neutral);
37, 35, 57, 87 (deals and financial results, gold neutral, engine positive);
55, 85, 86 (procedural notices). Neutral is the hardest class for every method
(see per-class F1). Part of the difficulty is in the labels themselves: ids 17 and
56 were labelled positive because their text praises the CEO, while id 45, the same
story told plainly, was labelled neutral. These boundary cases are where a second
human annotator would help most.

## 4. Coverage that never names the client (1 error)

Id 23 (electrocution deaths) has no sentence naming K-Electric. The engine reads
"deaths" as negative, while the gold label is neutral because the excerpt blames
civic drainage, not the utility. Gemini dropped this article as not relevant at all.

## Engine vs Gemini: different mistakes

- **Engine right, Gemini wrong (10):** ids 4, 5, 16, 19, 45, 66, 71, 73, 76, 81.
  Seven of these are procedural or neutral stories that Gemini gave a polarity to
  (e.g. a CEO appointment read as positive, a tariff review read as negative). The
  LLM reads more sentiment into announcements than the gold labels do.
- **Both wrong (10):** ids 2, 23, 32, 35, 36, 43, 55, 57, 59, 87. These are mostly
  categories 1 and 3 above, the genuinely ambiguous cases.
- Because the two make different mistakes, **disagreement between them is a strong
  error signal**. When they agree, the engine is right 92% of the time. When they
  disagree, the engine is wrong 66% of the time. The app flags exactly these
  articles for human review.

## What would help next

1. **More labelled data**, especially regulatory and financial stories (category 2).
2. **Event-aware features** for category 1: dependency relations such as
   (ends, load-shedding) or (restored, power) as features.
3. **A second human annotator** for the neutral boundary (category 3), with Cohen's κ
   between annotators.
