"""
Teacher Portal — Assignment Grading System
Teacher uploads:
  1. Question paper  (image / PDF)
  2. Expected answer key  (image / PDF)
  3. Rubrics / grading criteria  (image / PDF or typed)

All content is extracted via Groq Vision and saved as a JSON exam file
that the student grader will use when evaluating submissions.
"""

import json
import os
import uuid
from datetime import datetime

import streamlit as st

from utils import (
    GROQ_VISION_MODEL,
    GROQ_TEXT_MODEL,
    extract_text_from_images,
    file_to_image_bytes_list,
    image_to_base64,
)

# ==================== CONFIG ====================

EXAMS_DIR = os.path.join(os.path.dirname(__file__), "exams")
os.makedirs(EXAMS_DIR, exist_ok=True)

SUPPORTED_TYPES = ["jpg", "jpeg", "png", "bmp", "tiff", "webp", "pdf"]


# ==================== PROMPTS ====================

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


# ==================== HELPERS ====================

def save_exam(data: dict) -> str:
    """Save exam data dict to a JSON file. Returns the file path."""
    filename = f"{data['exam_id']}.json"
    path = os.path.join(EXAMS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_all_exams() -> list[dict]:
    """Load all saved exam JSON files, sorted newest first."""
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


def delete_exam(exam_id: str):
    path = os.path.join(EXAMS_DIR, f"{exam_id}.json")
    if os.path.exists(path):
        os.remove(path)


def extract_section(label: str, uploaded_file, prompt: str) -> str | None:
    """
    Show a status box, extract text from uploaded file via Groq Vision.
    Returns extracted text or None on failure.
    """
    with st.status(f"Extracting {label}...", expanded=True) as status:
        try:
            st.write(f"Processing `{uploaded_file.name}`...")
            pages = file_to_image_bytes_list(uploaded_file)
            st.write(f"  → {len(pages)} page(s) detected")
            st.write(f"  → Sending to Groq Vision (`{GROQ_VISION_MODEL}`)...")
            text = extract_text_from_images(pages, prompt)
            status.update(label=f"{label} extracted ✓", state="complete")
            return text
        except Exception as e:
            status.update(label=f"{label} failed: {e}", state="error")
            st.error(str(e))
            return None


# ==================== PAGES ====================

def page_create_exam():
    st.header("📄 Create New Exam")
    st.caption("Upload the question paper, answer key, and rubric. Groq Vision will extract the content.")

    # ── Exam Metadata ────────────────────────────────────────────
    st.subheader("Exam Details")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        exam_title   = st.text_input("Exam Title *", placeholder="e.g. OS Unit 2 Quiz")
    with col_b:
        subject      = st.text_input("Subject", placeholder="e.g. Operating Systems")
    with col_c:
        total_marks  = st.number_input("Total Marks", min_value=1, max_value=1000, value=20)

    st.divider()

    # ── Upload Sections ──────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📋 Question Paper")
        q_file = st.file_uploader(
            "Upload questions (image or PDF)",
            type=SUPPORTED_TYPES,
            key="q_upload",
            help="Handwritten or typed question paper"
        )
        if q_file:
            if q_file.name.lower().endswith(".pdf"):
                st.info(f"PDF: `{q_file.name}`")
            else:
                from PIL import Image; import io
                q_file.seek(0); st.image(Image.open(io.BytesIO(q_file.read())), width=600); q_file.seek(0)

    with col2:
        st.subheader("✅ Expected Answer Key")
        a_file = st.file_uploader(
            "Upload answer key (image or PDF)",
            type=SUPPORTED_TYPES,
            key="a_upload",
            help="Model answers / expected responses"
        )
        if a_file:
            if a_file.name.lower().endswith(".pdf"):
                st.info(f"PDF: `{a_file.name}`")
            else:
                from PIL import Image; import io
                a_file.seek(0); st.image(Image.open(io.BytesIO(a_file.read())), width=600); a_file.seek(0)

    with col3:
        st.subheader("📊 Rubric / Marking Scheme")
        rubric_mode = st.radio(
            "Rubric input method",
            ["Upload file", "Type manually"],
            horizontal=True,
            key="rubric_mode"
        )

        r_file  = None
        r_typed = ""

        if rubric_mode == "Upload file":
            r_file = st.file_uploader(
                "Upload rubric (image or PDF)",
                type=SUPPORTED_TYPES,
                key="r_upload",
                help="Grading criteria and mark allocation"
            )
            if r_file:
                if r_file.name.lower().endswith(".pdf"):
                    st.info(f"PDF: `{r_file.name}`")
                else:
                    from PIL import Image; import io
                    r_file.seek(0); st.image(Image.open(io.BytesIO(r_file.read())), width=600); r_file.seek(0)
        else:
            r_typed = st.text_area(
                "Type rubric here",
                height=250,
                placeholder=(
                    "Example:\n"
                    "Q1 (5 marks):\n"
                    "  - Correct definition: 2 marks\n"
                    "  - Two valid states listed: 2 marks\n"
                    "  - Neat diagram: 1 mark\n"
                )
            )

    st.divider()

    # ── Submit ───────────────────────────────────────────────────
    if not exam_title.strip():
        st.warning("Please enter an Exam Title before saving.")
        return

    if st.button("🚀 Extract & Save Exam", type="primary"):

        if not q_file and not a_file and not r_file and not r_typed.strip():
            st.error("Please upload at least one file.")
            return

        extracted = {}

        # Reset file pointers before reading (Streamlit may have consumed them for preview)
        if q_file:
            q_file.seek(0)
            result = extract_section("Question Paper", q_file, QUESTION_PROMPT)
            if result is None:
                return
            extracted["questions"] = result

        if a_file:
            a_file.seek(0)
            result = extract_section("Answer Key", a_file, ANSWER_PROMPT)
            if result is None:
                return
            extracted["answer_key"] = result

        if r_file:
            r_file.seek(0)
            result = extract_section("Rubric", r_file, RUBRIC_PROMPT)
            if result is None:
                return
            extracted["rubrics"] = result
        elif r_typed.strip():
            extracted["rubrics"] = r_typed.strip()

        # ── Preview ──────────────────────────────────────────
        st.divider()
        st.subheader("🔍 Extracted Content Preview")

        tabs = st.tabs([k.replace("_", " ").title() for k in extracted])
        for tab, (key, text) in zip(tabs, extracted.items()):
            with tab:
                edited = st.text_area(
                    f"Edit if needed:",
                    value=text,
                    height=300,
                    key=f"edit_{key}"
                )
                extracted[key] = edited   # use edited version

        # ── Save ─────────────────────────────────────────────
        exam_data = {
            "exam_id":     str(uuid.uuid4())[:8],
            "title":       exam_title.strip(),
            "subject":     subject.strip(),
            "total_marks": int(total_marks),
            "created_at":  datetime.now().isoformat(timespec="seconds"),
            **extracted
        }

        path = save_exam(exam_data)
        st.success(f"Exam saved! ID: `{exam_data['exam_id']}` → `{os.path.basename(path)}`")

        with st.expander("View saved JSON"):
            st.json(exam_data)


def page_view_exams():
    st.header("📚 Saved Exams")

    exams = load_all_exams()
    if not exams:
        st.info("No exams saved yet. Go to **Create New Exam** to add one.")
        return

    for exam in exams:
        with st.expander(
            f"**{exam.get('title', 'Untitled')}**  "
            f"| {exam.get('subject', '')}  "
            f"| {exam.get('total_marks', '?')} marks  "
            f"| ID: `{exam.get('exam_id', '')}`  "
            f"| {exam.get('created_at', '')}"
        ):
            tabs_labels = []
            if "questions"  in exam: tabs_labels.append("Questions")
            if "answer_key" in exam: tabs_labels.append("Answer Key")
            if "rubrics"    in exam: tabs_labels.append("Rubrics")

            if tabs_labels:
                tabs = st.tabs(tabs_labels)
                idx = 0
                for key, label in [("questions", "Questions"),
                                    ("answer_key", "Answer Key"),
                                    ("rubrics", "Rubrics")]:
                    if key in exam:
                        with tabs[idx]:
                            st.text_area(
                                label,
                                value=exam[key],
                                height=250,
                                disabled=True,
                                key=f"view_{exam['exam_id']}_{key}"
                            )
                        idx += 1

            col_dl, col_del = st.columns([3, 1])
            with col_dl:
                st.download_button(
                    "⬇️ Download JSON",
                    data=json.dumps(exam, indent=2),
                    file_name=f"{exam.get('exam_id', 'exam')}.json",
                    mime="application/json",
                    key=f"dl_{exam['exam_id']}"
                )
            with col_del:
                if st.button("🗑️ Delete", key=f"del_{exam['exam_id']}"):
                    delete_exam(exam["exam_id"])
                    st.rerun()


# ==================== MAIN ====================

def main():
    st.set_page_config(
        page_title="Teacher Portal — Assignment Grader",
        page_icon="🏫",
        layout="wide"
    )

    st.title("🏫 Teacher Portal")
    st.markdown("Set up exams by uploading the **question paper**, **answer key**, and **rubric**.")
    st.divider()

    # ── Sidebar Navigation ────────────────────────────────────────
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Go to",
            ["➕ Create New Exam", "📚 View Saved Exams"],
            label_visibility="collapsed"
        )
        st.markdown("---")
        st.markdown("**Models**")
        st.markdown(f"- Vision: `{GROQ_VISION_MODEL}`")
        st.markdown(f"- Text: `{GROQ_TEXT_MODEL}`")
        st.markdown("---")
        saved_count = len(load_all_exams())
        st.metric("Saved Exams", saved_count)

    if page == "➕ Create New Exam":
        page_create_exam()
    else:
        page_view_exams()


if __name__ == "__main__":
    main()
