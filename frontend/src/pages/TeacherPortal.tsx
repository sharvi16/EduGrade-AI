import React, { useCallback, useRef, useState } from "react";
import { createExam, deleteExam, listExams, getExamSubmissions } from "../api/client";
import type { Exam, Submission } from "../types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle, XCircle, Trash2, RefreshCw, ChevronDown, ChevronUp, Upload, FileText, BookOpen, PlusCircle, ListChecks } from "lucide-react";
import { cn } from "@/lib/utils";

// ── FileDrop ─────────────────────────────────────────────────────
interface FileDropProps {
  label: string;
  accept?: string;
  file: File | null;
  onChange: (f: File | null) => void;
}
const FileDrop: React.FC<FileDropProps> = ({ label, accept = "image/*,.pdf", file, onChange }) => {
  const ref = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault(); setDragging(false);
    onChange(e.dataTransfer.files[0] ?? null);
  }, [onChange]);

  return (
    <div
      className={`file-drop flex items-center justify-center p-4 min-h-20 transition-all ${dragging ? "drag-over" : ""}`}
      style={{ borderRadius: "var(--radius)" }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => ref.current?.click()}
    >
      <input ref={ref} type="file" accept={accept} className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)} />
      {file ? (
        <div className="flex items-center gap-2.5 text-sm w-full">
          <div className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: "#ede9fe" }}>
            <FileText className="h-4 w-4" style={{ color: "#7c3aed" }} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate max-w-44 font-medium text-sm">{file.name}</p>
            <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
          <button
            className="h-6 w-6 rounded-full flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-gray-100 transition-colors"
            onClick={(e) => { e.stopPropagation(); onChange(null); if (ref.current) ref.current.value = ""; }}
          >×</button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-1.5 text-muted-foreground text-sm pointer-events-none">
          <div className="h-9 w-9 rounded-full flex items-center justify-center mb-1"
            style={{ background: "#ede9fe" }}>
            <Upload className="h-4 w-4" style={{ color: "#7c3aed" }} />
          </div>
          <span className="font-medium" style={{ color: "#64748b" }}>{label}</span>
          <span className="text-xs opacity-60">Click or drag &amp; drop</span>
        </div>
      )}
    </div>
  );
};

const fmt = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

