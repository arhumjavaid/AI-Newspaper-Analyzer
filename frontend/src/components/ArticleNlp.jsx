import React from "react";
import { Badge } from "@/components/ui/badge";

// Collapsible view of the NLP engine's work (backend/services/engine.py + nlp.py) for one article.
const ENTITY_GROUPS = [
  { key: "people", label: "Person" },
  { key: "locations", label: "Location" },
  { key: "organisations", label: "Organisation" },
];

function Section({ title, children }) {
  return (
    <div>
      <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </div>
      {children}
    </div>
  );
}

export default function ArticleNlp({ nlp, llmLabel }) {
  if (!nlp) return null;
  const s = nlp.stats;
  const entities = ENTITY_GROUPS.flatMap((g) =>
    (nlp.entities?.[g.key] || []).map((name) => ({ name, label: g.label }))
  );

  return (
    <details className="group mt-3 rounded-md border border-border bg-secondary/30 print:hidden">
      <summary className="cursor-pointer select-none px-3 py-2 text-[12.5px] font-semibold text-foreground">
        NLP Analysis
        <span className="ml-2 font-normal text-muted-foreground">
          {s.sentences} sentences · {s.tokens} tokens
          {nlp.engine ? ` · engine ${nlp.engine.label}` : ` · VADER ${nlp.vader.label}`}
          {nlp.source === "summary" && " · from summary (no body text)"}
        </span>
      </summary>

      <div className="grid grid-cols-1 gap-4 border-t border-border p-3 text-[13px] md:grid-cols-2">
        <Section title="Tokenization & stopwords">
          <div className="text-ink2">
            {s.tokens} word tokens → {s.content_tokens} after removing {s.stopwords_removed} stopwords ·{" "}
            {s.unique_lemmas} unique lemmas
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {nlp.tokens_sample.map((t, i) => (
              <code key={i} className="rounded border border-border bg-card px-1.5 py-px text-[11.5px] text-foreground">
                {t}
              </code>
            ))}
          </div>
        </Section>

        {nlp.engine && (
          <Section title="NLP engine verdict (drives the dashboard)">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={nlp.engine.label}>
                {nlp.engine.label} {nlp.engine.score > 0 ? `+${nlp.engine.score}` : nlp.engine.score}
              </Badge>
              <span className="text-muted-foreground">
                {Math.round(nlp.engine.confidence * 100)}% confident ·{" "}
                {nlp.engine.target_sentences} sentence{nlp.engine.target_sentences === 1 ? "" : "s"} about
                the client · target VADER {nlp.engine.target_vader}
              </span>
            </div>
            {nlp.engine.why?.length > 0 && (
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[12px]">
                <span className="text-muted-foreground">Why:</span>
                {nlp.engine.why.map((w) => (
                  <Badge key={w.feature} variant="outline" className="font-mono text-[11px]" title={`weight ${w.weight}`}>
                    {w.feature}
                  </Badge>
                ))}
              </div>
            )}
          </Section>
        )}

        <Section title="Comparison: stock VADER and Gemini benchmark">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={nlp.vader.label}>
              VADER {nlp.vader.label} {nlp.vader.score > 0 ? `+${nlp.vader.score}` : nlp.vader.score}
            </Badge>
            {llmLabel && <Badge variant={llmLabel}>Gemini {llmLabel}</Badge>}
          </div>
          <div className="mt-1.5 text-[12px] text-muted-foreground">
            VADER compound {nlp.vader.compound} · pos {nlp.vader.pos} · neu {nlp.vader.neu} · neg {nlp.vader.neg}
          </div>
        </Section>

        <Section title="Stemming vs lemmatization">
          <table className="w-full text-[12.5px]">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="font-medium">Word</th>
                <th className="font-medium">POS</th>
                <th className="font-medium">Porter stem</th>
                <th className="font-medium">WordNet lemma</th>
              </tr>
            </thead>
            <tbody>
              {nlp.word_forms.map((w) => (
                <tr key={w.word} className="text-foreground">
                  <td>{w.word}</td>
                  <td className="text-muted-foreground">{w.pos}</td>
                  <td>{w.stem}</td>
                  <td>{w.lemma}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        <Section title="POS tag counts">
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(nlp.pos_counts).map(([tag, n]) => (
              <Badge key={tag} variant="outline" className="font-medium">
                {tag} {n}
              </Badge>
            ))}
          </div>
        </Section>

        <Section title="Named entities (NLTK NER)">
          {entities.length === 0 ? (
            <div className="text-muted-foreground">None found</div>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {entities.map((e) => (
                <Badge key={`${e.label}-${e.name}`} variant="primary" className="font-medium">
                  {e.name} <span className="font-normal opacity-70">· {e.label}</span>
                </Badge>
              ))}
            </div>
          )}
        </Section>

        <Section title="TF-IDF keywords & bigrams">
          <div className="flex flex-wrap gap-1.5">
            {(nlp.keywords || []).map((k) => (
              <Badge key={k.term} variant="primary" className="font-medium" title={`TF-IDF ${k.score}`}>
                {k.term}
              </Badge>
            ))}
            {nlp.bigrams.map((b) => (
              <Badge key={b.phrase} variant="outline" className="font-medium" title="repeated bigram">
                “{b.phrase}” ×{b.count}
              </Badge>
            ))}
          </div>
        </Section>

        <div className="md:col-span-2">
          <Section title="Extractive summary (word-frequency)">
            <div className="text-ink2">{nlp.extractive_summary || "—"}</div>
          </Section>
        </div>
      </div>
    </details>
  );
}
