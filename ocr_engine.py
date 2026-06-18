"""
ocr_engine.py - Camera / Image OCR Engine.

Extracts Tamil/English poem text from uploaded images using Gemini Vision.
"""

from __future__ import annotations

import io
import os
import re
import time

MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

OCR_PROMPT = """You are a Tamil and English literary OCR assistant.

Look at this image carefully. It may contain:
- A Tamil poem (classical or modern)
- An English poem or translation
- A mix of both Tamil and English text
- A photo of a book page, manuscript, or handwritten poem

Your task:
1. Extract ALL the poem/literary text you can see
2. Preserve line breaks exactly as they appear
3. Do NOT add any explanation, title, or commentary
4. Do NOT translate - output the text exactly as it appears
5. If both Tamil and English are present, output both with a blank line between them

After the extracted text, on a new line write exactly one of:
LANGUAGE: tamil
LANGUAGE: english
LANGUAGE: mixed

Output ONLY the poem text and the LANGUAGE line. Nothing else."""


def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> tuple[str, str]:
    """
    Extract poem text from an image using Gemini Vision.

    Returns:
        (extracted_text, detected_language)
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not set.")
    if not image_bytes:
        raise ValueError("No image bytes received from upload/camera input.")

    last_error: Exception | None = None
    for model_name in MODELS_TO_TRY:
        for attempt in range(1, 4):
            try:
                print(f"[ocr] Trying {model_name} (attempt {attempt}/3)...")
                raw = _call_gemini_vision(image_bytes, mime_type, api_key, model_name)
                extracted, lang = _parse_response(raw)
                extracted = _clean_text(extracted)
                if not extracted.strip():
                    raise ValueError("Gemini returned an empty OCR result.")
                print(f"[ocr] {model_name} succeeded. Language: {lang}")
                return extracted, lang
            except Exception as exc:
                last_error = exc
                err = str(exc)
                if any(x in err for x in ("429", "quota", "RESOURCE_EXHAUSTED", "rate")):
                    print(f"[ocr] {model_name} quota hit, trying next model...")
                    break
                if any(x in err for x in ("503", "UNAVAILABLE", "high demand")):
                    wait = 5 * attempt
                    print(f"[ocr] {model_name} overloaded, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if any(x in err for x in ("404", "not found")):
                    print(f"[ocr] {model_name} unavailable, skipping...")
                    break
                print(f"[ocr] {model_name}: {err[:180]}")
                break

    raise RuntimeError(f"All OCR models failed. Last error: {last_error}")


def _call_gemini_vision(image_bytes: bytes, mime_type: str, api_key: str, model_name: str) -> str:
    """Call Gemini Vision using the google-generativeai SDK."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    image = _prepare_image_for_vision(image_bytes)
    response = model.generate_content(
        [OCR_PROMPT, image],
        generation_config={"temperature": 0.0},
    )
    text = getattr(response, "text", "") or ""
    if not text and getattr(response, "candidates", None):
        try:
            text = response.candidates[0].content.parts[0].text
        except Exception:
            text = ""
    if not text:
        raise RuntimeError("Gemini Vision returned no text.")
    return text


def _prepare_image_for_vision(image_bytes: bytes):
    """Open and normalize images from camera/upload before sending to Gemini."""
    from PIL import Image, ImageOps

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.load()
    except Exception as exc:
        raise ValueError("Uploaded file is not a readable image.") from exc

    return image


def _parse_response(raw: str) -> tuple[str, str]:
    """Split Gemini response into (poem_text, language)."""
    raw = (raw or "").strip()
    lang = "unknown"

    lang_match = re.search(r"LANGUAGE:\s*(tamil|english|mixed)", raw, re.IGNORECASE)
    if lang_match:
        lang = lang_match.group(1).lower()
        raw = raw[: lang_match.start()].strip()

    if lang == "unknown":
        tamil_chars = len(re.findall(r"[\u0B80-\u0BFF]", raw))
        english_chars = len(re.findall(r"[A-Za-z]", raw))
        if tamil_chars > 10 and english_chars > 10:
            lang = "mixed"
        elif tamil_chars > 10:
            lang = "tamil"
        else:
            lang = "english"

    return raw, lang


def _clean_text(text: str) -> str:
    lines = (text or "").splitlines()
    cleaned = [line.strip() for line in lines]
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned)


def image_bytes_from_upload(uploaded_file) -> tuple[bytes, str]:
    """Convert a Streamlit UploadedFile/CameraInput to (bytes, mime_type)."""
    if hasattr(uploaded_file, "getvalue"):
        img_bytes = uploaded_file.getvalue()
    else:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        img_bytes = uploaded_file.read()

    if not img_bytes:
        raise ValueError("Image upload was empty.")

    name = (getattr(uploaded_file, "name", "") or "").lower()
    mime = getattr(uploaded_file, "type", "") or ""
    if not mime:
        if name.endswith(".png"):
            mime = "image/png"
        elif name.endswith(".webp"):
            mime = "image/webp"
        else:
            mime = "image/jpeg"
    return img_bytes, mime
