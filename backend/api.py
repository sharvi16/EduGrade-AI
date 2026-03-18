"""
FastAPI REST server — bridges the React frontend to the Python AI backend.
Run:  uvicorn api:app --reload --port 8000
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

from utils import (
    GROQ_API_KEY,
    GROQ_VISION_MODEL,
    GROQ_TEXT_MODEL,
    extract_text_from_images,
    file_to_image_bytes_list,
    image_to_base64,
)
from viva_proctor import check_frame_base64, session_store
from viva_proctor.proctor import create_session, get_session, delete_session

EXAMS_DIR = os.path.join(os.path.dirname(__file__), "exams")
os.makedirs(EXAMS_DIR, exist_ok=True)

SUBMISSIONS_DIR = os.path.join(os.path.dirname(__file__), "data", "submissions")
os.makedirs(SUBMISSIONS_DIR, exist_ok=True)


def save_submission(exam_id: str, student_name: str, written_result: dict = None, viva_result: dict = None):
    # Unique ID per exam + student
    sub_id = f"{exam_id}_{student_name.replace(' ', '_').lower()}"
    path = os.path.join(SUBMISSIONS_DIR, f"{sub_id}.json")
    
    data = {
        "submission_id": sub_id,
        "exam_id": exam_id,
        "student_name": student_name,
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
        "written": written_result,
        "viva": viva_result,
    }
    
    # Merge if exists
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                old = json.load(f)
            data["submitted_at"] = old.get("submitted_at", data["submitted_at"])
            if written_result is None:
                data["written"] = old.get("written")
            if viva_result is None:
                data["viva"] = old.get("viva")
        except:
            pass
            
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return sub_id


# ══════════════════════════════════════════════════════════════════
# PURE AI FUNCTIONS (no Streamlit dependency)
# ══════════════════════════════════════════════════════════════════

def load_all_exams() -> list[dict]:
    exams = []
    for fname in os.listdir(EXAMS_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(EXAMS_DIR, fname), encoding="utf-8") as f:
                    exams.append(json.load(f))
            except Exception:
                pass
    exams.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return exams


def grade_answer(exam: dict, student_answer: str) -> dict:
    client = Groq(api_key=GROQ_API_KEY)
    questions_section  = exam.get("questions",   "Not provided")
    answer_key_section = exam.get("answer_key",  "Not provided")
    rubric_section     = exam.get("rubrics",     "Not provided")
    total_marks        = exam.get("total_marks", 100)

    system_prompt = f"""You are an experienced and fair examiner grading a student's answer.
Total marks available: {total_marks}

Respond ONLY with a valid JSON object:
{{
  "marks_obtained": <number>,
  "total_marks": {total_marks},
  "percentage": <number>,
  "grade": "<O/A/B/C/D/F>",
  "breakdown": [
    {{"criterion": "<section/question>", "marks_awarded": <n>, "max_marks": <n>, "comment": "<text>"}}
  ],
  "strengths": ["<strength>"],
  "improvements": ["<area to improve>"],
  "feedback": "<2-3 sentence overall feedback>"
}}"""

    user_prompt = f"""## QUESTION PAPER\n{questions_section}

## MODEL ANSWER\n{answer_key_section}

## GRADING RUBRIC\n{rubric_section}

## STUDENT'S ANSWER\n{student_answer}

Grade the answer and return JSON only."""

    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content.strip())


def grade_from_images(exam: dict, image_bytes_list: list) -> tuple[str, dict]:
    """Single Vision call: extract handwriting AND grade together."""
    client = Groq(api_key=GROQ_API_KEY)
    questions_section  = exam.get("questions",   "Not provided")
    answer_key_section = exam.get("answer_key",  "Not provided")
    rubric_section     = exam.get("rubrics",     "Not provided")
    total_marks        = exam.get("total_marks", 100)

    content: list = []
    for img_bytes in image_bytes_list[:4]:
        b64 = image_to_base64(img_bytes)
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

    content.append({"type": "text", "text": f"""You are an expert examiner.
The images are a student's handwritten answer sheet.
STEP 1: Transcribe all handwritten text.
STEP 2: Grade against the rubric.

## QUESTION PAPER\n{questions_section}
## MODEL ANSWER\n{answer_key_section}
## GRADING RUBRIC\n{rubric_section}
## TOTAL MARKS: {total_marks}

