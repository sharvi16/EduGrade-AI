// ── Exam ──────────────────────────────────────────────────────────
export interface Exam {
  exam_id: string;
  title: string;
  subject: string;
  total_marks: number;
  created_at: string;
  questions?: string;
  answer_key?: string;
  rubrics?: string;
}

// ── Grading ────────────────────────────────────────────────────────
export interface MarkBreakdown {
  question?: string;
  criterion?: string;
  marks_awarded: number;
  max_marks: number;
  comment: string;
}

export interface GradeResult {
  marks_obtained: number;
  total_marks: number;
  percentage?: number;
  grade?: string;
  strengths?: string[];
  improvements?: string[];
  feedback?: string;
  breakdown?: MarkBreakdown[];
  // extended for image path
  extracted_answer?: string;
}

// ── Viva ──────────────────────────────────────────────────────────
export interface VivaQuestion {
  question: string;
  topic: string;
}

export interface VivaQA extends VivaQuestion {
  student_answer: string;
}

export interface VivaBreakdown {
  question?: string;
  marks_awarded: number;
  max_marks: number;
  comment: string;
}

export interface VivaResult {
  marks_obtained: number;
  total_marks: number;
  breakdown?: VivaBreakdown[];
  overall_feedback?: string;
}

// ── OCR ──────────────────────────────────────────────────────────
export interface OcrResult {
  raw_text: string;
  final_text: string;
}

// ── Submissions ──────────────────────────────────────────────────
export interface Submission {
  submission_id: string;
  exam_id: string;
  student_name: string;
  submitted_at: string;
  written: GradeResult | null;
  viva: VivaResult | null;
}
