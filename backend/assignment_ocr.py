"""
Student Assignment OCR
Upload a photo of a handwritten assignment → Groq Vision reads it → Clean text output
"""

import streamlit as st

from utils import (
    GROQ_API_KEY,
    GROQ_VISION_MODEL,
    GROQ_TEXT_MODEL,
    extract_text_from_images,
    file_to_image_bytes_list,
)
from groq import Groq

# ==================== GROQ VISION — EXTRACT TEXT ====================

ASSIGNMENT_PROMPT = (
    "This is a photo of a student's handwritten assignment. "
    "Please transcribe ALL the handwritten text exactly as written, "
    "preserving the structure, headings, numbered points, and paragraphs. "
    "Do not summarise, interpret, add, or remove anything. "
    "Output only the transcribed text."
)




# ==================== GROQ TEXT — POLISH ====================

def polish_text_with_groq(raw_text: str, api_key: str):
    """Optional second pass to fix any remaining transcription errors."""
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are proofreading a transcript of a student's handwritten assignment. "
                    "Fix any transcription errors (wrong letters, missing spaces, garbled words) "
                    "caused by imperfect handwriting recognition. "
                    "Do NOT change the student's content, ideas, or structure. "
                    "Return only the corrected text."
                )
            },
            {
                "role": "user",
                "content": raw_text
            }
        ],
        temperature=0.15,
        max_tokens=4096
    )

    return response.choices[0].message.content.strip(), None


# ==================== STREAMLIT UI ====================

def main():
    st.set_page_config(
        page_title="Student Assignment OCR",
        page_icon="📝",
        layout="wide"
    )

    st.title("📝 Student Assignment OCR")
    st.markdown(
        "Upload a photo of your **handwritten assignment**. "
        "Groq Vision will read the handwriting and convert it to clean text."
    )
    st.divider()

    # ── Sidebar ──────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Settings")
        polish = st.toggle(
            "Polish text after extraction",
            value=True,
            help="Run a second Groq pass to fix any remaining transcription errors"
        )
        st.markdown("---")
        st.markdown("**Models used**")
        st.markdown(f"- **Vision**: `{GROQ_VISION_MODEL}`")
        st.markdown(f"- **Polish**: `{GROQ_TEXT_MODEL}`")

    # ── File Upload ───────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Upload assignment photo",
        type=["jpg", "jpeg", "png", "bmp", "tiff", "webp", "pdf"],
        help="Take a clear, well-lit photo of the handwritten assignment"
    )

    if uploaded_file is not None:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📷 Uploaded Image")
            if not uploaded_file.name.lower().endswith(".pdf"):
                uploaded_file.seek(0)
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(uploaded_file.read()))
                uploaded_file.seek(0)
                st.image(img, width=600)
            else:
                st.info(f"📄 PDF uploaded: `{uploaded_file.name}`")

        if st.button("🔍 Extract Text", type="primary"):

            # ── Step 1: Process file ────────────────────────────
            with st.status("Processing file...", expanded=True) as status:
                try:
                    uploaded_file.seek(0)
                    pages = file_to_image_bytes_list(uploaded_file)
                    st.write(f"→ {len(pages)} page(s) ready")
                    status.update(label="File ready ✓", state="complete")
                except Exception as e:
                    status.update(label=f"File error: {e}", state="error")
                    st.stop()

            # ── Step 2: Vision extraction ──────────────────────
            with st.status("Reading handwriting with Groq Vision...", expanded=True) as status:
                st.write(f"Sending to `{GROQ_VISION_MODEL}`...")
                try:
                    raw_text = extract_text_from_images(pages, ASSIGNMENT_PROMPT, GROQ_API_KEY)
                    status.update(label="Handwriting extracted ✓", state="complete")
                except Exception as e:
                    status.update(label=f"Vision error: {e}", state="error")
                    st.error(str(e))
                    st.stop()

            # Show raw extraction
            with col2:
                st.subheader("🔤 Extracted Text (raw)")
                st.text_area(
                    "Direct output from the vision model:",
                    value=raw_text,
                    height=350,
                    key="raw_text"
                )

            # ── Step 3: Optional polish ────────────────────────
            final_text = raw_text
            if polish and raw_text.strip():
                with st.status("Polishing text...", expanded=True) as status:
                    st.write(f"Running final pass with `{GROQ_TEXT_MODEL}`...")
                    try:
                        polished, err = polish_text_with_groq(raw_text, GROQ_API_KEY)
                        if err:
                            raise RuntimeError(err)
                        final_text = polished
                        status.update(label="Text polished ✓", state="complete")
                    except Exception as e:
                        status.update(label=f"Polish skipped: {e}", state="warning")

            # ── Final output ──────────────────────────────────
            if final_text.strip():
                st.divider()
                st.subheader("✅ Final Clean Text")
                st.markdown(
                    "<div style='background:#f0f7f0; padding:1.5rem; "
                    "border-radius:8px; border-left:4px solid #28a745; "
                    "font-size:1.05rem; line-height:1.8; white-space:pre-wrap;'>"
                    + final_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>") +
                    "</div>",
                    unsafe_allow_html=True
                )

                st.download_button(
                    label="⬇️ Download as .txt",
                    data=final_text,
                    file_name="assignment_extracted.txt",
                    mime="text/plain"
                )


if __name__ == "__main__":
    main()
