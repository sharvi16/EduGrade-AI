import axios from "axios";
import type {
  Exam,
  GradeResult,
  OcrResult,
  VivaQA,
  VivaQuestion,
  VivaResult,
  Submission,
} from "../types";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 120000, // Vision calls can be slow
});

// ── Exam CRUD ──────────────────────────────────────────────────────
export const listExams = (): Promise<Exam[]> =>
  api.get("/exams").then((r) => r.data);

export const getExam = (examId: string): Promise<Exam> =>
  api.get(`/exams/${examId}`).then((r) => r.data);

export const deleteExam = (examId: string): Promise<void> =>
  api.delete(`/exams/${examId}`).then(() => undefined);

export const createExam = (formData: FormData): Promise<Exam> =>
  api
    .post("/exams", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);

// ── Grading ────────────────────────────────────────────────────────
export const gradeText = (
  examId: string,
  studentName: string,
  student_answer: string
): Promise<GradeResult> =>
  api
    .post("/grade/text", { exam_id: examId, student_name: studentName, student_answer })
    .then((r) => r.data);

export const gradeImage = (formData: FormData): Promise<GradeResult> =>
  api
    .post("/grade/image", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);

// ── Viva ──────────────────────────────────────────────────────────
export const generateVivaQuestions = (
  examId: string,
  student_answer: string,
  num_questions = 6
): Promise<{ questions: VivaQuestion[] }> =>
  api
    .post("/viva/generate", { exam_id: examId, student_answer, num_questions })
    .then((r) => r.data);

export const gradeViva = async (examId: string, studentName: string, studentAnswer: string, qaPairs: VivaQA[]): Promise<VivaResult> => {
  const req: any = { exam_id: examId, student_name: studentName, student_answer: studentAnswer, qa_pairs: qaPairs };
  const res = await api.post("/viva/grade", req);
  return res.data;
};

export const gradeVivaFail = async (examId: string, studentName: string, reason: string): Promise<VivaResult> => {
  const res = await api.post("/viva/fail", { exam_id: examId, student_name: studentName, reason: reason });
  return res.data;
};

// ── Proctoring ────────────────────────────────────────────────────
export const proctorStart = async (examId: string, studentId: string): Promise<any> => {
  const res = await api.post("/proctor/start", { exam_id: examId, student_id: studentId });
  return res.data;
};

export const proctorCheckFrame = (
  session_id: string,
  frame: string          // base64-encoded image from canvas
): Promise<{
  action: "ok" | "away" | "warning" | "terminated";
  warnings: number;
  terminated: boolean;
  message: string;
  frames_away: number;
  detection_reason: string;
}> =>
  api.post("/proctor/check-frame", { session_id, frame }).then((r) => r.data);

export const proctorDeleteSession = (session_id: string): Promise<void> =>
  api.delete(`/proctor/session/${session_id}`).then(() => undefined);

// ── OCR ──────────────────────────────────────────────────────────
export const extractText = (formData: FormData): Promise<OcrResult> =>
  api
    .post("/ocr/extract", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);

// ── Submissions ──────────────────────────────────────────────────
export const getExamSubmissions = (examId: string): Promise<Submission[]> =>
  api.get(`/exams/${examId}/submissions`).then((r) => r.data);

export const getStudentSubmission = (examId: string, studentName: string): Promise<Submission> =>
  api.get(`/exams/${examId}/submissions/${encodeURIComponent(studentName)}`).then((r) => r.data);
