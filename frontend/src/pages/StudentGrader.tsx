import React, { useCallback, useEffect, useRef, useState } from "react";
import { listExams, gradeImage, gradeText, generateVivaQuestions, gradeViva, gradeVivaFail, proctorStart, proctorDeleteSession, proctorCheckFrame, getStudentSubmission } from "../api/client";
import type { Exam, GradeResult, VivaQA, VivaQuestion, VivaResult } from "../types";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { CheckCircle, AlertTriangle, Upload, FileText, ChevronLeft, ChevronRight, Award, GraduationCap, Mic, RotateCcw, ArrowRight, Camera, CameraOff } from "lucide-react";

// ── Grade colour logic ────────────────────────────────────────────
const gradeStyle = (g: string): { bg: string; text: string; glow: string } => {
  const u = g.toUpperCase();
  if (u.startsWith("A")) return { bg: "oklch(0.66 0.19 155 / 18%)", text: "#10b981", glow: "oklch(0.66 0.19 155 / 40%)" };
  if (u.startsWith("B")) return { bg: "oklch(0.63 0.24 255 / 18%)", text: "oklch(0.75 0.20 255)", glow: "rgba(124,58,237,0.4)" };
  if (u.startsWith("C")) return { bg: "oklch(0.78 0.18 70 / 18%)", text: "#d97706", glow: "oklch(0.78 0.18 70 / 40%)" };
  if (u === "D") return { bg: "oklch(0.70 0.18 45 / 18%)", text: "oklch(0.75 0.16 45)", glow: "oklch(0.70 0.18 45 / 40%)" };
  return { bg: "oklch(0.62 0.22 27 / 18%)", text: "oklch(0.70 0.18 27)", glow: "oklch(0.62 0.22 27 / 40%)" };
};

const GradeBadge: React.FC<{ grade?: string }> = ({ grade }) => {
  if (!grade) return null;
  const s = gradeStyle(grade);
  return (
    <span
      className="inline-flex items-center justify-center h-10 w-10 rounded-full font-bold text-sm"
      style={{ background: s.bg, color: s.text, boxShadow: `0 0 14px -2px ${s.glow}`, border: `1px solid ${s.text}33` }}
    >{grade}</span>
  );
};

