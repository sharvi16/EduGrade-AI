"""
Student Grader — Assignment Grading System
Student selects an exam, submits their handwritten/typed answer,
and gets marks + detailed feedback based on the teacher's rubric.
"""

import json
import os
import uuid

import streamlit as st
import streamlit.components.v1 as components
from groq import Groq

from utils import (
    GROQ_API_KEY,
    GROQ_VISION_MODEL,
    GROQ_TEXT_MODEL,
    extract_text_from_images,
    file_to_image_bytes_list,
)

# ==================== CONFIG ====================

EXAMS_DIR = os.path.join(os.path.dirname(__file__), "exams")
SUPPORTED_TYPES = ["jpg", "jpeg", "png", "bmp", "tiff", "webp", "pdf"]

EXTRACT_PROMPT = (
    "This is a photo of a student's handwritten exam answer sheet. "
    "Transcribe ALL the written content exactly as it appears — including "
    "numbers, equations, diagrams described in words, and any working shown. "
    "Preserve question numbering and structure. Output only the transcribed text."
)


# ==================== HELPERS ====================

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
    """Grade plain text answer against the rubric. Single API call."""
    client = Groq(api_key=GROQ_API_KEY)

    questions_section  = exam.get("questions",   "Not provided")
    answer_key_section = exam.get("answer_key",  "Not provided")
    rubric_section     = exam.get("rubrics",     "Not provided")
    total_marks        = exam.get("total_marks", 100)

    system_prompt = f"""You are an experienced and fair examiner grading a student's answer.

You will be given:
1. The question paper
2. The expected model answer / answer key
3. The grading rubric (criteria and mark allocation)
4. The student's answer

Your task:
- Grade the student's answer strictly according to the rubric
- Award partial marks where warranted
- Be fair but accurate — do not give marks for incorrect content
- Total marks available: {total_marks}

Respond ONLY with a valid JSON object in exactly this format:
{{
  "marks_obtained": <number>,
  "total_marks": {total_marks},
  "percentage": <number>,
  "grade": "<O/A/B/C/D/F>",
  "section_breakdown": [
    {{"section": "<section/question name>", "marks_awarded": <number>, "max_marks": <number>, "comment": "<brief comment>"}}
  ],
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<area to improve 1>", "<area to improve 2>"],
  "overall_feedback": "<2-3 sentence overall feedback>"
}}"""

    user_prompt = f"""## QUESTION PAPER
{questions_section}

## MODEL ANSWER / ANSWER KEY
{answer_key_section}

## GRADING RUBRIC
{rubric_section}

## STUDENT'S ANSWER
{student_answer}

Grade the student's answer and return JSON only."""

    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


def grade_from_images(exam: dict, image_bytes_list: list) -> tuple[str, dict]:
    """
    FAST PATH: Read handwritten images AND grade in ONE single Vision API call.
    Returns (extracted_text, grading_result_dict).
    Up to 4 pages sent together; saves one full round-trip vs extract-then-grade.
    """
    from utils import image_to_base64 as _b64

    client = Groq(api_key=GROQ_API_KEY)
    questions_section  = exam.get("questions",   "Not provided")
    answer_key_section = exam.get("answer_key",  "Not provided")
    rubric_section     = exam.get("rubrics",     "Not provided")
    total_marks        = exam.get("total_marks", 100)

    # Attach up to 4 image pages
    content = []
    for img_bytes in image_bytes_list[:4]:
        b64 = _b64(img_bytes)
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

    content.append({"type": "text", "text": f"""You are an expert examiner.
The images above are a student's handwritten answer sheet.

STEP 1 — Transcribe the full handwritten content exactly.
STEP 2 — Grade it against the rubric below.

## QUESTION PAPER
{questions_section}

## MODEL ANSWER / ANSWER KEY
{answer_key_section}

## GRADING RUBRIC
{rubric_section}

## TOTAL MARKS: {total_marks}

Return ONLY a valid JSON object:
{{
  "extracted_answer": "<full transcribed answer>",
  "marks_obtained": <number>,
  "total_marks": {total_marks},
  "percentage": <number>,
  "grade": "<O/A/B/C/D/F>",
  "section_breakdown": [{{"section": "<name>", "marks_awarded": <n>, "max_marks": <n>, "comment": "<text>"}}],
  "strengths": ["<strength>"],
  "improvements": ["<improvement>"],
  "overall_feedback": "<2-3 sentence feedback>"
}}"""})

    response = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=0.2,
        max_tokens=3000,
        response_format={"type": "json_object"}
    )
    data = json.loads(response.choices[0].message.content.strip())
    extracted = data.pop("extracted_answer", "")
    return extracted, data


