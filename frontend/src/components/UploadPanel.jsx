import React, { useRef, useState } from "react";
import { Upload, Loader2, AlertCircle, Plus } from "lucide-react";
import { uploadPdf, analyzeText } from "../api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export default function UploadPanel({ onAnalyzed, configured, hasResults, onNew }) {
  const inputRef = useRef(null);
  const [mode, setMode] = useState("pdf"); // "pdf" | "text"
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [text, setText] = useState("");

  async function run(fn, label) {
    setError(null);
    setBusy(true);
    setFileName(label);
    try {
      onAnalyzed(await fn());
      setText("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function handleFile(file) {
    if (!file) return;
    run(() => uploadPdf(file), file.name);
  }

  function handleText() {
    if (text.trim().length < 40) {
      setError("Please paste at least a few sentences of article text.");
      return;
    }
    run(() => analyzeText(text.trim()), "Pasted text");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="self-center">Analyze Coverage</CardTitle>
        <div className="flex items-center gap-2">
          <Tabs value={mode} onValueChange={(v) => !busy && !hasResults && setMode(v)}>
            <TabsList className={cn(hasResults && "pointer-events-none opacity-40")}>
              <TabsTrigger value="pdf" disabled={hasResults}>Upload PDF</TabsTrigger>
              <TabsTrigger value="text" disabled={hasResults}>Paste text</TabsTrigger>
            </TabsList>
          </Tabs>
          {hasResults && (
            <button
              onClick={onNew}
              className="flex items-center gap-1.5 rounded-full border border-primary bg-primary px-3 py-1.5 text-[12.5px] font-semibold text-primary-foreground transition-opacity hover:opacity-90"
            >
              <Plus className="size-3.5" />
              New
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        {configured === false && (
          <div className="mb-4 rounded-md border border-mixed/35 bg-mixed-soft px-3.5 py-2.5 text-[13px] text-mixed">
            No Gemini API key detected. Add <b>GEMINI_API_KEY</b> to{" "}
            <b>.env</b> and restart the backend to run analysis.
          </div>
        )}

        {mode === "pdf" ? (
          <div
            className={cn(
              "rounded-md border-[1.5px] border-dashed bg-secondary px-5 py-7 text-center transition-all",
              hasResults
                ? "cursor-not-allowed opacity-50"
                : drag
                  ? "cursor-pointer scale-[1.005] border-primary bg-primary-soft"
                  : "cursor-pointer border-border-strong hover:border-primary hover:bg-primary-soft"
            )}
            onClick={() => !busy && !hasResults && inputRef.current?.click()}
            onDragOver={(e) => {
              if (hasResults) return;
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              if (!busy && !hasResults) handleFile(e.dataTransfer.files?.[0]);
            }}
          >
            {busy ? (
              <div>
                <Loader2 className="mx-auto mb-2 size-6 animate-spin text-primary" />
                <div className="text-[15px] font-semibold text-foreground">
                  Analyzing {fileName}…
                </div>
                <div className="mt-1 text-[13px] text-muted-foreground">
                  Scanning pages and judging sentiment
                </div>
              </div>
            ) : (
              <div>
                <div className="mx-auto mb-3 grid size-10 place-items-center rounded-[11px] border border-border bg-card text-primary">
                  <Upload className="size-5" />
                </div>
                <div className="text-[15px] font-semibold text-foreground">
                  Drop a newspaper PDF here
                </div>
                <div className="mt-1.5 text-[13px] text-muted-foreground">
                  or click to browse · text or scanned PDFs
                </div>
              </div>
            )}
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              disabled={hasResults}
              onChange={(e) => !hasResults && handleFile(e.target.files?.[0])}
            />
          </div>
        ) : (
          <div>
            <textarea
              className="min-h-[150px] w-full resize-y rounded-md border border-border-strong bg-secondary px-3.5 py-3 text-sm leading-relaxed text-foreground transition-colors focus:border-primary focus:bg-card focus:outline-none"
              placeholder="Paste a newspaper article (or several) here — headline and body text — then click Analyze."
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={busy || hasResults}
              rows={7}
            />
            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="text-[13px] text-muted-foreground tabular-nums">
                {text.trim().length} characters
              </span>
              <Button onClick={handleText} disabled={busy || hasResults || !configured}>
                {busy ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Analyzing…
                  </>
                ) : (
                  "Analyze text"
                )}
              </Button>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-2.5 flex items-center gap-1.5 text-[13px] text-negative">
            <AlertCircle className="size-3.5" /> {error}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
