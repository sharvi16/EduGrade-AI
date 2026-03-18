"""
Medical Prescription OCR Pipeline - Optimized for 8GB RAM Laptop
Uses TrOCR (CPU) + Groq Cloud API for intelligent text correction
"""

import cv2
import numpy as np
from PIL import Image
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from groq import Groq
import json 
import sys


# ==================== CONFIGURATION ====================

TROCR_MODEL = "microsoft/trocr-base-handwritten"  
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_MODEL = "llama-3.3-70b-versatile"

# ==================== IMAGE PREPROCESSING ====================

def preprocess_image(image_path):
    """
    Preprocess prescription image using OpenCV
    - Grayscale conversion
    - Bilateral filtering for noise reduction
    - Adaptive thresholding for ink isolation
    """
    # Read image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filtering for noise reduction (preserves edges)
    filtered = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Apply adaptive thresholding to isolate handwritten ink
    # ADAPTIVE_THRESH_GAUSSIAN_C gives better results for handwriting
    binary = cv2.adaptiveThreshold(
        filtered,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=11,
        C=2
    )
    
    return image, binary


def segment_lines(binary_image):
    """
    Segment prescription image into individual text lines using horizontal projection
    TrOCR works best on single lines of text
    """
    # Use inverse binary for projection (text = white, background = black)
    binary_inv = cv2.bitwise_not(binary_image)
    
    # Calculate horizontal projection (sum of white pixels in each row)
    horizontal_projection = np.sum(binary_inv, axis=1)
    
    # Find line boundaries
    lines = []
    in_line = False
    line_start = 0
    
    # Adaptive threshold based on average projection
    threshold = np.mean(horizontal_projection) * 0.2
    
    for i, val in enumerate(horizontal_projection):
        if val > threshold and not in_line:
            # Start of a line
            line_start = i
            in_line = True
        elif val <= threshold and in_line:
            # End of a line
            if i - line_start > 20:  # Minimum line height (20 pixels)
                lines.append((line_start, i))
            in_line = False
    
    # Add last line if still in progress
    if in_line and len(horizontal_projection) - line_start > 20:
        lines.append((line_start, len(horizontal_projection)))
    
    print(f"✓ Segmented into {len(lines)} text lines")
    return lines


def extract_line_images(original_image, binary_image, line_boundaries):
    """
    Extract individual line images from the original image
    """
    line_images = []
    
    for start_y, end_y in line_boundaries:
        # Add padding above and below
        y_start = max(0, start_y - 10)
        y_end = min(binary_image.shape[0], end_y + 10)
        
        # Extract line from original image
        line_img = original_image[y_start:y_end, :]
        
        # Skip very small or very large lines
        if 15 < line_img.shape[0] < 200:
            line_images.append(line_img)
    
    return line_images


# ==================== OCR WITH TROCR (CPU) ====================

def load_trocr_model():
    """
    Load TrOCR model on CPU to save memory
    """
    print("Loading TrOCR model (CPU mode for 8GB RAM)...")
    
    # Force CPU usage
    device = torch.device("cpu")
    
    processor = TrOCRProcessor.from_pretrained(TROCR_MODEL)
    model = VisionEncoderDecoderModel.from_pretrained(TROCR_MODEL)
    model.to(device)
    model.eval()  # Set to evaluation mode
    
    print("✓ TrOCR model loaded on CPU")
    return processor, model


