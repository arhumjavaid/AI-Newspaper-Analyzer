import React, { useEffect, useRef, useState } from "react";
import { getHealth, getUploads, getUpload, deleteUpload } from "./api";
import UploadPanel from "./components/UploadPanel";
import SentimentDonut from "./components/SentimentDonut";
import ShareOfVoice from "./components/ShareOfVoice";
import ReputationDrivers from "./components/ReputationDrivers";
import Sparkline from "./components/Sparkline";
import CrisisAlerts from "./components/CrisisAlerts";
import ExecutiveSummary from "./components/ExecutiveSummary";
import EntityInsights from "./components/EntityInsights";
import NlpComparison from "./components/NlpComparison";
import CoverageClusters from "./components/CoverageClusters";
import CoverageRadar from "./components/CoverageRadar";
import ArticleCard from "./components/ArticleCard";
import ArticleTable from "./components/ArticleTable";
import CoverageImpactMap from "./components/CoverageImpactMap";
import ThemeToggle from "./components/ThemeToggle";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, FileDown, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

const SESSION_KEY = "currentAnalysis";

export default function App() {
  const [health, setHealth] = useState(null);
  const [analysis, setAnalysis] = useState(() => {
    try {
      const stored = sessionStorage.getItem(SESSION_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [history, setHistory] = useState([]);
  const [clusterFilter, setClusterFilter] = useState(null);
  const [feedView, setFeedView] = useState("cards"); // "cards" | "table"
  const [query, setQuery] = useState("");
  const [feedFilter, setFeedFilter] = useState("all"); // all|critical|negative|front
  const [exporting, setExporting] = useState(false);
  const reportRef = useRef(null);

  async function refreshMeta() {
    try {
      setHistory(await getUploads());
    } catch (e) {
      /* non-fatal */
    }
  }

  useEffect(() => {
    let cancelled = false;
    // The backend can cold-start (Cloud Run scales to zero): nginx answers on
    // 8080 before uvicorn is up, so /api/health 502s for a second or two. Retry
    // with backoff instead of latching "no API key" on the first failure.
    async function pollHealth(attempt = 0) {
      try {
        const h = await getHealth();
        if (!cancelled) setHealth(h);
      } catch {
        if (cancelled) return;
        if (attempt < 15) {
          setTimeout(() => pollHealth(attempt + 1), Math.min(1000 * 2 ** attempt, 5000));
        } else {
          setHealth({ configured: false });
        }
      }
    }
    pollHealth();
    refreshMeta();
    return () => {
      cancelled = true;
    };
  }, []);

  function onAnalyzed(result) {
    setClusterFilter(null);
    setAnalysis(result);
    try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(result)); } catch {}
    refreshMeta();
  }

  function handleNew() {
    setAnalysis(null);
    setClusterFilter(null);
    setQuery("");
    try { sessionStorage.removeItem(SESSION_KEY); } catch {}
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Build a branded, paginated PDF from the report — no browser print chrome.
  async function handleExport() {
    if (!reportRef.current || exporting) return;
    setExporting(true);
    try {
      const { exportReportPdf } = await import("./lib/exportPdf");
      await exportReportPdf(reportRef.current, {
        title: "Media Intelligence Report",
        subtitle: `Monitoring ${health?.client || "K-Electric (KE)"}`,
        publication: analysis?.publication_name || "Newspaper coverage",
        date: new Date().toLocaleDateString(),
        filename: `media-intelligence-${new Date().toISOString().slice(0, 10)}.pdf`,
      });
    } catch (e) {
      console.error("PDF export failed", e);
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteUpload(id);
      // If the deleted analysis is the one on screen, clear the dashboard.
      if (analysis?.id === id) handleNew();
      refreshMeta();
    } catch (e) {
      /* non-fatal */
    }
  }

  async function openHistory(id) {
    try {
      setClusterFilter(null);
      const result = await getUpload(id);
      setAnalysis(result);
      try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(result)); } catch {}
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      /* ignore */
    }
  }

  const m = analysis?.metrics;
  const repSeries = history
    .map((h) => h.reputation_index)
    .filter((n) => n != null)
    .reverse();

  return (
    <div className="min-h-screen">
      {/* ── Top app bar ── */}
      <header className="sticky top-0 z-30 border-b border-border bg-card/80 backdrop-blur-md print:hidden">
        <div className="mx-auto flex h-16 max-w-[1240px] items-center gap-4 px-7">
          <div className="flex items-center gap-3">
            <div className="hidden sm:block">
              <div className="text-[15px] font-bold leading-tight tracking-[-0.01em] text-foreground">
                AI Newspaper Analyzer
              </div>
              <div className="text-[11px] text-muted-foreground">
                Media Intelligence
              </div>
            </div>
          </div>

          <div className="relative ml-2 hidden max-w-md flex-1 md:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search articles by headline…"
              className="h-9 w-full rounded-full border border-border bg-secondary pl-9 pr-12 text-[13px] text-foreground placeholder:text-muted-foreground focus:border-primary focus:bg-card focus:outline-none"
            />
            <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-border bg-card px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              ⌘K
            </kbd>
          </div>

          <div className="ml-auto flex items-center gap-2.5">
            <span className="hidden items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-[12.5px] text-muted-foreground sm:inline-flex">
              <span
                className={cn(
                  "size-[7px] rounded-full",
                  health?.configured
                    ? "bg-positive shadow-[0_0_0_3px_var(--positive-soft)]"
                    : health === null
                      ? "bg-mixed animate-pulse"
                      : "bg-neutral"
                )}
              />
              {health?.configured ? "Live" : health === null ? "Connecting…" : "Offline"}
            </span>
            <div className="hidden rounded-full border border-border bg-card px-3 py-1.5 text-[12.5px] text-muted-foreground lg:block">
              Monitoring:{" "}
              <b className="font-semibold text-foreground">
                {health?.client || "K-Electric (KE)"}
              </b>
            </div>
            {analysis && (
              <button
                onClick={handleExport}
                disabled={exporting}
                className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-[12.5px] font-semibold text-foreground transition-colors hover:bg-secondary disabled:cursor-wait disabled:opacity-60"
              >
                <FileDown className="size-3.5" /> {exporting ? "Exporting…" : "Export"}
              </button>
            )}
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1240px] px-7 pb-[72px] pt-7">
      {/* ── Print-only report header ── */}
      {analysis && (
        <div className="mb-6 hidden items-center justify-between border-b border-border pb-4 print:flex">
          <div className="flex items-center gap-3">
            <div>
              <div className="text-lg font-bold text-foreground">
                Media Intelligence Report
              </div>
              <div className="text-[12px] text-muted-foreground">
                Monitoring{" "}
                {health?.client || "K-Electric (KE)"}
              </div>
            </div>
          </div>
          <div className="text-right text-[12px] text-muted-foreground">
            <div>{analysis.publication_name || "Newspaper coverage"}</div>
            <div>{new Date().toLocaleDateString()}</div>
          </div>
        </div>
      )}

      {/* ── Upload + history ── */}
      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-[1.1fr_1fr] print:hidden">
        <UploadPanel
          onAnalyzed={onAnalyzed}
          configured={health?.configured}
          hasResults={!!analysis}
          onNew={handleNew}
        />
        <Card>
          <CardHeader>
            <CardTitle>Recent Analyses</CardTitle>
          </CardHeader>
          <CardContent className="pt-1">
            {repSeries.length >= 2 && (
              <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-border bg-secondary/40 px-3 py-2.5">
                <div>
                  <div className="text-[11px] text-muted-foreground">
                    Reputation over time
                  </div>
                  <div className="text-[15px] font-bold tabular-nums text-foreground">
                    {repSeries[repSeries.length - 1]}
                    <span className="text-[11px] font-normal text-muted-foreground">
                      {" "}
                      / 100
                    </span>
                  </div>
                </div>
                <Sparkline values={repSeries} />
              </div>
            )}
            {history.length === 0 ? (
              <div className="py-10 text-center text-sm text-muted-foreground">
                No newspapers analyzed yet
              </div>
            ) : (
              <div className="max-h-40 overflow-y-auto overflow-x-hidden">
              {history.map((h) => (
                <div
                  key={h.id}
                  className="group -mx-3 flex w-[calc(100%+1.5rem)] items-center gap-2 rounded-md px-3 py-2.5 text-[13px] transition-colors hover:bg-secondary"
                >
                  <button
                    onClick={() => openHistory(h.id)}
                    className="flex min-w-0 flex-1 items-center justify-between gap-3 text-left"
                  >
                    <span className="truncate font-medium text-foreground">
                      {h.filename}
                    </span>
                    <span className="whitespace-nowrap text-muted-foreground">
                      {h.article_count} articles · rep {h.reputation_index ?? "–"}
                    </span>
                  </button>
                  <button
                    onClick={() => handleDelete(h.id)}
                    aria-label={`Delete ${h.filename}`}
                    title="Delete analysis"
                    className="shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:text-negative focus-visible:opacity-100 group-hover:opacity-100"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {!analysis ? (
        <Card className="mt-[18px]">
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Upload a newspaper PDF or paste article text above to generate the intelligence dashboard.
          </CardContent>
        </Card>
      ) : (
        <div className="animate-fade-in" key={analysis.id} ref={reportRef}>
          <ExecutiveSummary
            summary={analysis.executive_summary}
            reputation={m.reputation_index}
          />

          <CoverageRadar analysis={analysis} />

          <CrisisAlerts alerts={m.crisis_alerts} />

          <div className="mt-[18px] grid grid-cols-1 gap-[18px] lg:grid-cols-2">
            <SentimentDonut distribution={m.sentiment_distribution} />
            <ShareOfVoice data={m.share_of_voice} />
          </div>

          <ReputationDrivers articles={analysis.articles} />

          <CoverageImpactMap articles={analysis.articles} />

          <CoverageClusters
            clusters={m.topic_clusters}
            active={clusterFilter}
            onSelect={setClusterFilter}
          />

          <EntityInsights insights={m.entity_insights} />

          <NlpComparison comparison={m.nlp_comparison} />

          {(() => {
            const q = query.trim().toLowerCase();
            const base = analysis.articles.filter(
              (a) =>
                (!clusterFilter || a.clusters?.includes(clusterFilter)) &&
                (!q || (a.headline || "").toLowerCase().includes(q))
            );
            const FILTERS = [
              { key: "all", label: "All", test: () => true },
              {
                key: "critical",
                label: "Critical",
                test: (a) => a.risk_level === "critical",
              },
              {
                key: "negative",
                label: "Negative",
                test: (a) => a.sentiment_label === "negative",
              },
              {
                key: "front",
                label: "Front-page",
                test: (a) => a.prominence === "front_page",
              },
            ];
            const counts = Object.fromEntries(
              FILTERS.map((f) => [f.key, base.filter(f.test).length])
            );
            const active = FILTERS.find((f) => f.key === feedFilter) || FILTERS[0];
            const feed = base.filter(active.test);
            return (
              <Card className="mt-[18px]">
                <CardHeader>
                  <CardTitle className="self-center">
                    Article Feed · {feed.length}
                    {clusterFilter && (
                      <span className="text-primary-ink"> · {clusterFilter}</span>
                    )}
                    {q && (
                      <span className="text-primary-ink"> · “{query.trim()}”</span>
                    )}
                  </CardTitle>
                  <Tabs
                    value={feedView}
                    onValueChange={setFeedView}
                    className="print:hidden"
                  >
                    <TabsList>
                      <TabsTrigger value="cards">Cards</TabsTrigger>
                      <TabsTrigger value="table">Table</TabsTrigger>
                    </TabsList>
                  </Tabs>
                </CardHeader>
                <CardContent className="pt-2">
                  <div className="mb-4 flex flex-wrap gap-2 print:hidden">
                    {FILTERS.map((f) => (
                      <button
                        key={f.key}
                        onClick={() => setFeedFilter(f.key)}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12.5px] font-medium transition-colors",
                          feedFilter === f.key
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border bg-card text-muted-foreground hover:border-border-strong hover:text-foreground"
                        )}
                      >
                        {f.label}
                        <span
                          className={cn(
                            "rounded-full px-1.5 text-[10px] font-bold tabular-nums",
                            feedFilter === f.key
                              ? "bg-white/25 text-white"
                              : "bg-secondary text-muted-foreground"
                          )}
                        >
                          {counts[f.key]}
                        </span>
                      </button>
                    ))}
                  </div>
                  {feed.length === 0 ? (
                    <div className="py-10 text-center text-sm text-muted-foreground">
                      {q
                        ? "No articles match your search."
                        : feedFilter !== "all"
                          ? "No articles match this filter."
                          : clusterFilter
                            ? "No articles in this cluster."
                            : "No articles mentioning the client in this issue."}
                    </div>
                  ) : feedView === "table" ? (
                    <ArticleTable articles={feed} />
                  ) : (
                    feed.map((a, i) => <ArticleCard key={i} article={a} />)
                  )}
                </CardContent>
              </Card>
            );
          })()}
        </div>
      )}
      </main>
    </div>
  );
}