Return ONLY valid JSON:
{{
  "extracted_answer": "<full transcribed answer>",
  "marks_obtained": <number>,
  "total_marks": {total_marks},
  "percentage": <number>,
  "grade": "<O/A/B/C/D/F>",
  "breakdown": [{{"criterion": "<name>", "marks_awarded": <n>, "max_marks": <n>, "comment": "<text>"}}],
  "strengths": ["<strength>"],
  "improvements": ["<improvement>"],
  "feedback": "<2-3 sentence feedback>"
}}"""})

    response = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=0.2,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content.strip())
    extracted = data.pop("extracted_answer", "")
    return extracted, data


def generate_viva_questions(exam: dict, student_answer: str, num_questions: int = 6) -> list[dict]:
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {"role": "system", "content": """You are an examiner conducting an oral viva.
Generate targeted viva questions that test understanding.
Return ONLY a valid JSON object: {"questions": [{"question": "...", "topic": "..."}]}"""},
            {"role": "user", "content": f"""Subject: {exam.get('subject', 'General')}
Student's answer: {student_answer}
Generate exactly {num_questions} viva questions. Return JSON only."""},
        ],
        temperature=0.5,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )
    raw = json.loads(response.choices[0].message.content.strip())
    if isinstance(raw, list):
        return raw
    for val in raw.values():
        if isinstance(val, list):
            return val
    return []


def grade_viva(exam: dict, student_answer: str, qa_pairs: list[dict]) -> dict:
    client = Groq(api_key=GROQ_API_KEY)
    qa_text = "".join(
        f"Q{i} [{qa.get('topic','')}]: {qa['question']}\n"
        f"Student: {qa.get('student_answer', '(none)')}\n\n"
        for i, qa in enumerate(qa_pairs, 1)
    )
    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {"role": "system", "content": """You are grading an oral viva out of 10 marks.
Return ONLY valid JSON:
{
  "marks_obtained": <number>,
  "total_marks": 10,
  "breakdown": [{"question_no": 1, "question": "...", "marks_awarded": <n>, "max_marks": <n>, "comment": "..."}],
  "overall_feedback": "<2-3 sentence summary>"
}"""},
            {"role": "user", "content": f"""Subject: {exam.get('subject', 'General')}
Written answer (context): {student_answer[:600]}