def extract_text_from_line(line_image, processor, model):
    """
    Extract text from a single line using TrOCR
    """
    # Convert to PIL Image
    if len(line_image.shape) == 2:
        # Grayscale
        pil_image = Image.fromarray(line_image)
    else:
        # Color - convert BGR to RGB
        rgb_image = cv2.cvtColor(line_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
    
    # Process with TrOCR
    pixel_values = processor(pil_image, return_tensors="pt").pixel_values
    
    # Generate (no GPU needed)
    with torch.no_grad():
        generated_ids = model.generate(pixel_values, max_length=128)
    
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()


def extract_text_from_prescription(image_path, processor, model):
    """
    Complete OCR pipeline: preprocess -> segment -> extract text line by line
    """
    print(f"\n{'='*60}")
    print(f"Processing: {image_path}")
    print(f"{'='*60}")
    
    # Step 1: Preprocess
    print("\n[1/3] Preprocessing image...")
    original_image, binary_image = preprocess_image(image_path)
    print("✓ Applied grayscale, bilateral filtering, and adaptive thresholding")
    
    # Step 2: Segment lines
    print("\n[2/3] Segmenting text lines...")
    line_boundaries = segment_lines(binary_image)
    line_images = extract_line_images(original_image, binary_image, line_boundaries)
    
    # Step 3: Extract text from each line
    print(f"\n[3/3] Extracting text with TrOCR (processing {len(line_images)} lines)...")
    all_text_lines = []
    
    for i, line_img in enumerate(line_images, 1):
        text = extract_text_from_line(line_img, processor, model)
        if text and len(text) > 1:  # Skip empty or single-char extractions
            print(f"  Line {i}: {text}")
            all_text_lines.append(text)
    
    raw_ocr_text = "\n".join(all_text_lines)
    
    print(f"\n{'='*60}")
    print("RAW OCR OUTPUT:")
    print(f"{'='*60}")
    print(raw_ocr_text if raw_ocr_text else "[No text extracted]")
    
    return raw_ocr_text


# ==================== GROQ API - CONTEXT LAYER ====================

def correct_with_groq(raw_ocr_text, api_key):
    """
    Send raw OCR text to Groq API for intelligent correction
    Role: Pharmacist correcting handwriting errors
    """
    if not api_key:
        print("\n⚠ WARNING: GROQ_API_KEY not set. Skipping LLM correction.")
        return []
    
    print(f"\n{'='*60}")
    print("CONTEXT LAYER: Groq API (Pharmacist Role)")
    print(f"{'='*60}")
    
    client = Groq(api_key=api_key)
    
    # Pharmacist prompt
    system_prompt = """You are an experienced pharmacist. Your task is to correct messy handwritten prescription text from OCR.

Common errors in doctor's handwriting:
- 'T. Pn 40' → 'Tablet Pan-40'
- 'Paractamol 500mq' → 'Paracetamol 500mg'
- 'Brufen 400' → 'Brufen 400mg'
- 'od' → 'once daily', 'bd' → 'twice daily', 'tds' → 'three times daily'

Return a JSON array with each medicine as an object containing:
- medicine: corrected medicine name
- dosage: corrected dosage with proper units
- frequency: how often to take (if mentioned)

If no valid medicines found, return []"""

    user_prompt = f"""Correct this prescription OCR text and extract medicine information:

{raw_ocr_text}

Return ONLY valid JSON array."""

    try:
        # Call Groq API
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON from markdown code blocks if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        medicines = json.loads(result_text)
        
        print(f"✓ Groq API processed successfully")
        print(f"✓ Extracted {len(medicines)} medicine(s)")
        
        return medicines
    
    except Exception as e:
        print(f"✗ Error calling Groq API: {e}")
        return []


# ==================== MAIN PIPELINE ====================

def process_prescription(image_path, groq_api_key):
    """
    Complete pipeline: Image → Preprocessing → TrOCR → Groq → Structured JSON
    """
    # Load TrOCR model (once)
    processor, model = load_trocr_model()
    
    # Extract raw text with OCR
    raw_text = extract_text_from_prescription(image_path, processor, model)
    
    # Correct with Groq API
    structured_output = correct_with_groq(raw_text, groq_api_key)
    
    # Final output
    print(f"\n{'='*60}")
    print("FINAL STRUCTURED OUTPUT (JSON)")
    print(f"{'='*60}")
    print(json.dumps(structured_output, indent=2, ensure_ascii=False))
    
    return {
        "raw_ocr": raw_text,
        "structured_data": structured_output
    }


# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    # Check if image path provided
    if len(sys.argv) < 2:
        print("Usage: python medical_ocr_groq.py <image_path>")
        print("\nExample:")
        print('  python medical_ocr_groq.py "prescription.jpg"')
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Check if Groq API key is set
    if not GROQ_API_KEY:
        print("⚠ WARNING: GROQ_API_KEY not set in script!")
        print("Set it in the script or use environment variable:")
        print('  $env:GROQ_API_KEY="your_key_here"')
        print("\nContinuing with OCR only (no LLM correction)...\n")
    
    # Get API key from environment if not set in script
    import os
    api_key = GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
    
    # Run pipeline
    result = process_prescription(image_path, api_key)
