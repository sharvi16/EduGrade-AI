"""
FastAPI REST server — bridges the React frontend to the Python AI backend.
Run:  uvicorn api:app --reload --port 8000
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, engine, Base
import models
from auth import verify_password, create_access_token, decode_access_token
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="EduGrade AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For production ease; restrict this later to your specific Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

security = HTTPBearer()

def get_current_user(auth: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    payload = decode_access_token(auth.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def check_role(user: models.User, roles: list[models.UserRole]):
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="Permission denied")

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

class LoginRequest(BaseModel):
    email: str
    password: str

# ══════════════════════════════════════════════════════════════════
# MANAGEMENT ENDPOINTS
# ══════════════════════════════════════════════════════════════════

class SchoolCreate(BaseModel):
    name: str

@app.post("/admin/schools")
def create_school(req: SchoolCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_role(current_user, [models.UserRole.SUPER_ADMIN])
    school = models.School(name=req.name)
    db.add(school)
    db.commit()
    db.refresh(school)
    return school

@app.get("/admin/schools")
def list_schools(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_role(current_user, [models.UserRole.SUPER_ADMIN])
    return db.query(models.School).all()

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: models.UserRole
    school_id: Optional[int] = None

@app.post("/admin/users")
def create_user(req: UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Super Admin can add anyone
    # Principal can add Teachers/Students in their school
    if current_user.role == models.UserRole.SUPER_ADMIN:
        pass
    elif current_user.role == models.UserRole.PRINCIPAL:
        if req.role not in [models.UserRole.TEACHER, models.UserRole.STUDENT]:
            raise HTTPException(403, "Principals can only add Teachers or Students")
        req.school_id = current_user.school_id
    elif current_user.role == models.UserRole.TEACHER:
        if req.role != models.UserRole.STUDENT:
            raise HTTPException(403, "Teachers can only add Students")
        req.school_id = current_user.school_id
    else:
        raise HTTPException(403, "Permission denied")

    from auth import get_password_hash
    user = models.User(
        email=req.email,
        password_hash=get_password_hash(req.password),
        name=req.name,
        role=req.role,
        school_id=req.school_id,
        teacher_id=current_user.id if current_user.role == models.UserRole.TEACHER else None
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role.value}

@app.get("/admin/users")
def list_users(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == models.UserRole.SUPER_ADMIN:
        return db.query(models.User).all()
    
    if current_user.role == models.UserRole.PRINCIPAL:
        return db.query(models.User).filter(models.User.school_id == current_user.school_id).all()
    
    if current_user.role == models.UserRole.TEACHER:
        # Teachers only see students they registered
        return db.query(models.User).filter(models.User.teacher_id == current_user.id).all()
    
    raise HTTPException(403, "Permission denied")

@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    print(f"DEBUG: Login attempt for {req.email}")
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "name": user.name,
            "email": user.email,
            "role": user.role.value
        }
    }


def save_submission(db: Session, exam_id: str, student_name: str, written: dict = None, viva: dict = None):
    # Unique ID per exam + student
    sub_id = f"{exam_id}_{student_name.replace(' ', '_').lower()}"
    submission = db.query(models.Submission).filter(models.Submission.submission_id == sub_id).first()
    
    if not submission:
        submission = models.Submission(
            submission_id=sub_id,
            exam_id=exam_id,
            student_name=student_name,
            written=written,
            viva=viva
        )
        db.add(submission)
    else:
        if written is not None:
            submission.written = written
        if viva is not None:
            submission.viva = viva
    
    db.commit()
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

# ══════════════════════════════════════════════════════════════════
# EXAM CRUD
# ══════════════════════════════════════════════════════════════════

@app.get("/exams")
def list_exams(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == models.UserRole.SUPER_ADMIN:
        return db.query(models.Exam).all()
    
    if current_user.role == models.UserRole.TEACHER:
        return db.query(models.Exam).filter(models.Exam.teacher_id == current_user.id).all()
    
    if current_user.role == models.UserRole.STUDENT:
        # Students only see exams from their assigned teacher
        return db.query(models.Exam).filter(models.Exam.teacher_id == current_user.teacher_id).all()
    
    # Principals see everything in the school
    return db.query(models.Exam).filter(models.Exam.school_id == current_user.school_id).all()


@app.get("/exams/{exam_id}")
def get_exam(exam_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    if current_user.role != models.UserRole.SUPER_ADMIN and exam.school_id != current_user.school_id:
        raise HTTPException(403, "Access denied")
    return exam


@app.delete("/exams/{exam_id}")
def delete_exam(exam_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_role(current_user, [models.UserRole.SUPER_ADMIN, models.UserRole.PRINCIPAL, models.UserRole.TEACHER])
    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    if current_user.role != models.UserRole.SUPER_ADMIN and exam.school_id != current_user.school_id:
        raise HTTPException(403, "Access denied")
    
    db.delete(exam)
    db.commit()
    return {"ok": True}


@app.get("/exams/{exam_id}/submissions")
def get_submissions(exam_id: str, db: Session = Depends(get_db)):
    subs = db.query(models.Submission).filter(models.Submission.exam_id == exam_id).all()
    import json
    for s in subs:
        if isinstance(s.written, str):
            s.written = json.loads(s.written)
        if isinstance(s.viva, str):
            s.viva = json.loads(s.viva)
    return subs


@app.get("/exams/{exam_id}/submissions/{student_name}")
def get_student_submission(exam_id: str, student_name: str, db: Session = Depends(get_db)):
    sub_id = f"{exam_id}_{student_name.replace(' ', '_').lower()}"
    submission = db.query(models.Submission).filter(models.Submission.submission_id == sub_id).first()
    if not submission:
        raise HTTPException(404, "Submission not found")
    
    # Ensure JSON fields are parsed if returned as strings (SQLite behavior)
    if isinstance(submission.written, str):
        import json
        submission.written = json.loads(submission.written)
    if isinstance(submission.viva, str):
        import json
        submission.viva = json.loads(submission.viva)
        
    return submission


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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    check_role(current_user, [models.UserRole.TEACHER, models.UserRole.PRINCIPAL])
    
    extracted: dict = {}
    if questions_file and questions_file.filename:
        extracted["questions"] = await _extract_upload(questions_file, QUESTION_PROMPT)
    if answer_key_file and answer_key_file.filename:
        extracted["answer_key"] = await _extract_upload(answer_key_file, ANSWER_PROMPT)
    if rubric_file and rubric_file.filename:
        extracted["rubrics"] = await _extract_upload(rubric_file, RUBRIC_PROMPT)
    elif rubric_text.strip():
        extracted["rubrics"] = rubric_text.strip()

    exam = models.Exam(
        exam_id=str(uuid.uuid4())[:8],
        title=title.strip(),
        subject=subject.strip(),
        total_marks=total_marks,
        questions=extracted.get("questions"),
        answer_key=extracted.get("answer_key"),
        rubrics=extracted.get("rubrics"),
        school_id=current_user.school_id,
        teacher_id=current_user.id
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


# ══════════════════════════════════════════════════════════════════
# GRADER
# ══════════════════════════════════════════════════════════════════

class GradeTextRequest(BaseModel):
    exam_id: str
    student_name: str
    student_answer: str


@app.post("/grade/text")
def grade_text(req: GradeTextRequest, db: Session = Depends(get_db)):
    sub_id = f"{req.exam_id}_{req.student_name.replace(' ', '_').lower()}"
    if db.query(models.Submission).filter(models.Submission.submission_id == sub_id).first():
        raise HTTPException(400, "You have already submitted an answer for this exam.")

    exam = db.query(models.Exam).filter(models.Exam.exam_id == req.exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    
    # Convert DB object back to dict for the logic
    exam_dict = {
        "questions": exam.questions,
        "answer_key": exam.answer_key,
        "rubrics": exam.rubrics,
        "total_marks": exam.total_marks
    }
    result = grade_answer(exam_dict, req.student_answer)
    save_submission(db, req.exam_id, req.student_name, written=result)
    return result


@app.post("/grade/image")
async def grade_image(
    exam_id: str = Form(...),
    student_name: str = Form(...),
    answer_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    sub_id = f"{exam_id}_{student_name.replace(' ', '_').lower()}"
    existing = db.query(models.Submission).filter(models.Submission.submission_id == sub_id).first()
    if existing and existing.written_result:
        raise HTTPException(400, "You have already submitted an answer for this exam.")

    exam = db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    
    exam_dict = {
        "questions": exam.questions,
        "answer_key": exam.answer_key,
        "rubrics": exam.rubrics,
        "total_marks": exam.total_marks
    }

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
    # Using local import for utils to avoid circular issues
    from utils import file_to_image_bytes_list
    
    pages = file_to_image_bytes_list(fake)
    extracted_answer, result = grade_from_images(exam_dict, pages)
    save_submission(db, exam_id, student_name, written={"extracted_answer": extracted_answer, **result})
    return {"extracted_answer": extracted_answer, **result}


# ══════════════════════════════════════════════════════════════════
# VIVA
# ══════════════════════════════════════════════════════════════════

class VivaGenRequest(BaseModel):
    exam_id: str
    student_answer: str
    num_questions: int = 6


@app.post("/viva/generate")
def viva_generate(req: VivaGenRequest, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == req.exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    
    exam_dict = {
        "subject": exam.subject,
        "questions": exam.questions
    }
    questions = generate_viva_questions(exam_dict, req.student_answer, req.num_questions)
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
def viva_grade(req: VivaGradeRequest, db: Session = Depends(get_db)):
    exam = db.query(models.Exam).filter(models.Exam.exam_id == req.exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    
    exam_dict = {
        "subject": exam.subject
    }
    result = grade_viva(exam_dict, req.student_answer, [q.model_dump() for q in req.qa_pairs])
    save_submission(db, req.exam_id, req.student_name, viva=result)
    return result


class VivaFailRequest(BaseModel):
    exam_id: str
    student_name: str
    reason: str

@app.post("/viva/fail")
def viva_fail(req: VivaFailRequest, db: Session = Depends(get_db)):
    """Permanently record a 0 score for a student who was terminated by the proctor."""
    result = {
        "marks_obtained": 0,
        "total_marks": 10,
        "percentage": 0,
        "grade": "F",
        "breakdown": [],
        "overall_feedback": req.reason
    }
    save_submission(db, req.exam_id, req.student_name, viva=result)
    return {"status": "failed_recorded", "result": result}


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