def generate_viva_questions(exam: dict, student_answer: str, num_questions: int = 6) -> list[dict]:
    """
    Generate viva questions based on what the student wrote.
    Returns list of {question, hint_topic}
    """
    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = """You are an examiner conducting an oral viva exam.

Based on the student's submitted written answer and the exam topic, generate targeted viva questions.

Rules:
- Questions should test UNDERSTANDING, not just memory
- Mix question types: definitions, explain-why, what-if scenarios, application
- Questions should be directly related to what the student wrote
- Vary difficulty: some straightforward, some probing
- Each question should be answerable in 1-3 sentences

Return ONLY a valid JSON array in exactly this format:
[
  {"question": "<the viva question>", "topic": "<brief topic tag>"},
  ...
]"""

    user_prompt = f"""Exam subject: {exam.get('subject', 'General')}
Exam title: {exam.get('title', '')}

Student's submitted answer:
{student_answer}

Generate exactly {num_questions} viva questions. Return JSON array only."""

    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.5,
        max_tokens=1024,
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)
    # handle both {"questions": [...]} and direct [...] wrapped in object
    if isinstance(parsed, list):
        return parsed
    for val in parsed.values():
        if isinstance(val, list):
            return val
    return []


def grade_viva(exam: dict, student_answer: str, qa_pairs: list[dict]) -> dict:
    """
    Grade the viva Q&A out of 10 marks.
    qa_pairs: list of {question, topic, student_answer}
    Returns {marks_obtained, total_marks:10, breakdown, overall_feedback}
    """
    client = Groq(api_key=GROQ_API_KEY)

    qa_text = ""
    for i, qa in enumerate(qa_pairs, 1):
        qa_text += f"Q{i} [{qa.get('topic','')}]: {qa['question']}\n"
        qa_text += f"Student answer: {qa.get('student_answer', '(no answer given)')}\n\n"

    system_prompt = """You are an examiner grading an oral viva exam out of 10 marks.

Evaluate each answer for:
- Correctness of the concept
- Clarity of explanation
- Depth of understanding

Be fair — award partial marks for partially correct answers.
Total viva marks: 10  (distribute across all questions proportionally)

Return ONLY a valid JSON object in exactly this format:
{
  "marks_obtained": <number out of 10>,
  "total_marks": 10,
  "breakdown": [
    {"question_no": 1, "question": "<question text>", "marks_awarded": <number>, "max_marks": <number>, "comment": "<brief feedback>"}
  ],
  "overall_feedback": "<2-3 sentence viva performance summary>"
}"""

    user_prompt = f"""Exam subject: {exam.get('subject', 'General')}

Student's written answer (for context):
{student_answer[:800]}...

VIVA Q&A:
{qa_text}

Grade the viva out of 10 marks. Return JSON only."""

    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=1024,
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


def render_grade_badge(grade: str) -> str:
    colours = {
        "O":  ("#1a7f37", "#d4f4dd"),
        "A":  ("#0969da", "#dbeafe"),
        "B":  ("#6e40c9", "#ede9fe"),
        "C":  ("#e65c00", "#fff3cd"),
        "D":  ("#9a3412", "#fee2e2"),
        "F":  ("#6b6b6b", "#f3f4f6"),
    }
    fg, bg = colours.get(grade.upper(), ("#000", "#eee"))
    return (
        f"<span style='background:{bg};color:{fg};padding:4px 14px;"
        f"border-radius:20px;font-weight:700;font-size:1.1rem'>{grade}</span>"
    )


# ==================== UI ====================

