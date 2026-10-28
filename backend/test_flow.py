"""End-to-end backend flow test with a mocked LLM (no API key needed).

Proves: upload -> extract -> (mocked) analyze -> aggregate -> store -> serve,
and that trends accumulate across multiple uploads.
"""
import main
from fastapi.testclient import TestClient

MOCK = {
    "publication_name": "The Karachi Herald",
    "publication_date": "2026-06-17",
    "model": "mock",
    "executive_summary": (
        "Today's coverage of K-Electric is mixed-to-negative, driven by a front-page "
        "story on prolonged load-shedding in Lyari that includes accusatory protester "
        "quotes. Positive items on tariff relief and a new grid station partly offset "
        "this. One item warrants an urgent response."
    ),
    "articles": [
        {
            "headline": "K-Electric blamed for prolonged load-shedding",
            "summary": "Residents protest unannounced load-shedding.",
            "body": ("Residents of several Karachi neighbourhoods staged protests on Monday, "
                     "accusing K-Electric of subjecting them to hours of unannounced "
                     "load-shedding despite paying inflated bills. \"KE has once again failed "
                     "the people of this city,\" said a protester. Critics say the utility's "
                     "excuses have worn thin."),
            "page": 1,
            "prominence": "front_page",
            "sentiment_label": "negative",
            "sentiment_score": -78,
            "tone_tags": ["accusatory", "taunt"],
            "key_quote": "KE has once again failed the people of this city.",
            "people": ["Protest leader Asif Khan"],
            "locations": ["Lyari", "Gulshan-e-Iqbal"],
            "organisations": ["NEPRA"],
            "topics": ["load-shedding", "billing"],
            "confidence": 0.95,
            "suggested_response": "Issue a statement detailing the fault and restoration timeline.",
        },
        {
            "headline": "NEPRA approves tariff relief; KE welcomes decision",
            "summary": "Small tariff adjustment welcomed by the utility.",
            "body": ("In a separate development, NEPRA announced a small tariff adjustment. "
                     "K-Electric welcomed the regulator's decision, saying it would help "
                     "sustain investment in the grid and improve supply reliability for "
                     "consumers across Karachi."),
            "page": 3,
            "prominence": "standard",
            "sentiment_label": "positive",
            "sentiment_score": 55,
            "tone_tags": ["factual"],
            "key_quote": "K-Electric welcomed the regulator's decision.",
            "people": [],
            "locations": [],
            "organisations": ["NEPRA"],
            "topics": ["tariff", "investment"],
            "confidence": 0.9,
            "suggested_response": None,
        },
        {
            "headline": "KE completes new grid station to boost supply",
            "summary": "New grid station strengthens supply.",
            "body": ("K-Electric announced the completion of a new grid station in the "
                     "industrial area, a move the company says will strengthen supply to "
                     "thousands of businesses and households."),
            "page": 5,
            "prominence": "minor",
            "sentiment_label": "positive",
            "sentiment_score": 40,
            "tone_tags": ["praise", "factual"],
            "key_quote": "strengthen supply to thousands of businesses",
            "people": [],
            "locations": ["Korangi"],
            "organisations": [],
            "topics": ["investment"],
            "confidence": 0.85,
            "suggested_response": None,
        },
    ],
}


def fake_analyze(pages):
    from pipeline.analyze import _clean_articles
    return {
        "publication_name": MOCK["publication_name"],
        "publication_date": MOCK["publication_date"],
        "executive_summary": MOCK["executive_summary"],
        "articles": _clean_articles(MOCK["articles"]),
        "model": "mock",
    }


main.analyze_pages = fake_analyze  # patch the name bound in main
client = TestClient(main.app)

# health
h = client.get("/api/health").json()
print("health:", h["status"], "configured:", h["configured"])

pdf = open("sample_newspaper.pdf", "rb").read()

