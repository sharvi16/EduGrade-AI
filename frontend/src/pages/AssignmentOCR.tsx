import React, { useEffect, useRef, useState } from "react";
import { extractText } from "../api/client";
import type { OcrResult } from "../types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Upload, FileText, Download, RotateCcw, Sparkles, ScanText, AlignLeft, Wand2 } from "lucide-react";

const AssignmentOCR: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [polish, setPolish] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OcrResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Create preview URL and clean up on unmount / file change
  useEffect(() => {
    if (!file || !file.type.startsWith("image/")) { setPreviewUrl(null); return; }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const handleExtract = async () => {
    if (!file) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const fd = new FormData(); fd.append("file", file); fd.append("polish", String(polish));
      const data = await extractText(fd); setResult(data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Extraction failed.";
      setError(String(msg));
    } finally { setLoading(false); }
  };

  const handleDownload = () => {
    if (!result) return;
    const text = result.final_text || result.raw_text;
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = (file?.name.replace(/\.[^.]+$/, "") ?? "extracted") + "_extracted.txt";
    a.click(); URL.revokeObjectURL(url);
  };

  const reset = () => {
    setFile(null); setResult(null); setError(null); setShowRaw(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const displayText = showRaw ? result?.raw_text : result?.final_text;
  const wordCount = displayText?.trim().split(/\s+/).filter(Boolean).length ?? 0;
  const hasRawPolished = result && result.raw_text !== result.final_text;

  return (
    <div className="space-y-8 animate-fade-up">

      {/* ── Page Header ─────────────────────────────────────── */}
      <div className="flex items-start gap-4">
        <div
          className="h-12 w-12 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: "linear-gradient(135deg, #ede9fe 0%, #e0f2fe 100%)", border: "1px solid rgba(124,58,237,0.15)" }}
        >
          <ScanText style={{ width: 22, height: 22, color: "var(--primary)" }} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gradient">Assignment OCR</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">Extract text from handwritten assignments using AI vision</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* ── Upload Panel ──────────────────────────────────── */}
        <Card className="content-card-elevated" >
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <span className="h-6 w-6 rounded-md flex items-center justify-center text-primary" style={{ background: "#ede9fe" }}>
                <Upload style={{ width: 13, height: 13 }} />
              </span>
              Upload Document
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">

            {/* Drop Zone */}
            <div
              className={cn("file-drop large", dragging && "dragging", file && "has-file")}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) { setFile(f); setResult(null); setError(null); } }}
              onClick={() => !file && fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                accept="image/*,.pdf"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) { setFile(f); setResult(null); setError(null); } }}
              />
              {file ? (
                <div className="flex flex-col items-center gap-3 z-10">
                  {previewUrl ? (
                    <img
                      src={previewUrl}
                      alt="preview"
                      className="max-h-36 rounded-xl object-contain"
                      style={{ border: "1px solid var(--border)", boxShadow: "0 4px 16px -4px rgba(0,0,0,0.12)" }}
                    />
                  ) : (
                    <div className="h-16 w-16 rounded-2xl flex items-center justify-center" style={{ background: "#ede9fe" }}>
                      <FileText style={{ width: 28, height: 28, color: "var(--primary)" }} />
                    </div>
                  )}
                  <div className="text-center">
                    <p className="font-semibold text-sm truncate max-w-52">{file.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs"
                    style={{ border: "1px solid var(--border)", background: "#f1f5f9" }}
                    onClick={(e) => { e.stopPropagation(); reset(); }}
                  >
                    <RotateCcw style={{ width: 11, height: 11 }} />Change File
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 text-muted-foreground pointer-events-none z-10">
                  <div
                    className="h-14 w-14 rounded-2xl flex items-center justify-center mb-1"
                    style={{ background: "#f1f5f9", border: "1px solid var(--border)" }}
                  >
                    <span style={{ fontSize: 28 }}>🖊</span>
                  </div>
                  <span className="font-medium text-sm text-foreground/70">Upload handwritten assignment</span>
                  <span className="text-xs opacity-55">JPG, PNG, PDF · Click or drag &amp; drop</span>
                </div>
              )}
            </div>

            <div className="h-px" style={{ background: "var(--border)" }} />

            {/* AI Polish Toggle */}
            <div
              className="flex items-center justify-between px-4 py-3 rounded-xl"
              style={{ background: polish ? "#faf5ff" : "#fafafa", border: `1px solid ${polish ? "rgba(124,58,237,0.25)" : "var(--border)"}`, transition: "all .25s ease" }}
            >
              <div className="flex items-start gap-2.5">
                <div
                  className="h-7 w-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{ background: polish ? "#ede9fe" : "#f1f5f9" }}
                >
                  <Wand2 style={{ width: 13, height: 13, color: polish ? "var(--primary)" : "var(--muted-foreground)" }} />
                </div>
                <div>
                  <Label htmlFor="polish-toggle" className="cursor-pointer font-semibold text-sm flex items-center gap-1.5">
                    <Sparkles style={{ width: 13, height: 13, color: polish ? "var(--primary)" : "var(--muted-foreground)" }} />
                    AI Polish
                  </Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {polish ? "Grammar & formatting will be improved" : "Raw OCR output only"}
                  </p>
                </div>
              </div>
              <Switch id="polish-toggle" checked={polish} onCheckedChange={setPolish} />
            </div>

            {/* Error */}
            {error && (
              <Alert variant="destructive" style={{ borderRadius: "var(--radius-lg)" }}>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Extract button */}
            <Button
              className="w-full gap-2"
              disabled={!file || loading}
              onClick={handleExtract}
              style={{
                background: "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)",
                boxShadow: file && !loading ? "0 2px 16px rgba(124,58,237,0.35)" : "none",
              }}
            >
              {loading ? (
                <><span className="spin h-4 w-4 inline-block border-2 border-current border-t-transparent rounded-full" />Extracting Text...</>
              ) : (
                <><ScanText style={{ width: 16, height: 16 }} />Extract Text</>
              )}
            </Button>
            {loading && (
              <p className="text-xs text-muted-foreground text-center">
                AI is reading the document — please wait (10–30 s)…
              </p>
            )}
          </CardContent>
        </Card>

        {/* ── Result Panel ──────────────────────────────────── */}
        <Card className="content-card-elevated" >
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <span className="h-6 w-6 rounded-md flex items-center justify-center text-primary" style={{ background: "#ede9fe" }}>
                  <AlignLeft style={{ width: 13, height: 13 }} />
                </span>
                Extracted Text
              </CardTitle>
              {result && (
                <div className="flex items-center gap-2">
                  {/* Raw / Polished toggle */}
                  {hasRawPolished && (
                    <div className="flex rounded-lg overflow-hidden text-xs" style={{ border: "1px solid var(--border)" }}>
                      <button
                        className="px-2.5 py-1.5 transition-all font-medium flex items-center gap-1"
                        style={!showRaw ? { background: "var(--primary)", color: "#fff" } : { background: "transparent", color: "var(--muted-foreground)" }}
                        onClick={() => setShowRaw(false)}
                      >
                        <Sparkles style={{ width: 10, height: 10 }} />Polished
                      </button>
                      <button
                        className="px-2.5 py-1.5 transition-all font-medium"
                        style={showRaw ? { background: "var(--primary)", color: "#fff" } : { background: "transparent", color: "var(--muted-foreground)" }}
                        onClick={() => setShowRaw(true)}
                      >
                        Raw OCR
                      </button>
                    </div>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDownload}
                    className="gap-1.5 text-xs h-7"
                    style={{ border: "1px solid var(--border)", background: "#f8fafc" }}
                  >
                    <Download style={{ width: 12, height: 12 }} />Download
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {/* Empty state */}
            {!result && !loading && (
              <div className="flex flex-col items-center justify-center h-64 gap-3">
                <div
                  className="h-16 w-16 rounded-2xl flex items-center justify-center"
                  style={{ background: "#f8fafc", border: "1px solid var(--border)" }}
                >
                  <FileText style={{ width: 28, height: 28, color: "var(--muted-foreground)", opacity: 0.35 }} />
                </div>
                <div className="text-center">
                  <p className="text-muted-foreground text-sm font-medium">No text extracted yet</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">Upload a file and click "Extract Text"</p>
                </div>
              </div>
            )}

            {/* Loading skeleton */}
            {loading && (
              <div className="space-y-3 pt-1">
                {Array.from({ length: 10 }).map((_, i) => (
                  <Skeleton
                    key={i}
                    className="h-3 rounded"
                    style={{ width: `${48 + (i * 17) % 45}%` }}
                  />
                ))}
              </div>
            )}

            {/* Result text */}
            {result && displayText && (
              <div className="space-y-4 animate-fade-in">
                <ScrollArea
                  className="h-72 rounded-xl p-4"
                  style={{ background: "oklch(0.10 0.025 264 / 70%)", border: "1px solid var(--border)" }}
                >
                  <pre className="text-sm whitespace-pre-wrap font-mono leading-7">{displayText}</pre>
                </ScrollArea>

                {/* Footer stats */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge
                      className="text-xs gap-1"
                      style={{ background: "#ede9fe", color: "#7c3aed", border: "1px solid rgba(124,58,237,0.2)" }}
                    >
                      <AlignLeft style={{ width: 10, height: 10 }} />
                      {wordCount} words
                    </Badge>
                    {!showRaw && polish && (
                      <Badge
                        className="text-xs gap-1"
                        style={{ background: "#e0f2fe", color: "#0ea5e9", border: "1px solid rgba(14,165,233,0.2)" }}
                      >
                        <Sparkles style={{ width: 10, height: 10 }} />AI Polished
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AssignmentOCR;