// ══════════════════════════════════════════════════════════════════
const TeacherPortal: React.FC = () => {
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [totalMarks, setTotalMarks] = useState(20);
  const [qFile, setQFile] = useState<File | null>(null);
  const [aFile, setAFile] = useState<File | null>(null);
  const [rubricMode, setRubricMode] = useState<"file" | "text">("file");
  const [rFile, setRFile] = useState<File | null>(null);
  const [rubricText, setRubricText] = useState("");
  const [creating, setCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [loadingExams, setLoadingExams] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [submissions, setSubmissions] = useState<Record<string, Submission[]>>({});
  const [loadingSubs, setLoadingSubs] = useState<Record<string, boolean>>({});

  const toggleExpand = async (examId: string) => {
    if (expanded === examId) { setExpanded(null); return; }
    setExpanded(examId);
    if (!submissions[examId]) {
      setLoadingSubs(prev => ({ ...prev, [examId]: true }));
      try {
        const subs = await getExamSubmissions(examId);
        setSubmissions(prev => ({ ...prev, [examId]: subs }));
      } finally {
        setLoadingSubs(prev => ({ ...prev, [examId]: false }));
      }
    }
  };

  const fetchExams = useCallback(async () => {
    setLoadingExams(true);
    try { const data = await listExams(); setExams(data.sort((a, b) => b.created_at.localeCompare(a.created_at))); }
    finally { setLoadingExams(false); }
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) { setCreateMsg({ type: "error", text: "Please enter an exam title." }); return; }
    setCreating(true); setCreateMsg(null);
    try {
      const fd = new FormData();
      fd.append("title", title.trim()); fd.append("subject", subject.trim());
      fd.append("total_marks", String(totalMarks));
      if (qFile) fd.append("questions_file", qFile);
      if (aFile) fd.append("answer_key_file", aFile);
      if (rubricMode === "file" && rFile) fd.append("rubric_file", rFile);
      if (rubricMode === "text") fd.append("rubric_text", rubricText);
      const exam = await createExam(fd);
      setCreateMsg({ type: "success", text: `Exam "${exam.title}" created successfully!` });
      setTitle(""); setSubject(""); setTotalMarks(20); setQFile(null); setAFile(null); setRFile(null); setRubricText("");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create exam.";
      setCreateMsg({ type: "error", text: String(msg) });
    } finally { setCreating(false); }
  };

  const handleDelete = async (examId: string) => {
    if (!window.confirm("Delete this exam? This cannot be undone.")) return;
    setDeleting(examId);
    try { await deleteExam(examId); setExams(prev => prev.filter(e => e.exam_id !== examId)); }
    finally { setDeleting(null); }
  };

  return (
    <div className="space-y-8 animate-fade-up">
      {/* ── Page header ───────────────────────────────────────── */}
      <div className="page-header">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: "linear-gradient(135deg, #ede9fe 0%, #e0f2fe 100%)", border: "1px solid rgba(124,58,237,0.15)" }}>
            <BookOpen className="h-5 w-5" style={{ color: "#7c3aed" }} />
          </div>
          <h1 className="text-gradient" style={{ fontSize: "1.6rem", fontWeight: 700, letterSpacing: "-0.02em" }}>Teacher Portal</h1>
        </div>
        <p>Manage exams, upload question papers and answer keys</p>
      </div>

      <Tabs defaultValue="create" onValueChange={(v) => { if (v === "view") fetchExams(); }}>
        <TabsList className="grid w-full grid-cols-2 max-w-sm h-10 p-1"
          style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
          <TabsTrigger value="create" className="flex items-center gap-1.5 text-sm">
            <PlusCircle className="h-3.5 w-3.5" />New Exam
          </TabsTrigger>
          <TabsTrigger value="view" className="flex items-center gap-1.5 text-sm">
            <ListChecks className="h-3.5 w-3.5" />Saved Exams
          </TabsTrigger>
        </TabsList>

        {/* ── CREATE ──────────────────────────────────────────── */}
        <TabsContent value="create" className="mt-6">
          <div className="content-card-elevated p-6">
            <div className="flex items-center gap-2 mb-6">
              <div className="h-7 w-7 rounded-lg flex items-center justify-center"
                style={{ background: "#ede9fe" }}>
                <PlusCircle className="h-4 w-4" style={{ color: "#7c3aed" }} />
              </div>
              <h2 className="font-semibold text-base">Create New Exam</h2>
            </div>

            <form onSubmit={handleCreate} className="space-y-6">
              {/* Title + Subject */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="title" className="text-sm font-medium">Exam Title <span className="text-red-500">*</span></Label>
                  <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Economics Unit Test 1"
                    style={{ background: "#f8fafc", border: "1px solid var(--border)" }} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="subject" className="text-sm font-medium">Subject</Label>
                  <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)}
                    placeholder="e.g. Economics"
                    style={{ background: "#f8fafc", border: "1px solid var(--border)" }} />
                </div>
              </div>

              {/* Total Marks */}
              <div className="space-y-1.5 max-w-36">
                <Label htmlFor="marks" className="text-sm font-medium">Total Marks</Label>
                <Input id="marks" type="number" min={1} max={500} value={totalMarks}
                  onChange={(e) => setTotalMarks(Number(e.target.value))}
                  style={{ background: "#f8fafc", border: "1px solid var(--border)" }} />
              </div>

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
                <span className="section-label">Documents</span>
                <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
              </div>

              {/* Uploads */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-sm font-medium flex items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />Question Paper
                  </Label>
                  <FileDrop label="Upload question paper" file={qFile} onChange={setQFile} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-sm font-medium flex items-center gap-1.5">
                    <CheckCircle className="h-3.5 w-3.5 text-muted-foreground" />Answer Key / Model Answer
                  </Label>
                  <FileDrop label="Upload answer key" file={aFile} onChange={setAFile} />
                </div>
              </div>

              {/* Rubric */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Rubric / Marking Scheme</Label>
                <div className="flex gap-2">
                  {[
                    { mode: "file" as const, icon: <Upload className="h-3 w-3" />, label: "Upload File" },
                    { mode: "text" as const, icon: <FileText className="h-3 w-3" />, label: "Type Manually" },
                  ].map(({ mode, icon, label: ml }) => (
                    <button key={mode} type="button" onClick={() => setRubricMode(mode)}
                      className={cn(
                        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all",
                        rubricMode === mode
                          ? "text-purple-700 border-purple-300 bg-purple-50"
                          : "border-gray-200 bg-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                      )}
                    >{icon}{ml}</button>
                  ))}
                </div>
                {rubricMode === "file"
                  ? <FileDrop label="Upload rubric / marking scheme" file={rFile} onChange={setRFile} />
                  : (
                    <Textarea rows={5} placeholder="Paste or type the rubric here..."
                      value={rubricText} onChange={(e) => setRubricText(e.target.value)}
                      style={{ background: "#f8fafc", border: "1px solid var(--border)", resize: "vertical" }} />
                  )
                }
              </div>

              {/* Feedback */}
              {createMsg && (
                <div className={createMsg.type === "success" ? "feedback-positive" : ""}
                  style={createMsg.type === "error" ? { background: "#fef2f2", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "var(--radius)", padding: "12px 16px", color: "#991b1b" } : {}}>
                  <div className="flex items-start gap-2">
                    {createMsg.type === "success"
                      ? <CheckCircle style={{ width: 16, height: 16, color: "#10b981", marginTop: 1, flexShrink: 0 }} />
                      : <XCircle style={{ width: 16, height: 16, color: "#ef4444", marginTop: 1, flexShrink: 0 }} />}
                    <span className="text-sm">{createMsg.text}</span>
                  </div>
                </div>
              )}

              {/* Submit */}
              <div className="flex items-center gap-4 pt-1">
                <button type="submit" disabled={creating}
                  className="btn-primary btn-primary-gradient"
                  style={{ opacity: creating ? 0.7 : 1 }}>
                  {creating ? (
                    <><span style={{ display: "inline-block", width: 14, height: 14, border: "2px solid rgba(255,255,255,0.5)", borderTopColor: "white", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />Extracting &amp; Saving...</>
                  ) : (
                    <><PlusCircle style={{ width: 15, height: 15 }} />Create Exam</>
                  )}
                </button>
                {creating && (
                  <p className="text-xs text-muted-foreground">AI is extracting text — this may take 10–30 s.</p>
                )}
              </div>
            </form>
          </div>
        </TabsContent>

        {/* ── VIEW ──────────────────────────────────────────────── */}
        <TabsContent value="view" className="mt-6">
          <div className="content-card-elevated p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg flex items-center justify-center"
                  style={{ background: "#ede9fe" }}>
                  <ListChecks className="h-4 w-4" style={{ color: "#7c3aed" }} />
                </div>
                <h2 className="font-semibold text-base">Saved Exams</h2>
                {exams.length > 0 && (
                  <span className="h-5 min-w-5 px-1 rounded-full flex items-center justify-center text-xs font-bold text-white"
                    style={{ background: "#7c3aed" }}>{exams.length}</span>
                )}
              </div>
              <button className="btn-ghost text-xs gap-1.5" style={{ padding: "6px 12px" }}
                onClick={fetchExams} disabled={loadingExams}>
                <RefreshCw style={{ width: 13, height: 13, animation: loadingExams ? "spin 0.7s linear infinite" : "none" }} />
                {loadingExams ? "Refreshing..." : "Refresh"}
              </button>
            </div>

            {loadingExams && (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="flex items-center gap-3 p-4 rounded-xl" style={{ border: "1px solid var(--border)" }}>
                    <Skeleton className="h-10 w-10 rounded-lg" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-40 rounded" />
                      <Skeleton className="h-3 w-24 rounded" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!loadingExams && exams.length === 0 && (
              <div className="text-center py-14">
                <div className="h-14 w-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
                  style={{ background: "#ede9fe", border: "1px solid rgba(124,58,237,0.15)" }}>
                  <BookOpen className="h-6 w-6" style={{ color: "#7c3aed" }} />
                </div>
                <p className="font-medium text-muted-foreground">No exams yet</p>
                <p className="text-xs text-muted-foreground mt-1">Switch to "New Exam" tab to create one</p>
              </div>
            )}

            <div className="space-y-2">
              {exams.map((exam) => (
                <div key={exam.exam_id} className="rounded-xl transition-all overflow-hidden"
                  style={{ border: expanded === exam.exam_id ? "1px solid rgba(124,58,237,0.35)" : "1px solid var(--border)", background: "var(--card)" }}>
                  <div className="flex items-center justify-between p-4 cursor-pointer select-none hover:bg-slate-50/50"
                    onClick={() => toggleExpand(exam.exam_id)}>
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-9 w-9 rounded-lg flex items-center justify-center shrink-0 text-sm font-bold"
                        style={{ background: "#ede9fe", color: "#7c3aed" }}>
                        {exam.title.charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-sm truncate">{exam.title}</p>
                        <div className="flex flex-wrap items-center gap-1.5 mt-1">
                          {exam.subject && (
                            <span className="badge-teal">{exam.subject}</span>
                          )}
                          <span className="badge-purple">{exam.total_marks} marks</span>
                          <span className="text-xs text-muted-foreground hidden sm:inline">{fmt(exam.created_at)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4 shrink-0">
                      <Button variant="ghost" size="sm"
                        className="h-8 w-8 p-0 text-red-400 hover:text-red-600 hover:bg-red-50"
                        onClick={(e) => { e.stopPropagation(); handleDelete(exam.exam_id); }}
                        disabled={deleting === exam.exam_id}>
                        {deleting === exam.exam_id
                          ? <span style={{ display: "inline-block", width: 13, height: 13, border: "2px solid currentColor", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
                          : <Trash2 className="h-3.5 w-3.5" />}
                      </Button>
                      <div className="h-7 w-7 rounded-md flex items-center justify-center"
                        style={{ background: "#f1f5f9" }}>
                        {expanded === exam.exam_id
                          ? <ChevronUp className="h-4 w-4 text-muted-foreground" />
                          : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                      </div>
                    </div>
                  </div>

                  {expanded === exam.exam_id && (
                    <div className="mx-4 mb-4 rounded-xl p-4 space-y-6 animate-fade-up"
                      style={{ background: "#f8fafc", border: "1px solid var(--border)" }}>

                      {/* Submissions Dashboard */}
                      <section>
                        <div className="flex items-center justify-between mb-3 border-b pb-2" style={{ borderColor: "var(--border)" }}>
                          <p className="font-semibold text-base text-slate-800">Student Submissions</p>
                          <span className="badge-purple">{submissions[exam.exam_id]?.length || 0} received</span>
                        </div>
                        {loadingSubs[exam.exam_id] ? (
                          <div className="animate-pulse flex space-x-4 p-4 bg-white rounded-lg border">
                            <div className="flex-1 space-y-3 py-1">
                              <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                              <div className="h-3 bg-slate-200 rounded w-1/2"></div>
                            </div>
                          </div>
                        ) : submissions[exam.exam_id]?.length > 0 ? (
                          <div className="space-y-3">
                            {submissions[exam.exam_id].map(sub => (
                              <div key={sub.submission_id} className="p-3.5 bg-white rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all hover:shadow-sm">
                                <div>
                                  <p className="font-bold text-slate-900">{sub.student_name}</p>
                                  <p className="text-xs text-muted-foreground mt-0.5">{fmt(sub.submitted_at)}</p>
                                </div>
                                <div className="flex items-center gap-5 sm:gap-6 bg-slate-50 px-4 py-2 rounded-md border">
                                  {sub.written ? (
                                    <div className="text-center">
                                      <span className="block text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-0.5">Written</span>
                                      <span className="font-bold text-slate-700">{sub.written.marks_obtained}<span className="text-xs font-normal text-slate-400">/{sub.written.total_marks}</span></span>
                                    </div>
                                  ) : (
                                    <div className="text-center text-xs text-muted-foreground">No written</div>
                                  )}

                                  {sub.viva ? (
                                    <div className="text-center border-l pl-5 sm:pl-6 border-slate-200">
                                      <span className="block text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-0.5">Viva</span>
                                      <span className="font-bold text-slate-700">{sub.viva.marks_obtained}<span className="text-xs font-normal text-slate-400">/{sub.viva.total_marks}</span></span>
                                    </div>
                                  ) : (
                                    <div className="text-center border-l pl-5 sm:pl-6 border-slate-200 text-xs text-muted-foreground">
                                      <span className="block text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-0.5">Viva</span>
                                      Pending
                                    </div>
                                  )}

                                  <div className="text-center border-l pl-5 sm:pl-6 border-slate-200">
                                    <span className="block text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-0.5">Grade</span>
                                    <span className="font-black text-primary text-lg" style={{ lineHeight: 1 }}>{sub.written?.grade || "-"}</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-6 bg-white rounded-lg border border-dashed">
                            <p className="text-sm text-slate-500 font-medium">No student submissions yet.</p>
                            <p className="text-xs text-slate-400 mt-1">When students submit answers, they will appear here.</p>
                          </div>
                        )}
                      </section>

                      {exam.questions && (
                        <section>
                          <p className="section-label mb-2">Questions</p>
                          <pre className="text-xs whitespace-pre-wrap font-mono rounded-lg p-3 max-h-48 overflow-y-auto leading-relaxed"
                            style={{ background: "#f1f5f9", border: "1px solid var(--border)", color: "#1e1b4b" }}>{exam.questions}</pre>
                        </section>
                      )}
                      {exam.answer_key && (
                        <section>
                          <p className="section-label mb-2">Answer Key</p>
                          <pre className="text-xs whitespace-pre-wrap font-mono rounded-lg p-3 max-h-48 overflow-y-auto leading-relaxed"
                            style={{ background: "#f1f5f9", border: "1px solid var(--border)", color: "#1e1b4b" }}>{exam.answer_key}</pre>
                        </section>
                      )}
                      {exam.rubrics && (
                        <section>
                          <p className="section-label mb-2">Rubric</p>
                          <pre className="text-xs whitespace-pre-wrap font-mono rounded-lg p-3 max-h-48 overflow-y-auto leading-relaxed"
                            style={{ background: "#f1f5f9", border: "1px solid var(--border)", color: "#1e1b4b" }}>{exam.rubrics}</pre>
                        </section>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default TeacherPortal;