# upload twice (simulates two days -> trend line)
for n in (1, 2):
    r = client.post(
        "/api/upload",
        files={"file": (f"herald_day{n}.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    a = r.json()
    print(f"\nUPLOAD {n}: id={a['id']} articles={len(a['articles'])}")
    m = a["metrics"]
    print("  reputation_index:", m["reputation_index"])
    print("  sentiment_dist  :", m["sentiment_distribution"])
    print("  avg_sentiment   :", m["average_sentiment"])
    print("  AVE (USD)       :", m["ave_estimate_usd"])
    print("  share_of_voice  :", [(x["name"], x["mentions"]) for x in m["share_of_voice"]])
    print("  top_topics      :", [(t["topic"], t["count"]) for t in m["top_topics"]])
    print("  crisis_alerts   :", len(m["crisis_alerts"]),
          "->", [c["headline"] for c in m["crisis_alerts"]])
    print("  risk_dist       :", m["risk_distribution"])
    print("  entity_insights :", {k: [e["name"] for e in v]
                                   for k, v in m["entity_insights"].items()})
    print("  exec_summary?   :", bool(a.get("executive_summary")))
    print("  article risk    :", [x["risk_level"] for x in a["articles"]])
    assert a.get("executive_summary"), "executive_summary missing"
    assert all("risk_level" in x for x in a["articles"]), "risk_level missing"
    nlp0 = a["articles"][0]["nlp"]
    print("  nlp stats       :", nlp0["stats"])
    print("  nlp keywords    :", [k["term"] for k in nlp0["keywords"]])
    print("  nlp entities    :", nlp0["entities"])
    print("  nlp vader       :", [x["nlp"]["vader"]["label"] for x in a["articles"]])
    print("  nlp comparison  :", m["nlp_comparison"])
    assert all(x["nlp"]["source"] == "body" for x in a["articles"]), "body not used"
    assert m["nlp_comparison"]["articles"] == 3, "nlp_comparison missing"
    print("  needs review    :", [x["review_reasons"] for x in a["articles"]])
    print("  engine          :", [(x["sentiment_label"], x["nlp"]["engine"]["method"]) for x in a["articles"]])
    print("  gemini benchmark:", [x["llm"]["sentiment_label"] for x in a["articles"]])
    print("  engine topics   :", [x["topics"] for x in a["articles"]])
    print("  engine summary  :", a["executive_summary"])
    assert all("needs_review" in x for x in a["articles"]), "needs_review missing"
    assert m["review_count"] == sum(x["needs_review"] for x in a["articles"])
    # The dashboard's sentiment must come from the NLP engine, not from Gemini.
    assert all(x["sentiment_score"] == x["nlp"]["engine"]["score"] for x in a["articles"])
    assert all(x["llm"]["sentiment_label"] for x in a["articles"]), "Gemini benchmark missing"
    assert a["llm_executive_summary"] != a["executive_summary"]

# review rule: engine vs Gemini benchmark disagreement must be flagged
from pipeline.aggregate import review_reasons
conflict = {"sentiment_label": "positive", "confidence": 0.9, "llm": {"sentiment_label": "negative"}}
agree = {"sentiment_label": "neutral", "confidence": 0.9, "llm": {"sentiment_label": "mixed"}}
assert review_reasons(conflict) == ["polarity conflict: NLP engine positive, Gemini benchmark negative"]
assert review_reasons(agree) == []  # Gemini's "mixed" counts as neutral
assert review_reasons({**agree, "confidence": 0.4}) == ["low NLP engine confidence (0.40)"]

# engine helpers
from services import engine
from services.targets import target_sentence_ids
sents = ["Rain lashed the city.", "K-Electric said supply was restored.", "The utility added that teams were deployed.", "Traffic was slow."]
assert target_sentence_ids(sents) == [1, 2], target_sentence_ids(sents)  # coreference follow-up
assert "load-shedding" in engine.topics("Hours of load-shedding and outages in Lyari")
ents = engine.entities("Residents of Lyari protested outside NEPRA in Karachi.", {"organisations": ["Karachi"]})
assert ents["locations"] == ["Lyari"] and ents["organisations"] == ["NEPRA"], ents

# list + trends
ups = client.get("/api/uploads").json()
trends = client.get("/api/trends").json()
print("\nuploads stored:", len(ups))
print("trend points  :", len(trends),
      "->", [(t["date"], t["reputation_index"]) for t in trends])

# fetch one full upload
one = client.get(f"/api/uploads/{ups[0]['id']}").json()
print("fetch one upload OK, articles:", len(one["articles"]))
print("\nALL ASSERTIONS PASSED")