def main():
    st.set_page_config(
        page_title="Student Grader",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 Student Answer Grader")
    st.markdown("Select your exam, submit your answer, and get instant AI-powered grading.")
    st.divider()

    # ── Session state init ────────────────────────────────────────
    for key, default in [
        ("grading_result", None),
        ("final_answer", ""),
        ("graded_exam_id", ""),
        ("viva_questions", []),
        ("viva_started", False),
        ("viva_result", None),
        ("viva_tab_switches", 0),
        ("viva_session_id", ""),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ── Load exams ────────────────────────────────────────────────
    exams = load_all_exams()
    if not exams:
        st.warning("No exams available yet. Ask your teacher to create one in the Teacher Portal.")
        return

    # ── Sidebar: exam selector ────────────────────────────────────
    with st.sidebar:
        st.header("📋 Select Exam")
        exam_labels = {
            f"{e['title']}  |  {e.get('subject','')}  |  {e.get('total_marks','?')} marks": e
            for e in exams
        }
        chosen_label = st.selectbox("Choose exam", list(exam_labels.keys()))
        exam = exam_labels[chosen_label]

        st.markdown("---")
        st.markdown(f"**Exam ID**: `{exam['exam_id']}`")
        st.markdown(f"**Total Marks**: {exam.get('total_marks', '?')}")
        st.markdown(f"**Created**: {exam.get('created_at', '')[:10]}")

        if "questions" in exam:
            with st.expander("📄 View Question Paper"):
                st.markdown(exam["questions"])

        st.markdown("---")
        if st.button("🔄 Reset / New Attempt"):
            for k in ("grading_result", "final_answer", "graded_exam_id",
                      "viva_questions", "viva_started", "viva_result",
                      "viva_tab_switches", "viva_session_id"):
                st.session_state[k] = None if k in ("grading_result", "viva_result") else (
                    "" if k in ("final_answer", "graded_exam_id", "viva_session_id") else
                    [] if k == "viva_questions" else
                    0  if k == "viva_tab_switches" else False
                )
            st.rerun()

    # ── Main: answer submission ───────────────────────────────────
    # Only show submission form if not yet graded for this exam
    already_graded = (
        st.session_state.grading_result is not None
        and st.session_state.graded_exam_id == exam["exam_id"]
    )

    if not already_graded:
        st.subheader(f"✏️ Submit Answer for: *{exam['title']}*")

        answer_mode = st.radio(
            "How will you submit your answer?",
            ["📷 Upload photo / PDF of handwritten answer", "⌨️ Type answer directly"],
            horizontal=True
        )

        student_answer_text = ""
        uploaded_file = None
        col1, col2 = st.columns([1, 1])

        if answer_mode == "📷 Upload photo / PDF of handwritten answer":
            with col1:
                uploaded_file = st.file_uploader(
                    "Upload your answer sheet",
                    type=SUPPORTED_TYPES,
                    help="Photo or scan of your handwritten/printed answer"
                )
                if uploaded_file:
                    if not uploaded_file.name.lower().endswith(".pdf"):
                        from PIL import Image
                        import io
                        uploaded_file.seek(0)
                        img = Image.open(io.BytesIO(uploaded_file.read()))
                        uploaded_file.seek(0)
                        st.image(img, width=600)
                    else:
                        st.info(f"PDF uploaded: `{uploaded_file.name}`")
        else:
            with col1:
                student_answer_text = st.text_area(
                    "Type your answer here",
                    height=400,
                    placeholder="Write your complete answer here..."
                )

        st.divider()
        can_grade = (uploaded_file is not None) or (student_answer_text.strip() != "")
        if st.button("🎯 Grade My Answer", type="primary", disabled=not can_grade):

            final_answer = student_answer_text

            if uploaded_file is not None:
                with st.status("⚡ Reading & grading in one step...", expanded=True) as status:
                    try:
                        uploaded_file.seek(0)
                        pages = file_to_image_bytes_list(uploaded_file)
                        st.write(f"→ {len(pages)} page(s) detected")
                        st.write(f"→ Sending to Groq Vision — extracting + grading simultaneously...")
                        final_answer, result = grade_from_images(exam, pages)
                        st.session_state.grading_result = result
                        st.session_state.final_answer    = final_answer
                        st.session_state.graded_exam_id  = exam["exam_id"]
                        st.session_state.viva_questions  = []
                        st.session_state.viva_started    = False
                        st.session_state.viva_result     = None
                        status.update(label="Done ✓  (extracted + graded in one call)", state="complete")
                    except Exception as e:
                        status.update(label=f"Failed: {e}", state="error")
                        st.error(str(e))
                        st.stop()

                with col2:
                    st.subheader("🔤 Extracted Answer Text")
                    st.text_area(
                        "What the AI read from your answer sheet:",
                        value=final_answer,
                        height=350,
                        key="extracted_answer"
                    )

            else:
                final_answer = student_answer_text

                if not final_answer.strip():
                    st.error("No answer text found.")
                    st.stop()

                with st.status("Grading your answer...", expanded=True) as status:
                    st.write(f"Comparing against rubric using `{GROQ_TEXT_MODEL}`...")
                    try:
                        result = grade_answer(exam, final_answer)
                        st.session_state.grading_result = result
                        st.session_state.final_answer    = final_answer
                        st.session_state.graded_exam_id  = exam["exam_id"]
                        st.session_state.viva_questions  = []
                        st.session_state.viva_started    = False
                        st.session_state.viva_result     = None
                        status.update(label="Grading complete ✓", state="complete")
                    except Exception as e:
                        status.update(label=f"Grading failed: {e}", state="error")
                        st.error(str(e))
                        st.stop()

            st.rerun()

    # ── Results (persisted in session state) ─────────────────────
    if st.session_state.grading_result and st.session_state.graded_exam_id == exam["exam_id"]:
        result       = st.session_state.grading_result
        final_answer = st.session_state.final_answer

        st.divider()
        st.subheader("📈 Your Written Answer Results")

        marks = result.get("marks_obtained", 0)
        total = result.get("total_marks", exam.get("total_marks", 100))
        pct   = result.get("percentage", round(marks / total * 100, 1))
        grade = result.get("grade", "—")

        m1, m2, m3 = st.columns(3)
        m1.metric("Marks Obtained", f"{marks} / {total}")
        m2.metric("Percentage", f"{pct}%")
        with m3:
            st.markdown("**Grade**")
            st.markdown(render_grade_badge(grade), unsafe_allow_html=True)

        st.divider()

        breakdown = result.get("section_breakdown", [])
        if breakdown:
            st.subheader("📋 Section Breakdown")
            for sec in breakdown:
                awarded  = sec.get("marks_awarded", 0)
                maximum  = sec.get("max_marks", 0)
                pct_sec  = (awarded / maximum * 100) if maximum else 0
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{sec.get('section', 'Section')}**")
                        st.caption(sec.get("comment", ""))
                    with c2:
                        st.metric("Marks", f"{awarded} / {maximum}", label_visibility="collapsed")
                    st.progress(int(pct_sec) / 100)

        st.divider()

        col_s, col_i = st.columns(2)
        with col_s:
            st.subheader("✅ Strengths")
            for s in result.get("strengths", []):
                st.markdown(f"- {s}")
        with col_i:
            st.subheader("📌 Areas to Improve")
            for imp in result.get("improvements", []):
                st.markdown(f"- {imp}")

        st.subheader("💬 Overall Feedback")
        st.info(result.get("overall_feedback", "No feedback provided."))

        # Download written report
        report  = (
            f"GRADING REPORT\n==============\n"
            f"Exam    : {exam['title']}\n"
            f"Subject : {exam.get('subject','')}\n"
            f"Marks   : {marks} / {total}  ({pct}%)\n"
            f"Grade   : {grade}\n\n"
            f"SECTION BREAKDOWN\n-----------------\n"
        )
        for sec in breakdown:
            report += f"  {sec.get('section','')}: {sec.get('marks_awarded',0)}/{sec.get('max_marks',0)} — {sec.get('comment','')}\n"
        report += "\nSTRENGTHS\n---------\n"
        for s in result.get("strengths", []):
            report += f"  - {s}\n"
        report += "\nAREAS TO IMPROVE\n----------------\n"
        for i in result.get("improvements", []):
            report += f"  - {i}\n"
        report += f"\nOVERALL FEEDBACK\n----------------\n{result.get('overall_feedback','')}\n"

        st.download_button(
            "⬇️ Download Grading Report",
            data=report,
            file_name=f"grade_{exam['exam_id']}.txt",
            mime="text/plain"
        )

        # ═══════════════════════════════════════════════════════════
        # VIVA SECTION (10 marks)
        # ═══════════════════════════════════════════════════════════
        st.divider()
        st.subheader("🎤 Viva Voce — 10 Marks")
        st.caption(
            "Answer these oral-style questions based on your submitted assignment. "
            "Your viva performance adds up to 10 marks on top of your written score."
        )

        # ── Step 1: Generate questions ────────────────────────────
        if not st.session_state.viva_started:
            if st.button("▶️ Start Viva (generates 6 questions)", type="primary"):
                with st.spinner("Generating viva questions based on your answer..."):
                    try:
                        qs = generate_viva_questions(exam, final_answer, num_questions=6)
                        st.session_state.viva_questions  = qs
                        st.session_state.viva_started    = True
                        st.session_state.viva_result     = None
                        st.session_state.viva_tab_switches = 0
                        st.session_state.viva_session_id = str(uuid.uuid4())[:12]
                    except Exception as e:
                        st.error(f"Could not generate viva questions: {e}")
                st.rerun()

        # ── Step 2: Show questions + collect answers ──────────────
        if st.session_state.viva_started and st.session_state.viva_questions:
            if st.session_state.viva_result is None:

                # ── Tab-switch watchdog ───────────────────────────
                session_id = st.session_state.viva_session_id
                ls_key = f"viva_sw_{session_id}"   # localStorage key

                # Hidden sensor input: JS polls and writes switch count here
                raw_val = st.text_input(
                    "tab_sensor",
                    value=str(st.session_state.viva_tab_switches),
                    key="viva_sw_field",
                    label_visibility="collapsed",
                    placeholder=f"__VIVASW_{session_id}__"
                )
                try:
                    sensed = int(raw_val)
                except (ValueError, TypeError):
                    sensed = 0
                if sensed > st.session_state.viva_tab_switches:
                    st.session_state.viva_tab_switches = sensed

                cur_switches = st.session_state.viva_tab_switches

                # JS strategy:
                #  - visibilitychange → increment localStorage count + show alert
                #  - setInterval every 600ms → push current localStorage count to
                #    the hidden Streamlit input via React native setter
                #    (decoupled from alert so blocking doesn't prevent the push)
                placeholder = f"__VIVASW_{session_id}__"
                components.html(
                    f"""<script>
(function() {{
  var KEY = '{ls_key}';
  var PH  = '{placeholder}';

  // Read persisted count (survives component re-renders)
  var count = parseInt(localStorage.getItem(KEY) || '0');

  function pushToStreamlit(val) {{
    try {{
      var inp = window.parent.document.querySelector('input[placeholder="' + PH + '"]');
      if (!inp) return false;
      var nativeSetter = Object.getOwnPropertyDescriptor(
        window.parent.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(inp, String(val));
      inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
      return true;
    }} catch(e) {{ return false; }}
  }}

  // Polling loop: push every 600ms regardless of other events
  setInterval(function() {{
    var stored = parseInt(localStorage.getItem(KEY) || '0');
    if (stored > 0) pushToStreamlit(stored);
  }}, 600);

  // Tab-switch detection
  document.addEventListener('visibilitychange', function() {{
    if (document.hidden) {{
      count++;
      localStorage.setItem(KEY, count);
      // Show alert AFTER scheduling the push (setTimeout → non-blocking)
      var msg;
      if (count === 1)      msg = '[WARNING 1/2] You switched tabs!\\nReturn immediately. One more switch = final warning.';
      else if (count === 2) msg = '[FINAL WARNING 2/2] Do NOT switch tabs again!\\nNext switch will TERMINATE your viva with 0 marks.';
      else                  msg = '[VIVA TERMINATED] You switched tabs 3 times.\\nYour viva score is 0 marks.';
      setTimeout(function() {{ alert(msg); }}, 50);
    }}
  }});
}})();
</script>""",
                    height=0
                )

                # Act on current switch count
                if cur_switches == 1:
                    st.warning("**Warning 1/2** — You switched tabs. One more switch = final warning.")
                elif cur_switches == 2:
                    st.error("**Final Warning (2/2)** — ONE MORE tab switch will TERMINATE your viva with 0 marks!")
                elif cur_switches >= 3:
                    st.session_state.viva_result = {
                        "marks_obtained":  0,
                        "total_marks":     10,
                        "breakdown":       [],
                        "overall_feedback": "Viva terminated: student switched tabs 3 times during the viva session."
                    }
                    # Clear localStorage key so it doesn't affect future vivas
                    components.html(
                        f"<script>localStorage.removeItem('{ls_key}');</script>",
                        height=0
                    )
                    st.rerun()

                viva_inputs: dict[int, str] = {}
                for idx, q in enumerate(st.session_state.viva_questions, 1):
                    with st.container(border=True):
                        st.markdown(
                            f"**Q{idx}** &nbsp; <span style='background:#e8f0fe;color:#1a56db;"
                            f"padding:2px 8px;border-radius:10px;font-size:0.8rem'>"
                            f"{q.get('topic','')}</span>",
                            unsafe_allow_html=True
                        )
                        st.markdown(q["question"])
                        viva_inputs[idx] = st.text_area(
                            "Your answer",
                            key=f"viva_q_{idx}",
                            height=100,
                            label_visibility="collapsed",
                            placeholder="Type your answer here..."
                        )

                st.markdown("")
                all_answered = all(v.strip() for v in viva_inputs.values())
                if st.button("📤 Submit Viva Answers", type="primary", disabled=not all_answered):
                    qa_pairs = [
                        {
                            "question":       st.session_state.viva_questions[i - 1]["question"],
                            "topic":          st.session_state.viva_questions[i - 1].get("topic", ""),
                            "student_answer": ans
                        }
                        for i, ans in viva_inputs.items()
                    ]
                    with st.spinner("Grading your viva answers..."):
                        try:
                            viva_res = grade_viva(exam, final_answer, qa_pairs)
                            st.session_state.viva_result = viva_res
                        except Exception as e:
                            st.error(f"Viva grading failed: {e}")
                    st.rerun()

                if not all_answered:
                    st.caption("⚠️ Please answer all questions before submitting.")

        # ── Step 3: Show viva results ─────────────────────────────
        if st.session_state.viva_result:
            vr          = st.session_state.viva_result
            viva_marks  = vr.get("marks_obtained", 0)
            viva_total  = vr.get("total_marks", 10)
            viva_pct    = round(viva_marks / viva_total * 100, 1)

            st.divider()

            # Show termination notice if viva was auto-ended
            if viva_marks == 0 and "terminated" in vr.get("overall_feedback", "").lower():
                st.error("🚫 **Viva Terminated** — You switched tabs 3 times during the viva. Your viva score is **0 / 10**.")
            else:
                st.subheader("📊 Viva Results")

            vm1, vm2 = st.columns(2)
            vm1.metric("Viva Marks", f"{viva_marks} / {viva_total}")
            vm2.metric("Viva Percentage", f"{viva_pct}%")

            # Combined scorecard
            combined_marks = marks + viva_marks
            combined_total = total + viva_total
            combined_pct   = round(combined_marks / combined_total * 100, 1)
            st.markdown("")
            with st.container(border=True):
                st.markdown("### 🏆 Combined Scorecard")
                cc1, cc2 = st.columns(2)
                cc1.metric("Total Marks (Written + Viva)", f"{combined_marks} / {combined_total}")
                cc2.metric("Overall Percentage", f"{combined_pct}%")

            # Viva question-by-question breakdown
            viva_breakdown = vr.get("breakdown", [])
            if viva_breakdown:
                st.subheader("📋 Viva Breakdown")
                for item in viva_breakdown:
                    qn       = item.get("question_no", "?")
                    awarded  = item.get("marks_awarded", 0)
                    maximum  = item.get("max_marks", 0)
                    pct_q    = (awarded / maximum * 100) if maximum else 0
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"**Q{qn}: {item.get('question', '')}**")
                            st.caption(item.get("comment", ""))
                        with c2:
                            st.metric("Marks", f"{awarded} / {maximum}", label_visibility="collapsed")
                        st.progress(int(pct_q) / 100)

            st.subheader("💬 Viva Feedback")
            st.info(vr.get("overall_feedback", "No feedback provided."))

            # Full combined download
            full_report = (
                report
                + f"\n\nVIVA RESULTS\n============\n"
                f"Viva Marks : {viva_marks} / {viva_total}  ({viva_pct}%)\n\n"
                f"VIVA BREAKDOWN\n--------------\n"
            )
            for item in viva_breakdown:
                full_report += (
                    f"  Q{item.get('question_no','?')}: {item.get('marks_awarded',0)}/{item.get('max_marks',0)}"
                    f" — {item.get('comment','')}\n"
                )
            full_report += (
                f"\nVIVA FEEDBACK\n-------------\n{vr.get('overall_feedback','')}\n\n"
                f"COMBINED TOTAL\n--------------\n"
                f"  Written : {marks}/{total}\n"
                f"  Viva    : {viva_marks}/{viva_total}\n"
                f"  TOTAL   : {combined_marks}/{combined_total}  ({combined_pct}%)\n"
            )
            st.download_button(
                "⬇️ Download Full Report (Written + Viva)",
                data=full_report,
                file_name=f"full_report_{exam['exam_id']}.txt",
                mime="text/plain"
            )


if __name__ == "__main__":
    main()
