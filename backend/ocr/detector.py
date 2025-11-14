import os
import re
import base64
import traceback
from dotenv import load_dotenv

# local OCR
try:
    import easyocr
except Exception as e:
    easyocr = None
    print("EasyOCR import failed:", e)

# Groq client
try:
    from groq import Groq, BadRequestError, AuthenticationError
except Exception as e:
    Groq = None
    BadRequestError = Exception
    AuthenticationError = Exception
    print("Groq import issue:", e)

load_dotenv()
GROQ_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")

# init easyocr reader lazily (costly)
_reader = None
def get_reader():
    global _reader
    if _reader is None:
        if easyocr is None:
            return None
        _reader = easyocr.Reader(['en'], gpu=False)
    return _reader

# init groq client
_client = None
if GROQ_KEY and Groq is not None:
    try:
        _client = Groq(api_key=GROQ_KEY)
    except Exception as e:
        print("Groq client init failed:", e)
        _client = None

ISO_PATTERN = re.compile(r"[A-Z]{4}[0-9]{7}")

def run_local_ocr_debug(image_path):
    """Return joined raw OCR text (for debugging)."""
    reader = get_reader()
    if not reader:
        return ""
    try:
        texts = reader.readtext(image_path, detail=0)
        return " ".join(texts).upper() if texts else ""
    except Exception as e:
        print("EasyOCR readtext error:", e)
        return ""

# --- VISION FORMATTING ATTEMPTS ---
def _try_groq_format_blocks(img_b64, prompt, model):
    if not _client:
        raise RuntimeError("Groq client not initialized")
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_b64}"}
                ]
            }
        ],
        temperature=0,
        max_tokens=40
    )
    return resp.choices[0].message.content.strip()

def _try_groq_markdown_image(img_b64, prompt, model):
    if not _client:
        raise RuntimeError("Groq client not initialized")
    md = prompt + "\n\nImage:\n\n" + f"![img](data:image/jpeg;base64,{img_b64})"
    resp = _client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": md}],
        temperature=0,
        max_tokens=40
    )
    return resp.choices[0].message.content.strip()

def _try_groq_image_object(img_b64, prompt, model):
    if not _client:
        raise RuntimeError("Groq client not initialized")
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "input_image", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }
        ],
        temperature=0,
        max_tokens=40
    )
    return resp.choices[0].message.content.strip()

# --- main function ---
def extract_container_id(image_path):
    try:
        # Local OCR first
        local_text = run_local_ocr_debug(image_path)
        if local_text:
            m = ISO_PATTERN.findall(local_text)
            if m:
                return m[0]

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        prompt = (
            "Extract ONLY the shipping container number (ISO-6346).\n"
            "Format: 4 uppercase letters + 7 digits (e.g. MSCU1234567).\n"
            "Return ONLY the code or UNKNOWN.\n"
        )

        if _client:
            try:
                out = _try_groq_format_blocks(img_b64, prompt, GROQ_MODEL)
                if out:
                    found = ISO_PATTERN.findall(out.upper())
                    if found:
                        return found[0]
            except Exception as e:
                print("Groq attempt blocks failed:", e)

            try:
                out = _try_groq_markdown_image(img_b64, prompt, GROQ_MODEL)
                if out:
                    found = ISO_PATTERN.findall(out.upper())
                    if found:
                        return found[0]
            except Exception as e:
                print("Groq attempt markdown failed:", e)

            try:
                out = _try_groq_image_object(img_b64, prompt, GROQ_MODEL)
                if out:
                    found = ISO_PATTERN.findall(out.upper())
                    if found:
                        return found[0]
            except Exception as e:
                print("Groq attempt image_object failed:", e)

        if local_text:
            found = ISO_PATTERN.findall(local_text)
            if found:
                return found[0]

        return "UNKNOWN"

    except Exception as e:
        print("extract_container_id unexpected error:", e)
        traceback.print_exc()
        return "UNKNOWN"