VIVA Q&A:
{qa_text}
Grade out of 10. Return JSON only."""},
        ],
        temperature=0.2,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content.strip())


def polish_text(raw_text: str) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {"role": "system", "content": (
                "You are proofreading a transcript of a student's handwritten assignment. "
                "Fix transcription errors only. Do NOT change content or structure. "
                "Return only the corrected text."
            )},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.15,
        max_tokens=4096,
    )
    return response.choices[0].message.content.strip()

# ── App ────────────────────────────────────────────────────────────
app = FastAPI(title="EduGrade AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════
# EXAM CRUD
# ══════════════════════════════════════════════════════════════════

@app.get("/exams")
def list_exams():
    return load_all_exams()


@app.get("/exams/{exam_id}")
def get_exam(exam_id: str):
    path = os.path.join(EXAMS_DIR, f"{exam_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Exam not found")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.delete("/exams/{exam_id}")
def delete_exam(exam_id: str):
    path = os.path.join(EXAMS_DIR, f"{exam_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Exam not found")
    os.remove(path)
    # Also delete submissions
    for fname in os.listdir(SUBMISSIONS_DIR):
        if fname.startswith(f"{exam_id}_"):
            try:
                os.remove(os.path.join(SUBMISSIONS_DIR, fname))
            except:
                pass
    return {"ok": True}


@app.get("/exams/{exam_id}/submissions")
def get_submissions(exam_id: str):
    submissions = []
    for fname in os.listdir(SUBMISSIONS_DIR):
        if fname.startswith(f"{exam_id}_") and fname.endswith(".json"):
            try:
                with open(os.path.join(SUBMISSIONS_DIR, fname), encoding="utf-8") as f:
                    submissions.append(json.load(f))
            except:
                pass
    # Sort newest first
    submissions.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
    return submissions


@app.get("/exams/{exam_id}/submissions/{student_name}")
def get_student_submission(exam_id: str, student_name: str):
    sub_id = f"{exam_id}_{student_name.replace(' ', '_').lower()}"
    path = os.path.join(SUBMISSIONS_DIR, f"{sub_id}.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    raise HTTPException(404, "Submission not found")


# ══════════════════════════════════════════════════════════════════
# TEACHER — Create Exam
# ══════════════════════════════════════════════════════════════════

QUESTION_PROMPT = (
    "This is a question paper for a student assignment or exam. "
    "Transcribe ALL questions exactly as written, preserving numbering, "
    "sub-questions, and formatting. Output only the transcribed text."
)
ANSWER_PROMPT = (
    "This is an answer key / model answer for an exam. "
    "Transcribe ALL the answers exactly as written, preserving question numbers, "
    "structure, and key points. Output only the transcribed text."
)
RUBRIC_PROMPT = (
    "This is a grading rubric / marking scheme for an exam. "
    "Transcribe ALL criteria, marks allocation, and grade descriptors exactly. "
    "Preserve all structure, numbering, and mark breakdowns. "
    "Output only the transcribed text."
)


async def _extract_upload(upload: UploadFile, prompt: str) -> str:
    raw = await upload.read()

    class _FakeFile:
        def __init__(self, name, data):
            self.name = name
            self._data = data
            self._pos = 0
        def read(self):
            return self._data
        def seek(self, n):
            self._pos = n

    fake = _FakeFile(upload.filename, raw)
    pages = file_to_image_bytes_list(fake)
    return extract_text_from_images(pages, prompt)


@app.post("/exams")
async def create_exam(
    title:        str        = Form(...),
    subject:      str        = Form(""),
    total_marks:  int        = Form(20),
    rubric_text:  str        = Form(""),
    questions_file:  Optional[UploadFile] = File(None),
    answer_key_file: Optional[UploadFile] = File(None),
    rubric_file:     Optional[UploadFile] = File(None),
):
    extracted: dict = {}

    if questions_file and questions_file.filename:
        extracted["questions"] = await _extract_upload(questions_file, QUESTION_PROMPT)
    if answer_key_file and answer_key_file.filename:
        extracted["answer_key"] = await _extract_upload(answer_key_file, ANSWER_PROMPT)
    if rubric_file and rubric_file.filename:
        extracted["rubrics"] = await _extract_upload(rubric_file, RUBRIC_PROMPT)
    elif rubric_text.strip():
        extracted["rubrics"] = rubric_text.strip()

    exam_data = {
        "exam_id":     str(uuid.uuid4())[:8],
        "title":       title.strip(),
        "subject":     subject.strip(),
        "total_marks": total_marks,
        "created_at":  datetime.now().isoformat(timespec="seconds"),
        **extracted,
    }

    path = os.path.join(EXAMS_DIR, f"{exam_data['exam_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(exam_data, f, indent=2, ensure_ascii=False)

    return exam_data


# ══════════════════════════════════════════════════════════════════
# GRADER
# ══════════════════════════════════════════════════════════════════

class GradeTextRequest(BaseModel):
    exam_id: str
    student_name: str
    student_answer: str


@app.post("/grade/text")
def grade_text(req: GradeTextRequest):
    sub_id = f"{req.exam_id}_{req.student_name.replace(' ', '_').lower()}"
    if os.path.exists(os.path.join(SUBMISSIONS_DIR, f"{sub_id}.json")):
        raise HTTPException(400, "You have already submitted an answer for this exam.")

    path = os.path.join(EXAMS_DIR, f"{req.exam_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Exam not found")
    with open(path, encoding="utf-8") as f:
        exam = json.load(f)
    result = grade_answer(exam, req.student_answer)
    save_submission(req.exam_id, req.student_name, written_result=result)
    return result


@app.post("/grade/image")
async def grade_image(
    exam_id: str = Form(...),
    student_name: str = Form(...),
    answer_file: UploadFile = File(...),
):
    sub_id = f"{exam_id}_{student_name.replace(' ', '_').lower()}"
    if os.path.exists(os.path.join(SUBMISSIONS_DIR, f"{sub_id}.json")):
        raise HTTPException(400, "You have already submitted an answer for this exam.")

    path = os.path.join(EXAMS_DIR, f"{exam_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Exam not found")
    with open(path, encoding="utf-8") as f:
        exam = json.load(f)

    raw = await answer_file.read()

    class _FakeFile:
        def __init__(self, name, data):
            self.name = name
            self._data = data
        def read(self):
            return self._data
        def seek(self, n):
            pass

    fake = _FakeFile(answer_file.filename, raw)
    pages = file_to_image_bytes_list(fake)
    extracted_answer, result = grade_from_images(exam, pages)
    save_submission(exam_id, student_name, written_result={"extracted_answer": extracted_answer, **result})
    return {"extracted_answer": extracted_answer, **result}


# ══════════════════════════════════════════════════════════════════
# VIVA
# ══════════════════════════════════════════════════════════════════

class VivaGenRequest(BaseModel):
    exam_id: str
    student_answer: str
    num_questions: int = 6


@app.post("/viva/generate")
def viva_generate(req: VivaGenRequest):
    path = os.path.join(EXAMS_DIR, f"{req.exam_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Exam not found")
    with open(path, encoding="utf-8") as f:
        exam = json.load(f)
    questions = generate_viva_questions(exam, req.student_answer, req.num_questions)
    return {"questions": questions}


class VivaQA(BaseModel):
    question: str
    topic: str = ""
    student_answer: str


class VivaGradeRequest(BaseModel):
    exam_id: str
    student_name: str
    student_answer: str
    qa_pairs: list[VivaQA]


@app.post("/viva/grade")
def viva_grade(req: VivaGradeRequest):
    path = os.path.join(EXAMS_DIR, f"{req.exam_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Exam not found")
    with open(path, encoding="utf-8") as f:
        exam = json.load(f)
    result = grade_viva(exam, req.student_answer, [q.model_dump() for q in req.qa_pairs])
    save_submission(req.exam_id, req.student_name, viva_result=result)
    return result


class VivaFailRequest(BaseModel):
    exam_id: str
    student_name: str
    reason: str

@app.post("/viva/fail")
def viva_fail(req: VivaFailRequest):
    """Permanently record a 0 score for a student who was terminated by the proctor."""
    path = os.path.join(EXAMS_DIR, f"{req.exam_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Exam not found")
        
    result = {
        "marks_obtained": 0,
        "total_marks": 10,
        "percentage": 0,
        "grade": "F",
        "breakdown": [],
        "overall_feedback": req.reason
    }
    save_submission(req.exam_id, req.student_name, viva_result=result)
    return result


# ══════════════════════════════════════════════════════════════════
# ASSIGNMENT OCR
# ══════════════════════════════════════════════════════════════════

@app.post("/ocr/extract")
async def ocr_extract(
    file: UploadFile = File(...),
    polish: bool = Form(True),
):
    raw = await file.read()

    class _FakeFile:
        def __init__(self, name, data):
            self.name = name
            self._data = data
        def read(self):
            return self._data
        def seek(self, n):
            pass

    fake = _FakeFile(file.filename, raw)
    pages = file_to_image_bytes_list(fake)

    ASSIGNMENT_PROMPT = (
        "This is a photo of a student's handwritten assignment. "
        "Please transcribe ALL the handwritten text exactly as written, "
        "preserving the structure, headings, numbered points, and paragraphs. "
        "Do not summarise, interpret, add, or remove anything. "
        "Output only the transcribed text."
    )
    raw_text = extract_text_from_images(pages, ASSIGNMENT_PROMPT, GROQ_API_KEY)

    final_text = raw_text
    if polish and raw_text.strip():
        final_text = polish_text(raw_text)

    return {"raw_text": raw_text, "final_text": final_text}


# ══════════════════════════════════════════════════════════════════
# VIVA PROCTORING  (CV-based, integrated from cv_proctor/)
# ══════════════════════════════════════════════════════════════════

class ProctorStartRequest(BaseModel):
    exam_id:    str
    student_id: str

@app.post("/proctor/start")
async def proctor_start(req: ProctorStartRequest):
    """Create a new proctoring session for a viva. Returns session_id."""
    sess = create_session(req.exam_id, req.student_id)
    return {"session_id": sess.session_id, "max_warnings": 3}


class ProctorFrameRequest(BaseModel):
    session_id: str
    frame:      str   # base64-encoded JPEG/PNG captured by the browser

@app.post("/proctor/check-frame")
async def proctor_check_frame(req: ProctorFrameRequest):
    """
    Receive one webcam frame, run OpenCV face+eye detection (same Haar-cascade
    logic as cv_proctor/cv_proctor.py), update session state, and return status.

    Response action values:
      ok         – student is looking at the screen
      away       – briefly looking away (no violation yet)
      warning    – violation recorded, N/3 warnings issued
      terminated – 3 violations reached, viva score = 0
    """
    sess = get_session(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Proctor session not found.")

    is_looking, reason = check_frame_base64(req.frame)
    result = sess.process_frame(is_looking, reason)
    result["detection_reason"] = reason
    return result


@app.get("/proctor/status/{session_id}")
async def proctor_status(session_id: str):
    """Get the current warnings / termination status for a session."""
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Proctor session not found.")
    return {
        "session_id": sess.session_id,
        "warnings":   sess.warnings,
        "terminated": sess.terminated,
        "max_warnings": 3,
    }


@app.delete("/proctor/session/{session_id}")
async def proctor_delete(session_id: str):
    """Clean up a session after the viva ends."""
    delete_session(session_id)
    return {"status": "deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