// ── Breakdown table ───────────────────────────────────────────────
const Breakdown: React.FC<{ items?: Array<{ question?: string; criterion?: string; marks_awarded: number; max_marks: number; comment: string }> }> = ({ items }) => {
  if (!items?.length) return null;
  return (
    <div className="overflow-x-auto rounded-xl mt-3" style={{ border: "1px solid var(--border)" }}>
      <table className="w-full text-sm">
        <thead style={{ background: "#f8fafc" }}>
          <tr>
            <th className="text-left px-4 py-2.5 font-medium text-muted-foreground text-xs uppercase tracking-wide">Criterion</th>
            <th className="px-4 py-2.5 font-medium text-xs uppercase tracking-wide text-muted-foreground text-center w-24">Marks</th>
            <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wide text-muted-foreground">Comment</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row, i) => (
            <tr key={i} className="border-t transition-colors" style={{ borderColor: "var(--border)" }}>
              <td className="px-4 py-3 font-medium text-sm">{row.question ?? row.criterion ?? `Q${i + 1}`}</td>
              <td className="px-4 py-3 text-center">
                <span
                  className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-bold"
                  style={
                    row.marks_awarded === row.max_marks
                      ? { background: "oklch(0.66 0.19 155 / 15%)", color: "#10b981", border: "1px solid oklch(0.66 0.19 155 / 30%)" }
                      : { background: "#f1f5f9", color: "var(--muted-foreground)", border: "1px solid var(--border)" }
                  }
                >{row.marks_awarded}/{row.max_marks}</span>
              </td>
              <td className="px-4 py-3 text-muted-foreground text-sm leading-relaxed">{row.comment}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ── Step type ─────────────────────────────────────────────────────
type Step = "select-exam" | "submit-answer" | "grading" | "result" | "viva" | "final";
const STEP_LABELS = ["Select Exam", "Submit", "Results", "Viva", "Final"];
const STEP_KEYS: Step[] = ["select-exam", "submit-answer", "result", "viva", "final"];

// ── Spinner helper ────────────────────────────────────────────────
const Spinner = () => (
  <span className="spin h-4 w-4 inline-block border-2 border-current border-t-transparent rounded-full" />
);

// ══════════════════════════════════════════════════════════════════
const StudentGrader: React.FC = () => {
  const { user } = useAuth();
  const studentName = user?.name || "Unknown Student";
  const [step, setStep] = useState<Step>("select-exam");
  const [exams, setExams] = useState<Exam[]>([]);
  const [loadingExams, setLoadingExams] = useState(false);
  const [checkingSubmission, setCheckingSubmission] = useState(false);
  const [selectedExam, setSelectedExam] = useState<Exam | null>(null);
  const [answerMode, setAnswerMode] = useState<"upload" | "type">("upload");
  const [answerFile, setAnswerFile] = useState<File | null>(null);
  const [answerText, setAnswerText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [gradeResult, setGradeResult] = useState<GradeResult | null>(null);
  const [extractedAnswer, setExtractedAnswer] = useState("");
  const [gradeError, setGradeError] = useState<string | null>(null);
  const [vivaQuestions, setVivaQuestions] = useState<VivaQuestion[]>([]);
  const [vivaAnswers, setVivaAnswers] = useState<string[]>([]);
  const [currentQ, setCurrentQ] = useState(0);
  const [generatingViva, setGeneratingViva] = useState(false);
  const [gradingViva, setGradingViva] = useState(false);
  const [vivaResult, setVivaResult] = useState<VivaResult | null>(null);

  // ── Camera-based proctoring ──────────────────────────────────
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const proctorIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const proctorStreamRef = useRef<MediaStream | null>(null);
  const [proctorSessionId, setProctorSessionId] = useState<string | null>(null);
  const [proctorWarnings, setProctorWarnings] = useState(0);
  const [proctorTerminated, setProctorTerminated] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [proctorMessage, setProctorMessage] = useState("");
  const [proctorAction, setProctorAction] = useState<"ok" | "away" | "warning" | "terminated">("ok");
  // Keep backward-compat for viva-terminated guard
  const vivaTerminated = proctorTerminated;

  // ── Camera helpers ───────────────────────────────────────────
  const stopCamera = useCallback(() => {
    if (proctorIntervalRef.current) {
      clearInterval(proctorIntervalRef.current);
      proctorIntervalRef.current = null;
    }
    proctorStreamRef.current?.getTracks().forEach(t => t.stop());
    proctorStreamRef.current = null;
    setCameraReady(false);
  }, []);

  // Start camera + polling when viva begins
  useEffect(() => {
    if (step !== "viva" || !proctorSessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }
        proctorStreamRef.current = stream;
        if (videoRef.current) { videoRef.current.srcObject = stream; videoRef.current.play(); }
        setCameraReady(true); setCameraError(null);
        // Poll every 3 s — gives detector more time between checks
        proctorIntervalRef.current = setInterval(async () => {
          if (!videoRef.current || !canvasRef.current || !proctorSessionId) return;
          // Only send frame once video is actually playing and has enough data
          if (videoRef.current.readyState < HTMLMediaElement.HAVE_ENOUGH_DATA) return;
          if (videoRef.current.paused || videoRef.current.ended) return;
          const canvas = canvasRef.current;
          // Capture at a slightly larger size for better Haar detection
          canvas.width = 480; canvas.height = 360;
          const ctx = canvas.getContext("2d");
          if (!ctx) return;
          ctx.drawImage(videoRef.current, 0, 0, 480, 360);
          const frame = canvas.toDataURL("image/jpeg", 0.8);
          try {
            const res = await proctorCheckFrame(proctorSessionId, frame);
            setProctorWarnings(res.warnings);
            setProctorMessage(res.message);
            setProctorAction(res.action);
            if (res.terminated) setProctorTerminated(true);
          } catch { /* silent */ }
        }, 2000);
      } catch (err) {
        console.error("Proctor init error", err);
        setCameraError("Camera access denied. Allow camera permission for proctoring.");
      }
    })();
    return () => { cancelled = true; stopCamera(); };
  }, [step, proctorSessionId, stopCamera]);

  // Auto-terminate when proctoring flags termination
  useEffect(() => {
    if (!proctorTerminated || !selectedExam || !studentName) return;

    // Prevent duplicated calls
    if (vivaResult?.marks_obtained === 0) return;

    stopCamera();
    const reason = "Viva terminated automatically by AI due to sustained violation (looking away / no face detected). You scored 0 on the Viva.";

    // Call backend to hard-fail the student so they can't simply refresh the page!
    gradeVivaFail(selectedExam.exam_id, studentName, reason)
      .then(res => {
        setVivaResult(res);
        setStep("final");
      })
      .catch(err => {
        console.error("Failed to sync fail state:", err);
        // Fallback UI
        const tm = selectedExam?.total_marks ?? 10;
        setVivaResult({
          marks_obtained: 0,
          total_marks: tm,
          breakdown: [],
          overall_feedback: reason
        });
        setStep("final");
      });
  }, [proctorTerminated, proctorSessionId, stopCamera, selectedExam, studentName, vivaResult]);

  useEffect(() => {
    setLoadingExams(true);
    listExams().then(data => setExams(data.sort((a: any, b: any) => b.created_at.localeCompare(a.created_at)))).finally(() => setLoadingExams(false));
  }, []);

  const handleContinueSelection = async () => {
    if (!selectedExam) return;
    setCheckingSubmission(true);
    try {
      const existing = await getStudentSubmission(selectedExam.exam_id, studentName);
      if (existing) {
        setExtractedAnswer(existing.written?.extracted_answer || "");
        setGradeResult(existing.written);
        setVivaResult(existing.viva);

        if (existing.viva) {
          setStep("final");
        } else {
          setStep("result");
        }
      }
    } catch {
      // 404 or error means no submission
      setStep("submit-answer");
    } finally {
      setCheckingSubmission(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedExam) return;
    setStep("grading"); setGradeError(null);
    try {
      if (answerMode === "upload" && answerFile) {
        const fd = new FormData(); fd.append("exam_id", selectedExam.exam_id); fd.append("student_name", studentName); fd.append("answer_file", answerFile);
        const res = await gradeImage(fd); setExtractedAnswer(res.extracted_answer ?? ""); setGradeResult(res);
      } else {
        const res = await gradeText(selectedExam.exam_id, studentName, answerText); setExtractedAnswer(answerText); setGradeResult(res);
      }
      setStep("result");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Grading failed.";
      setGradeError(String(msg)); setStep("submit-answer");
    }
  };

  const handleStartViva = async () => {
    if (!selectedExam) return;
    setGeneratingViva(true);
    setProctorWarnings(0); setProctorTerminated(false); setProctorMessage("");
    setProctorAction("ok"); setCameraError(null); setCameraReady(false);
    try {
      const [{ questions }, proctorSession] = await Promise.all([
        generateVivaQuestions(selectedExam.exam_id, extractedAnswer),
        proctorStart(selectedExam.exam_id, selectedExam.exam_id),
      ]);
      setVivaQuestions(questions); setVivaAnswers(Array(questions.length).fill(""));
      setCurrentQ(0); setProctorSessionId(proctorSession.session_id);
      setStep("viva");
    } finally { setGeneratingViva(false); }
  };

  const handleSubmitViva = async () => {
    if (!selectedExam) return;
    setGradingViva(true);
    stopCamera();
    if (proctorSessionId) proctorDeleteSession(proctorSessionId).catch(() => { });
    try {
      const qa_pairs: VivaQA[] = vivaQuestions.map((q, i) => ({ ...q, student_answer: vivaAnswers[i] ?? "" }));
      const res = await gradeViva(selectedExam.exam_id, studentName, extractedAnswer, qa_pairs);
      setVivaResult(res); setStep("final");
    } finally { setGradingViva(false); }
  };

  const reset = () => {
    stopCamera();
    if (proctorSessionId) proctorDeleteSession(proctorSessionId).catch(() => { });
    setStep("select-exam"); setSelectedExam(null); setAnswerFile(null); setAnswerText("");
    setGradeResult(null); setExtractedAnswer(""); setGradeError(null);
    setVivaQuestions([]); setVivaAnswers([]); setVivaResult(null);
    setProctorTerminated(false); setProctorSessionId(null); setProctorWarnings(0);
    setProctorMessage(""); setCameraError(null); setCameraReady(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const stepIndex = STEP_KEYS.indexOf(step === "grading" ? "submit-answer" : step);
  const pct = gradeResult ? (gradeResult.percentage ?? (gradeResult.marks_obtained / gradeResult.total_marks * 100)) : 0;

  // ════════════════════════ RENDER ═════════════════════════════════
  return (
    <div className="space-y-8 animate-fade-up">

      {/* ── Page Header ─────────────────────────────────────── */}
      <div className="flex items-start gap-4">
        <div
          className="h-12 w-12 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: "linear-gradient(135deg, rgba(124,58,237,0.2) 0%, oklch(0.68 0.18 195 / 15%) 100%)", border: "1px solid rgba(124,58,237,0.25)" }}
        >
          <GraduationCap style={{ width: 22, height: 22, color: "var(--primary)" }} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gradient">Student Grader</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">Submit your answer, get instant AI grading &amp; a live viva</p>
          <div className="mt-2 text-xs font-medium px-2 py-1 bg-secondary/60 text-secondary-foreground rounded-md inline-flex items-center gap-1.5 border border-border">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
            Submitting as: <span className="font-bold">{studentName}</span>
          </div>
        </div>
      </div>

      {/* ── Step Progress ────────────────────────────────────── */}
      <div className="flex items-center max-w-xl">
        {STEP_LABELS.map((label, i) => {
          const active = stepIndex === i;
          const done = stepIndex > i;
          return (
            <React.Fragment key={label}>
              <div className="flex flex-col items-center gap-1.5">
                <div className={cn("step-dot", done && "done", active && "active")}>
                  {done ? <CheckCircle style={{ width: 14, height: 14 }} /> : i + 1}
                </div>
                <span className={cn("text-xs whitespace-nowrap hidden sm:block transition-colors", active ? "text-foreground font-semibold" : "text-muted-foreground")}>
                  {label}
                </span>
              </div>
              {i < STEP_LABELS.length - 1 && (
                <div
                  className="flex-1 h-px mx-2 rounded-full transition-all duration-500"
                  style={{ background: done ? "var(--primary)" : "#e2e8f0" }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* ══════ SELECT EXAM ══════════════════════════════════ */}
      {step === "select-exam" && (
        <Card className="content-card-elevated page-section" >
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <span className="h-6 w-6 rounded-md flex items-center justify-center text-primary" style={{ background: "#ede9fe" }}>
                <FileText style={{ width: 14, height: 14 }} />
              </span>
              Choose an Exam
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {loadingExams ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="flex items-center gap-3 p-4 rounded-xl" style={{ border: "1px solid var(--border)" }}>
                    <Skeleton className="h-10 w-10 rounded-lg shrink-0" />
                    <div className="flex-1 space-y-2"><Skeleton className="h-3.5 w-36 rounded" /><Skeleton className="h-3 w-20 rounded" /></div>
                  </div>
                ))}
              </div>
            ) : exams.length === 0 ? (
              <div className="text-center py-12">
                <div className="h-12 w-12 rounded-xl mx-auto mb-3 flex items-center justify-center" style={{ background: "#faf5ff", border: "1px solid rgba(124,58,237,0.15)" }}>
                  <FileText style={{ width: 20, height: 20, color: "var(--muted-foreground)" }} />
                </div>
                <p className="text-muted-foreground font-medium text-sm">No exams available</p>
                <p className="text-xs text-muted-foreground/60 mt-1">Ask your teacher to create one first</p>
              </div>
            ) : (
              <div className="space-y-2">
                {exams.map(exam => (
                  <div
                    key={exam.exam_id}
                    className={cn("exam-card flex items-center justify-between", selectedExam?.exam_id === exam.exam_id && "selected")}
                    onClick={() => setSelectedExam(exam)}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className="h-9 w-9 rounded-lg flex items-center justify-center shrink-0 text-sm font-bold"
                        style={{ background: "#ede9fe", color: "var(--primary)" }}
                      >
                        {exam.title.charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-sm truncate">{exam.title}</p>
                        <div className="flex flex-wrap items-center gap-1.5 mt-1">
                          {exam.subject && (
                            <Badge className="text-xs h-4.5 px-1.5" style={{ background: "#e0f2fe", color: "#0ea5e9", border: "1px solid rgba(14,165,233,0.2)" }}>
                              {exam.subject}
                            </Badge>
                          )}
                          <Badge className="text-xs h-4.5 px-1.5" style={{ color: "var(--primary)", border: "1px solid rgba(124,58,237,0.3)", background: "transparent" }}>
                            {exam.total_marks} marks
                          </Badge>
                        </div>
                      </div>
                    </div>
                    {selectedExam?.exam_id === exam.exam_id && (
                      <CheckCircle style={{ width: 18, height: 18, color: "var(--primary)", flexShrink: 0 }} />
                    )}
                  </div>
                ))}
              </div>
            )}

            <Button
              disabled={!selectedExam || checkingSubmission}
              onClick={handleContinueSelection}
              className="gap-2"
              style={{ width: "100%", height: "2.75rem", background: "linear-gradient(135deg, var(--primary) 0%, oklch(0.68 0.18 250) 100%)", boxShadow: "0 4px 14px rgba(124,58,237,0.25)" }}
            >
              {checkingSubmission ? (
                <><span style={{ display: "inline-block", width: 14, height: 14, border: "2px solid rgba(255,255,255,0.5)", borderTopColor: "white", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} /> Checking Status...</>
              ) : (
                <>Continue to Submission <ArrowRight style={{ width: 16, height: 16 }} /></>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ══════ SUBMIT ANSWER ════════════════════════════════ */}
      {(step === "submit-answer" || step === "grading") && (
        <Card className="content-card-elevated page-section" >
          <CardHeader className="pb-4">
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-base font-semibold">
                Submit Your Answer
                {selectedExam && <span className="font-normal text-muted-foreground ml-2 text-sm">— {selectedExam.title}</span>}
              </CardTitle>
              {selectedExam && (
                <Badge
                  className="shrink-0 text-xs"
                  style={{ background: "#ede9fe", color: "var(--primary)", border: "1px solid rgba(124,58,237,0.25)" }}
                >
                  {selectedExam.total_marks} marks
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Mode toggle */}
            <div className="flex gap-2">
              {(["upload", "type"] as const).map(mode => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setAnswerMode(mode)}
                  className={cn("flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium border transition-all", answerMode === mode
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-border bg-transparent text-muted-foreground hover:text-foreground")}
                >
                  {mode === "upload" ? <><Upload style={{ width: 12, height: 12 }} />Upload Handwritten</> : <><FileText style={{ width: 12, height: 12 }} />Type Answer</>}
                </button>
              ))}
            </div>

            {answerMode === "upload" ? (
              <div
                className={cn("file-drop large", answerFile && "has-file")}
                onClick={() => fileRef.current?.click()}
              >
                <input ref={fileRef} type="file" accept="image/*,.pdf" className="hidden" onChange={(e) => setAnswerFile(e.target.files?.[0] ?? null)} />
                {answerFile ? (
                  <div className="flex items-center gap-3 z-10">
                    <div className="h-9 w-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: "#ede9fe" }}>
                      <FileText style={{ width: 18, height: 18, color: "var(--primary)" }} />
                    </div>
                    <div>
                      <p className="font-medium text-sm truncate max-w-48">{answerFile.name}</p>
                      <p className="text-xs text-muted-foreground">{(answerFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      className="ml-auto h-7 w-7 rounded-full flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                      onClick={(e) => { e.stopPropagation(); setAnswerFile(null); if (fileRef.current) fileRef.current.value = ""; }}
                    >×</button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 text-muted-foreground pointer-events-none z-10">
                    <div className="h-12 w-12 rounded-2xl flex items-center justify-center mb-1" style={{ background: "#f1f5f9" }}>
                      <Upload style={{ width: 20, height: 20 }} />
                    </div>
                    <span className="font-medium text-sm text-foreground/70">Upload your answer sheet</span>
                    <span className="text-xs opacity-60">JPG, PNG, PDF · Click or drag &amp; drop</span>
                  </div>
                )}
              </div>
            ) : (
              <Textarea
                rows={10}
                placeholder="Type your full answer here..."
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                style={{ background: "#f8fafc", border: "1px solid var(--border)", resize: "vertical" }}
              />
            )}

            {gradeError && (
              <Alert variant="destructive" style={{ borderRadius: "var(--radius-lg)" }}>
                <AlertDescription>{gradeError}</AlertDescription>
              </Alert>
            )}

            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={() => setStep("select-exam")}
                className="gap-1.5"
                style={{ border: "1px solid var(--border)", background: "#f8fafc" }}
              >
                <ChevronLeft style={{ width: 14, height: 14 }} />Back
              </Button>
              <Button
                disabled={step === "grading" || (answerMode === "upload" ? !answerFile : !answerText.trim())}
                onClick={handleSubmit}
                className="gap-2"
                style={{ background: "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)", boxShadow: "0 2px 16px rgba(124,58,237,0.3)" }}
              >
                {step === "grading" ? <><Spinner />Grading your answer...</> : <>Submit for Grading <ArrowRight style={{ width: 14, height: 14 }} /></>}
              </Button>
            </div>
            {step === "grading" && <p className="text-xs text-muted-foreground">AI is reading and grading your answer — this may take 15–30 s.</p>}
          </CardContent>
        </Card>
      )}

      {/* ══════ RESULT ═══════════════════════════════════════ */}
      {step === "result" && gradeResult && (
        <div className="space-y-5 page-section">
          {/* Score hero card */}
          <div
            className="rounded-2xl p-6 relative overflow-hidden"
            style={{
              background: "linear-gradient(135deg, #7c3aed 0%, #0ea5e9 100%)",
              border: "1px solid rgba(124,58,237,0.3)",
              boxShadow: "0 8px 32px -8px rgba(124,58,237,0.35)",
            }}
          >
            {/* Background glow */}
            <div className="absolute inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 60% 60% at 80% 50%, rgba(255,255,255,0.12) 0%, transparent 70%)" }} />

            <div className="flex flex-col sm:flex-row sm:items-center gap-6 relative z-10">
              {/* Grade badge */}
              <div className="shrink-0">
                <GradeBadge grade={gradeResult.grade} />
              </div>
              {/* Score numbers */}
              <div className="flex-1">
                <p className="text-muted-foreground text-xs font-semibold uppercase tracking-wider mb-2">Written Test Score</p>
                <div className="flex items-end gap-5">
                  <div>
                    <span className="text-5xl font-black tabular-nums text-gradient">{gradeResult.marks_obtained}</span>
                    <span className="text-2xl text-muted-foreground font-light ml-1">/{gradeResult.total_marks}</span>
                  </div>
                  {gradeResult.percentage !== undefined && (
                    <div className="pb-1">
                      <span className="text-2xl font-bold">{Math.round(gradeResult.percentage)}<span className="text-lg">%</span></span>
                      <p className="text-xs text-muted-foreground">percentage</p>
                    </div>
                  )}
                </div>
                <div className="mt-3">
                  <Progress
                    value={pct}
                    className="h-2 rounded-full"
                    style={{ background: "#e2e8f0" }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Feedback */}
          {gradeResult.feedback && (
            <Card className="content-card-elevated" >
              <CardContent className="pt-5 pb-5">
                <p className="section-label mb-2">AI Feedback</p>
                <p className="text-sm leading-relaxed">{gradeResult.feedback}</p>
              </CardContent>
            </Card>
          )}

          {/* Strengths + Improvements */}
          {(gradeResult.strengths?.length || gradeResult.improvements?.length) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {gradeResult.strengths?.length ? (
                <div className="feedback-positive animate-fade-in">
                  <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: "#10b981" }}>Strengths</p>
                  <ul className="space-y-2">
                    {gradeResult.strengths.map((s, i) => (
                      <li key={i} className="text-sm flex gap-2 items-start">
                        <CheckCircle style={{ width: 14, height: 14, color: "#10b981", flexShrink: 0, marginTop: 2 }} />
                        <span className="leading-snug">{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {gradeResult.improvements?.length ? (
                <div className="feedback-warning animate-fade-in">
                  <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: "#92400e" }}>Areas to Improve</p>
                  <ul className="space-y-2">
                    {gradeResult.improvements.map((s, i) => (
                      <li key={i} className="text-sm flex gap-2 items-start">
                        <AlertTriangle style={{ width: 14, height: 14, color: "#92400e", flexShrink: 0, marginTop: 2 }} />
                        <span className="leading-snug">{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          )}

          {/* Mark breakdown */}
          {gradeResult.breakdown?.length ? (
            <Card className="content-card-elevated" >
              <CardContent className="pt-5 pb-5">
                <p className="section-label mb-2">Mark Breakdown</p>
                <Breakdown items={gradeResult.breakdown} />
              </CardContent>
            </Card>
          ) : null}

          {/* Extracted text */}
          {extractedAnswer && (
            <details>
              <summary className="text-xs text-muted-foreground/70 cursor-pointer hover:text-muted-foreground select-none transition-colors">
                View extracted text from your answer
              </summary>
              <pre className="mt-2 text-xs font-mono rounded-xl p-4 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed" style={{ background: "#f1f5f9", border: "1px solid var(--border)" }}>
                {extractedAnswer}
              </pre>
            </details>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={reset}
              className="gap-1.5"
              style={{ border: "1px solid var(--border)", background: "#f8fafc" }}
            >
              <RotateCcw style={{ width: 13, height: 13 }} />Start Over
            </Button>
            <Button
              onClick={handleStartViva}
              disabled={generatingViva}
              className="gap-2"
              style={{ background: "linear-gradient(135deg, #7c3aed 0%, #0ea5e9 100%)", boxShadow: "0 2px 16px rgba(124,58,237,0.35)" }}
            >
              {generatingViva ? <><Spinner />Generating Questions...</> : <><Mic style={{ width: 14, height: 14 }} />Start Viva <span className="text-primary-foreground/70 text-xs">(+10 marks)</span></>}
            </Button>
          </div>
        </div>
      )}

      {/* ══════ VIVA ═════════════════════════════════════════ */}
      {step === "viva" && vivaQuestions.length > 0 && (
        <div className="space-y-4 page-section">

          {/* Hidden canvas for frame capture */}
          <canvas ref={canvasRef} className="hidden" />

          {/* Proctor status bar */}
          <div
            className="flex items-center justify-between px-4 py-2.5 rounded-xl text-sm font-medium"
            style={{
              background: proctorAction === "terminated" ? "#fef2f2" : proctorAction === "warning" ? "#fef3c7" : proctorAction === "away" ? "#fff7ed" : "#f0fdf4",
              border: `1px solid ${proctorAction === "terminated" ? "rgba(239,68,68,0.3)" : proctorAction === "warning" ? "rgba(245,158,11,0.3)" : proctorAction === "away" ? "rgba(249,115,22,0.25)" : "rgba(16,185,129,0.3)"}`,
            }}
          >
            <div className="flex items-center gap-2">
              {cameraReady
                ? <Camera style={{ width: 15, height: 15, color: proctorAction === "ok" ? "#10b981" : "#f59e0b" }} />
                : <CameraOff style={{ width: 15, height: 15, color: "#94a3b8" }} />
              }
              <span style={{ color: proctorAction === "terminated" ? "#991b1b" : proctorAction === "warning" ? "#92400e" : proctorAction === "away" ? "#7c2d12" : "#065f46" }}>
                {proctorMessage || (cameraReady ? "Proctoring active — keep your eyes on screen" : "Starting camera…")}
              </span>
            </div>
            {proctorWarnings > 0 && (
              <span className="font-bold" style={{ color: "#dc2626" }}>
                ⚠ {proctorWarnings}/3 warnings
              </span>
            )}
          </div>

          {/* Camera error fallback */}
          {cameraError && (
            <Alert style={{ borderColor: "rgba(245,158,11,0.3)", background: "#fef3c7" }}>
              <AlertTriangle style={{ width: 15, height: 15, color: "#92400e" }} />
              <AlertDescription style={{ color: "#78350f" }}>{cameraError}</AlertDescription>
            </Alert>
          )}

          {/* Main viva card — camera left, question right */}
          <Card className="content-card-elevated">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <span className="h-6 w-6 rounded-md flex items-center justify-center" style={{ background: "#ede9fe", color: "var(--primary)" }}>
                    <Mic style={{ width: 13, height: 13 }} />
                  </span>
                  Viva Examination
                </CardTitle>
                <span
                  className="text-xs font-semibold px-2.5 py-1 rounded-full"
                  style={{ background: "#ede9fe", color: "var(--primary)", border: "1px solid rgba(124,58,237,0.2)" }}
                >
                  Q {currentQ + 1} / {vivaQuestions.length}
                </span>
              </div>
              {/* Progress bar */}
              <div className="mt-3 rounded-full overflow-hidden h-1.5" style={{ background: "#e2e8f0" }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${((currentQ + 1) / vivaQuestions.length) * 100}%`, background: "linear-gradient(90deg, #7c3aed, #0ea5e9)" }}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Two-column layout: camera | question+answer */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

                {/* Camera feed */}
                <div className="flex flex-col gap-2">
                  <p className="section-label">Proctoring Camera</p>
                  <div
                    className="relative rounded-xl overflow-hidden flex items-center justify-center"
                    style={{ background: "#0f172a", aspectRatio: "4/3", border: "2px solid", borderColor: proctorAction === "warning" || proctorAction === "terminated" ? "#f59e0b" : proctorAction === "away" ? "#fb923c" : "#7c3aed" }}
                  >
                    <video
                      ref={videoRef}
                      autoPlay
                      muted
                      playsInline
                      className="w-full h-full object-cover"
                      style={{ display: cameraReady ? "block" : "none" }}
                    />
                    {!cameraReady && (
                      <div className="flex flex-col items-center gap-2 text-slate-400">
                        <CameraOff style={{ width: 28, height: 28 }} />
                        <span className="text-xs">{cameraError ? "Camera denied" : "Starting…"}</span>
                      </div>
                    )}
                    {/* Live indicator */}
                    {cameraReady && (
                      <div className="absolute top-2 left-2 flex items-center gap-1.5 px-2 py-0.5 rounded-full" style={{ background: "rgba(0,0,0,0.55)" }}>
                        <span className="h-1.5 w-1.5 rounded-full bg-red-500" style={{ animation: "pulse 1.5s infinite" }} />
                        <span className="text-white text-xs font-medium">LIVE</span>
                      </div>
                    )}
                    {/* Warning overlay */}
                    {(proctorAction === "away" || proctorAction === "warning") && (
                      <div className="absolute inset-0 border-4 rounded-xl pointer-events-none" style={{ borderColor: "#f59e0b", animation: "pulse 1s infinite" }} />
                    )}
                  </div>
                  {/* Warning dots */}
                  <div className="flex gap-1.5 justify-center mt-1">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="h-2 w-2 rounded-full transition-all"
                        style={{ background: i < proctorWarnings ? "#ef4444" : "#e2e8f0", boxShadow: i < proctorWarnings ? "0 0 6px rgba(239,68,68,0.6)" : "none" }} />
                    ))}
                  </div>
                  <p className="text-xs text-center text-muted-foreground">
                    {3 - proctorWarnings} warning{3 - proctorWarnings !== 1 ? "s" : ""} remaining
                  </p>
                </div>

                {/* Question + Answer */}
                <div className="lg:col-span-2 space-y-3">
                  {/* Question card */}
                  <div className="rounded-xl p-5" style={{ background: "#f8fafc", border: "1px solid var(--border)" }}>
                    {vivaQuestions[currentQ].topic && (
                      <Badge className="mb-3 text-xs" style={{ background: "#e0f2fe", color: "#0ea5e9", border: "1px solid rgba(14,165,233,0.25)" }}>
                        {vivaQuestions[currentQ].topic}
                      </Badge>
                    )}
                    <p className="font-medium leading-relaxed">{vivaQuestions[currentQ].question}</p>
                  </div>

                  {/* Answer textarea */}
                  <Textarea
                    rows={6}
                    placeholder="Type your answer here..."
                    value={vivaAnswers[currentQ] ?? ""}
                    onChange={(e) => setVivaAnswers(prev => { const next = [...prev]; next[currentQ] = e.target.value; return next; })}
                    style={{ background: "#f8fafc", border: "1px solid var(--border)", resize: "vertical" }}
                  />

                  {/* Navigation */}
                  <div className="flex items-center justify-between pt-1">
                    <div className="flex gap-2">
                      {currentQ > 0 && (
                        <Button
                          variant="outline" size="sm"
                          onClick={() => setCurrentQ(q => q - 1)}
                          className="gap-1"
                          style={{ border: "1px solid var(--border)", background: "#f8fafc" }}
                        >
                          <ChevronLeft style={{ width: 14, height: 14 }} />Prev
                        </Button>
                      )}
                      {currentQ < vivaQuestions.length - 1 ? (
                        <Button size="sm" onClick={() => setCurrentQ(q => q + 1)} className="gap-1"
                          style={{ background: "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)" }}>
                          Next <ChevronRight style={{ width: 14, height: 14 }} />
                        </Button>
                      ) : (
                        <Button onClick={handleSubmitViva} disabled={gradingViva} className="gap-2"
                          style={{ background: "linear-gradient(135deg, #7c3aed 0%, #0ea5e9 100%)", boxShadow: "0 2px 16px rgba(124,58,237,0.3)" }}>
                          {gradingViva ? <><Spinner />Grading Viva...</> : <>Submit Viva <CheckCircle style={{ width: 14, height: 14 }} /></>}
                        </Button>
                      )}
                    </div>
                    {/* Dot indicator */}
                    <div className="flex gap-1.5">
                      {vivaQuestions.map((_, i) => (
                        <button key={i} onClick={() => setCurrentQ(i)} className="h-2 w-2 rounded-full transition-all"
                          style={{ background: i === currentQ ? "var(--primary)" : vivaAnswers[i] ? "rgba(124,58,237,0.4)" : "#e2e8f0", transform: i === currentQ ? "scale(1.4)" : "scale(1)" }} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ══════ FINAL SCORECARD ══════════════════════════════ */}
      {step === "final" && gradeResult && vivaResult && (
        <div className="space-y-5 page-section">
          {/* Hero banner */}
          <div
            className="rounded-2xl p-6 relative overflow-hidden"
            style={{
              background: "linear-gradient(135deg, #7c3aed 0%, #0ea5e9 100%)",
              border: "1px solid rgba(124,58,237,0.3)",
              boxShadow: "0 8px 40px -8px rgba(124,58,237,0.35)",
            }}
          >
            <div className="absolute inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 70% 80% at 90% 50%, rgba(255,255,255,0.12) 0%, transparent 60%)" }} />
            <div className="flex items-center gap-3 mb-5 relative z-10">
              <div className="h-10 w-10 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #7c3aed 0%, #0ea5e9 100%)", boxShadow: "0 4px 16px rgba(124,58,237,0.4)" }}>
                <Award style={{ width: 18, height: 18, color: "#fff" }} />
              </div>
              <div>
                <p className="font-bold text-lg text-gradient">Final Scorecard</p>
                <p className="text-xs text-muted-foreground">Combined written + viva assessment</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 relative z-10">
              {[
                { label: "Written Test", val: `${gradeResult.marks_obtained}`, total: `${gradeResult.total_marks}`, extra: <GradeBadge grade={gradeResult.grade} /> },
                { label: "Viva", val: `${vivaResult.marks_obtained}`, total: `${vivaResult.total_marks}`, extra: null },
                {
                  label: "Total Score",
                  val: `${gradeResult.marks_obtained + vivaResult.marks_obtained}`,
                  total: `${gradeResult.total_marks + vivaResult.total_marks}`,
                  extra: null,
                  highlight: true,
                },
              ].map(({ label, val, total, extra, highlight }) => (
                <div
                  key={label}
                  className="rounded-xl p-4 flex flex-col items-center gap-2 text-center"
                  style={
                    highlight
                      ? { background: "rgba(124,58,237,0.1)", border: "1px solid rgba(124,58,237,0.35)", boxShadow: "0 0 20px -4px rgba(124,58,237,0.25)" }
                      : { background: "#f1f5f9", border: "1px solid var(--border)" }
                  }
                >
                  <p className="section-label">{label}</p>
                  <p className={cn("font-black tabular-nums", highlight ? "text-3xl text-gradient" : "text-2xl")}>
                    {val}<span className="opacity-50 font-light text-base">/{total}</span>
                  </p>
                  {extra}
                </div>
              ))}
            </div>
          </div>

          {/* Terminated warning */}
          {vivaTerminated && (
            <Alert variant="destructive">
              <AlertTriangle style={{ width: 15, height: 15 }} />
              <AlertDescription>Viva was terminated by the AI proctor — you looked away from the screen 3 times. Viva score: 0/{vivaResult.total_marks}.</AlertDescription>
            </Alert>
          )}

          {/* Viva feedback */}
          {vivaResult.overall_feedback && !vivaTerminated && (
            <Card className="content-card-elevated" >
              <CardContent className="pt-5 pb-5">
                <p className="section-label mb-2">Viva Feedback</p>
                <p className="text-sm leading-relaxed">{vivaResult.overall_feedback}</p>
              </CardContent>
            </Card>
          )}

          {/* Viva breakdown */}
          {vivaResult.breakdown?.length && !vivaTerminated ? (
            <Card className="content-card-elevated" >
              <CardContent className="pt-5 pb-5">
                <p className="section-label mb-2">Viva Breakdown</p>
                <Breakdown items={vivaResult.breakdown} />
              </CardContent>
            </Card>
          ) : null}

          <Button
            onClick={reset}
            className="gap-2"
            style={{ background: "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)", boxShadow: "0 2px 16px rgba(124,58,237,0.3)" }}
          >
            <RotateCcw style={{ width: 14, height: 14 }} />Start New Submission
          </Button>
        </div>
      )}
    </div>
  );
};

export default StudentGrader;


