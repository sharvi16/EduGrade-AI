"""
Shared utilities for the Assignment Grading System
- Image enhancement
- PDF → image conversion  
- Groq Vision text extraction
"""

import base64
import os
import tempfile

import cv2
import fitz  # PyMuPDF
import numpy as np
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ==================== CONFIG ====================

GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # only active Groq vision model
GROQ_TEXT_MODEL   = "llama-3.3-70b-versatile"


# ==================== IMAGE HELPERS ====================

def enhance_image_bytes(img_bytes: bytes) -> bytes:
    """Enhance image bytes: upscale if small, CLAHE contrast boost. Returns JPEG bytes under 4MB."""
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return img_bytes

    h, w = img.shape[:2]
    if w < 1200:
        scale = 1200 / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_CUBIC)

    # CLAHE on luminance only
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    # Encode and enforce Groq's 4MB base64 limit (~3MB raw JPEG)
    # Reduce quality or downscale until under limit
    quality = 90
    while True:
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        result = buf.tobytes()
        # base64 size = ceil(len * 4/3); keep raw JPEG under ~2.9MB to be safe
        if len(result) <= 2_900_000 or quality <= 50:
            return result
        quality -= 10
        # If still too big at quality 50, also downscale
        if quality <= 50:
            h, w = img.shape[:2]
            img = cv2.resize(img, (int(w * 0.75), int(h * 0.75)),
                             interpolation=cv2.INTER_AREA)
            quality = 75


def enhance_image_file(image_path: str) -> bytes:
    """Enhance an image file and return JPEG bytes."""
    with open(image_path, "rb") as f:
        return enhance_image_bytes(f.read())


def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# ==================== PDF SUPPORT ====================

def pdf_to_image_bytes_list(pdf_path: str, dpi: int = 200) -> list[bytes]:
    """
    Convert each page of a PDF to a JPEG bytes object.
    Returns a list — one item per page.
    """
    doc = fitz.open(pdf_path)
    pages = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)  # scale factor

    for page in doc:
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img_bytes = pix.tobytes("jpeg")
        pages.append(enhance_image_bytes(img_bytes))

    doc.close()
    return pages


def file_to_image_bytes_list(uploaded_file) -> list[bytes]:
    """
    Accept a Streamlit UploadedFile (image or PDF).
    Returns a list of JPEG bytes (one per page for PDF, one item for image).
    """
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()

    if name.endswith(".pdf"):
        # Write to temp file for PyMuPDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
        try:
            pages = pdf_to_image_bytes_list(tmp_path)
        finally:
            os.unlink(tmp_path)
        return pages
    else:
        # Image file
        return [enhance_image_bytes(raw)]


# ==================== GROQ VISION ====================

def _extract_single_page(
    args: tuple
) -> tuple[int, str]:
    """Worker: extract text from one image page. Returns (index, text)."""
    i, img_bytes, prompt, api_key, multi_page = args
    client = Groq(api_key=api_key)
    b64 = image_to_base64(img_bytes)
    response = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text",      "text": prompt}
                ]
            }
        ],
        temperature=0.1,
        max_tokens=4096
    )
    page_text = response.choices[0].message.content.strip()
    return i, (f"[Page {i + 1}]\n{page_text}" if multi_page else page_text)


def extract_text_from_images(
    image_bytes_list: list[bytes],
    prompt: str,
    api_key: str = GROQ_API_KEY
) -> str:
    """
    Send one or more images to Groq Vision and return extracted text.
    Pages are processed in parallel for speed.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    multi = len(image_bytes_list) > 1
    args = [(i, b, prompt, api_key, multi) for i, b in enumerate(image_bytes_list)]

    results = {}
    with ThreadPoolExecutor(max_workers=min(len(args), 5)) as ex:
        futures = {ex.submit(_extract_single_page, a): a[0] for a in args}
        for fut in as_completed(futures):
            i, text = fut.result()
            results[i] = text

    return "\n\n".join(results[i] for i in sorted(results))
