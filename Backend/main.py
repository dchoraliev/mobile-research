from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Annotated
from starlette.middleware.base import BaseHTTPMiddleware
import os
import csv
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\choralievd\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

load_dotenv()

from search import search, format_context

app = FastAPI()

SYSTEM_PROMPT_RESEARCH = (
    "You are a research assistant helping analyze academic papers. "
    "Answer the user's question by synthesizing the provided context. "
    "Draw reasonable inferences from what the documents do say. "
    "When referencing sources, use their source filename, not their document number. "
    "Do not refuse to answer if relevant context exists. "
    "Never say the documents lack information if they contain anything relevant."
)

SYSTEM_PROMPT_PHOTO = (
    "You are a research assistant. The user has attached a photo with text extracted via OCR. "
    "Answering their question about that photo is your primary job. "
    "Knowledge-base context is provided as supporting background — use it if it clearly relates "
    "to the photo or question, otherwise answer using the photo and OCR text alone. "
    "Draw reasonable inferences from what the photo and documents do say. "
    "When referencing sources, use their source filename, not their document number. "
    "Do not refuse to answer if relevant context or a photo exists."
)

SYSTEM_PROMPT_CAPTION = (
    "You are a research assistant. The user has attached a photo; an automatic image-captioning "
    "model (BLIP) has generated a short caption describing what the photo shows. No OCR text is "
    "available for this photo. Answering their question about that photo is your primary job. "
    "Knowledge-base context is provided as supporting background — use it if it clearly relates "
    "to the photo or question, otherwise answer using the caption and question alone. "
    "Draw reasonable inferences from what the caption and documents do say. "
    "When referencing sources, use their source filename, not their document number. "
    "Do not refuse to answer if relevant context or a photo exists."
)

# ── Measurement logging ───────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEASUREMENTS_DIR = os.path.join(BASE_DIR, "measurements")
LOG_FILE     = os.path.join(MEASUREMENTS_DIR, "measurements.csv")
EVAL_FILE    = os.path.join(MEASUREMENTS_DIR, "evaluations.csv")
ANSWERS_FILE = os.path.join(MEASUREMENTS_DIR, "answers.csv")
os.makedirs(MEASUREMENTS_DIR, exist_ok=True)

if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
    with open(LOG_FILE, "w", newline="") as f:
        csv.writer(f).writerow([
            "timestamp", "scenario", "endpoint",
            "request_bytes", "response_bytes", "total_bytes",
            "end_to_end_ms", "ocr_ms", "caption_ms", "embedding_ms",
            "retrieval_ms", "llm_ms"
        ])

if not os.path.exists(EVAL_FILE) or os.path.getsize(EVAL_FILE) == 0:
    with open(EVAL_FILE, "w", newline="") as f:
        csv.writer(f).writerow([
            "timestamp", "scenario", "query",
            "sources_returned", "sources_expected",
            "recall_at_k", "answer_quality",
            "answer_grounding", "notes"
        ])

if not os.path.exists(ANSWERS_FILE) or os.path.getsize(ANSWERS_FILE) == 0:
    with open(ANSWERS_FILE, "w", newline="") as f:
        csv.writer(f).writerow([
            "timestamp", "scenario", "query",
            "answer", "sources", "k_requested", "relevant_chunks"
        ])


class MeasurementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/photos" or request.url.path.startswith("/images/"):
            return await call_next(request)

        start = time.time()
        body = await request.body()
        request_bytes = len(body)

        response = await call_next(request)

        end_to_end_ms = (time.time() - start) * 1000
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        response_bytes = len(response_body)

        ocr_ms = getattr(request.state, "ocr_ms", None)
        if ocr_ms is None:
            header_ocr_ms = request.headers.get("X-OCR-Ms")
            if header_ocr_ms is not None:
                try:
                    ocr_ms = float(header_ocr_ms)
                except ValueError:
                    pass

        caption_ms = getattr(request.state, "caption_ms", None)
        if caption_ms is None:
            header_caption_ms = request.headers.get("X-Caption-Ms")
            if header_caption_ms is not None:
                try:
                    caption_ms = float(header_caption_ms)
                except ValueError:
                    pass

        embedding_ms = getattr(request.state, "embedding_ms", None)
        retrieval_ms = getattr(request.state, "retrieval_ms", None)
        llm_ms       = getattr(request.state, "llm_ms",       None)
        scenario     = request.headers.get("X-Scenario", "unset")

        try:
            with open(LOG_FILE, "a", newline="") as f:
                csv.writer(f).writerow([
                    time.strftime("%Y-%m-%dT%H:%M:%S"),
                    scenario,
                    request.url.path,
                    request_bytes,
                    response_bytes,
                    request_bytes + response_bytes,
                    round(end_to_end_ms, 2),
                    round(ocr_ms,       2) if ocr_ms       else "",
                    round(caption_ms,   2) if caption_ms   else "",
                    round(embedding_ms, 2) if embedding_ms else "",
                    round(retrieval_ms, 2) if retrieval_ms else "",
                    round(llm_ms,       2) if llm_ms       else "",
                ])
        except OSError as e:
            print(f"WARNING: Could not write to measurements.csv (file locked?): {e}")

        from starlette.responses import Response
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

app.add_middleware(MeasurementMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Image storage ─────────────────────────────────────────────────────────────
UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png", "image/jpg")

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    try:
        from search import _load_vectorstore
        _load_vectorstore()
        print("Vector store ready.")
    except FileNotFoundError:
        print("WARNING: Vector store not found — run ingest.py first.")
    except Exception as e:
        print(f"WARNING: Could not load vector store: {e}")

    try:
        _load_blip()
        print("BLIP captioning model ready.")
    except Exception as e:
        print(f"WARNING: Could not load BLIP model: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#   WebSocket
# ══════════════════════════════════════════════════════════════════════════════
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except (RuntimeError, OSError) as e:
                print("Error sending to client:", e)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received: {data}")
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except RuntimeError as e:
        print("WebSocket error:", e)
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except RuntimeError:
            pass

@app.get("/")
async def root():
    return {"message": "FastAPI server running — RAG pipeline active"}


# ══════════════════════════════════════════════════════════════════════════════
#   Photo upload & listing
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/upload-photo")
async def upload_photo(file: Annotated[UploadFile, File()]):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    uploaded_at = datetime.utcnow().isoformat() + "Z"
    print(f"Saved {file_path}")

    return {
        "filename": unique_name,
        "url": f"/images/{unique_name}",
        "uploaded_at": uploaded_at,
        "content_type": file.content_type,
    }

@app.get("/photos")
async def list_photos():
    files = [
        {"filename": f, "url": f"/images/{f}"}
        for f in os.listdir(UPLOAD_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    files.sort(key=lambda x: x["filename"])
    return {"photos": files}


# ══════════════════════════════════════════════════════════════════════════════
#   OCR
# ══════════════════════════════════════════════════════════════════════════════
class OCRRequest(BaseModel):
    image_base64: str

class OCRFromStoredRequest(BaseModel):
    filename: str

@app.post("/ocr-from-stored")
async def ocr_from_stored(req: OCRFromStoredRequest):
    try:
        from PIL import Image
        file_path = os.path.join(UPLOAD_DIR, req.filename)
        if not os.path.isfile(file_path):
            return {"text": "", "error": "File not found"}
        image = Image.open(file_path)
        processed = _preprocess_for_ocr(image)
        custom_config = r"--oem 3 --psm 11"
        text = pytesseract.image_to_string(processed, config=custom_config).strip()
        return {"text": text}
    except Exception as e:
        return {"text": "", "error": str(e)}

def _preprocess_for_ocr(image):
    from PIL import ImageEnhance, ImageFilter, ImageOps
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    max_side = 1500
    w, h = image.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)))
    gray = image.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(2.0)
    gray = ImageEnhance.Sharpness(gray).enhance(2.0)
    gray = gray.filter(ImageFilter.SHARPEN)
    return gray

@app.post("/ocr")
async def ocr_image(req: OCRRequest, request: Request):
    """Server-side OCR using pytesseract with image preprocessing."""
    try:
        if not req.image_base64 or len(req.image_base64) < 100:
            return {"text": "", "error": "Empty or invalid base64 image"}

        t0 = time.time()
        from PIL import Image
        import base64
        import io

        image_data = base64.b64decode(req.image_base64)
        image = Image.open(io.BytesIO(image_data))
        processed = _preprocess_for_ocr(image)
        custom_config = r"--oem 3 --psm 11"
        text = pytesseract.image_to_string(processed, config=custom_config).strip()
        request.state.ocr_ms = (time.time() - t0) * 1000
        return {"text": text}
    except Exception as e:
        print(f"OCR error: {e}")
        return {"text": "", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#   BLIP image captioning (Scenario 4 — caption replaces OCR as photo context)
# ══════════════════════════════════════════════════════════════════════════════
_blip_processor = None
_blip_model = None

def _load_blip():
    """Load the BLIP captioning model once per process."""
    global _blip_processor, _blip_model
    if _blip_model is not None:
        return _blip_processor, _blip_model

    from transformers import BlipProcessor, BlipForConditionalGeneration

    _blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    _blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    return _blip_processor, _blip_model

def _generate_caption(image) -> str:
    processor, model = _load_blip()
    inputs = processor(image.convert("RGB"), return_tensors="pt")
    out = model.generate(**inputs, max_new_tokens=40)
    return processor.decode(out[0], skip_special_tokens=True).strip()

class CaptionRequest(BaseModel):
    image_base64: str

class CaptionFromStoredRequest(BaseModel):
    filename: str

@app.post("/caption")
async def caption_image(req: CaptionRequest, request: Request):
    """Server-side image captioning using BLIP."""
    try:
        if not req.image_base64 or len(req.image_base64) < 100:
            return {"caption": "", "error": "Empty or invalid base64 image"}

        t0 = time.time()
        from PIL import Image
        import base64
        import io

        image_data = base64.b64decode(req.image_base64)
        image = Image.open(io.BytesIO(image_data))
        caption = _generate_caption(image)
        request.state.caption_ms = (time.time() - t0) * 1000
        return {"caption": caption}
    except Exception as e:
        print(f"BLIP captioning error: {e}")
        return {"caption": "", "error": str(e)}

@app.post("/caption-from-stored")
async def caption_from_stored(req: CaptionFromStoredRequest, request: Request):
    try:
        from PIL import Image
        file_path = os.path.join(UPLOAD_DIR, req.filename)
        if not os.path.isfile(file_path):
            return {"caption": "", "error": "File not found"}

        t0 = time.time()
        image = Image.open(file_path)
        caption = _generate_caption(image)
        request.state.caption_ms = (time.time() - t0) * 1000
        return {"caption": caption}
    except Exception as e:
        print(f"BLIP captioning error: {e}")
        return {"caption": "", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#   LLM
# ══════════════════════════════════════════════════════════════════════════════
MODELS = [
    "google/gemini-2.5-flash",
    "openai/gpt-4o-mini",
]

CONVERSATIONAL_PATTERNS = {
    "hello", "hi", "hey", "how are you", "good morning", "good afternoon",
    "good evening", "thanks", "thank you", "bye", "goodbye", "ok", "okay",
    "yes", "no", "sure", "sounds good", "great", "cool", "nice"
}

MIN_RELEVANCE_SCORE = 0.3

def is_conversational(query: str) -> bool:
    """True if the query is a short greeting or filler with no research intent."""
    q = query.lower().strip().rstrip("!?.")
    if q in CONVERSATIONAL_PATTERNS:
        return True
    words = q.split()
    if len(words) <= 3 and not any(
        kw in q for kw in ["what", "how", "why", "when", "which", "who",
                            "explain", "describe", "compare", "define", "find"]
    ):
        return True
    return False

def call_openrouter(
    question: str,
    context: str,
    image_base64: Optional[str] = None,
    ocr_text: Optional[str] = None,
    caption_text: Optional[str] = None,
) -> str:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    has_photo = bool(image_base64 or ocr_text or caption_text)
    if caption_text:
        system_content = SYSTEM_PROMPT_CAPTION
    elif has_photo:
        system_content = SYSTEM_PROMPT_PHOTO
    else:
        system_content = SYSTEM_PROMPT_RESEARCH

    parts = []
    if caption_text:
        parts.append(f"Auto-generated caption of the photo (BLIP):\n{caption_text}")
    if ocr_text:
        parts.append(f"Text extracted from the photo (OCR):\n{ocr_text}")
    if context:
        parts.append(f"Context:\n{context}")
    parts.append(f"Question: {question}")
    context_text = "\n\n".join(parts)

    user_content = (
        [{"type": "text", "text": context_text},
         {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}]
        if image_base64 else context_text
    )

    for model in MODELS:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user",   "content": user_content},
                    ],
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Model {model} attempt {attempt + 1} failed: {e}")
                time.sleep(2)
    return "LLM unavailable — all providers failed."

def call_openrouter_conversational(question: str) -> str:
    """Answer without retrieval context for conversational queries."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    for model in MODELS:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": (
                            "You are a helpful research assistant. "
                            "Answer the user conversationally. "
                            "If they ask a research question, let them know "
                            "you can search the knowledge base if they provide more detail."
                        )},
                        {"role": "user", "content": question},
                    ],
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Model {model} attempt {attempt + 1} failed: {e}")
                time.sleep(2)
    return "I'm here to help — could you ask me something about the documents?"


# ══════════════════════════════════════════════════════════════════════════════
#   RAG query
# ══════════════════════════════════════════════════════════════════════════════
class QueryRequest(BaseModel):
    query: str
    ocr_text: Optional[str] = None
    caption_text: Optional[str] = None
    image_base64: Optional[str] = None
    k: int = 10

@app.post("/query")
async def query_knowledge_base(req: QueryRequest, request: Request):
    """
    Full RAG pipeline:
      1. Detect conversational queries and answer without retrieval
      2. Combine question + OCR text into a single search query
      3. Embed with BGE-m3, search Chroma for top-k chunks
      4. Filter results below relevance threshold
      5. Format chunks as XML context
      6. Send context + question to LLM via OpenRouter
      7. Log answer automatically to answers.csv
      8. Return answer, sources, retrieved chunks, and timings
    """
    combined_query = " ".join(filter(None, [req.query, req.ocr_text, req.caption_text]))
    has_attachment = bool(req.ocr_text or req.caption_text or req.image_base64)
    scenario = request.headers.get("X-Scenario", "unset")

    # Skip retrieval for conversational queries
    if is_conversational(combined_query) and not has_attachment:
        t1 = time.time()
        llm_answer = call_openrouter_conversational(question=req.query)
        request.state.llm_ms = (time.time() - t1) * 1000
        return {
            "query":          req.query,
            "ocr_text":       req.ocr_text,
            "caption_text":   req.caption_text,
            "context_status": "conversational",
            "result_count":   0,
            "results":        [],
            "context":        "",
            "sources":        [],
            "answer":         llm_answer,
            "timings":        {"embedding_ms": 0, "retrieval_ms": 0},
        }

    # Research query — full RAG pipeline
    results, timings = search(combined_query, k=req.k)
    request.state.embedding_ms = timings["embedding_ms"]
    request.state.retrieval_ms = timings["retrieval_ms"]

    relevant_results = [r for r in results if r["score"] >= MIN_RELEVANCE_SCORE]
    context = format_context(relevant_results)
    context_status = "found" if relevant_results else "none"
    sources = list({r["source"] for r in relevant_results})

    t1 = time.time()
    if relevant_results or has_attachment:
        llm_answer = call_openrouter(
            question=req.query,
            context=context,
            image_base64=req.image_base64 or None,
            ocr_text=req.ocr_text or None,
            caption_text=req.caption_text or None,
        )
    else:
        llm_answer = call_openrouter_conversational(question=req.query)
    request.state.llm_ms = (time.time() - t1) * 1000

    # ── Auto-log answer to answers.csv ───────────────────────────────────────
    try:
        with open(ANSWERS_FILE, "a", newline="") as f:
            csv.writer(f).writerow([
                time.strftime("%Y-%m-%dT%H:%M:%S"),
                scenario,
                req.query,
                llm_answer,
                "|".join(sources),
                req.k,
                len(relevant_results),
            ])
    except OSError as e:
        print(f"WARNING: Could not write to answers.csv (file locked?): {e}")

    return {
        "query":          req.query,
        "ocr_text":       req.ocr_text,
        "caption_text":   req.caption_text,
        "context_status": context_status,
        "result_count":   len(relevant_results),
        "results":        relevant_results,
        "context":        context,
        "sources":        sources,
        "answer":         llm_answer,
        "timings":        timings,
    }

@app.post("/search")
async def search_alias(req: QueryRequest, request: Request):
    """Alias for /query — keeps the existing frontend working without changes."""
    return await query_knowledge_base(req, request)


# ══════════════════════════════════════════════════════════════════════════════
#   Evaluation logging
# ══════════════════════════════════════════════════════════════════════════════
class EvalRequest(BaseModel):
    scenario: str
    query: str
    answer: str
    sources_returned: list[str]
    sources_expected: list[str]
    answer_quality: int       # 1–4 Likert
    answer_grounding: str     # "Grounded" / "Partial" / "Refusal" / "Hallucination"
    notes: str = ""

@app.post("/eval")
async def log_evaluation(req: EvalRequest):
    returned = set(req.sources_returned)
    expected = set(req.sources_expected)
    recall = len(returned & expected) / len(expected) if expected else None

    try:
        with open(EVAL_FILE, "a", newline="") as f:
            csv.writer(f).writerow([
                time.strftime("%Y-%m-%dT%H:%M:%S"),
                req.scenario,
                req.query,
                "|".join(req.sources_returned),
                "|".join(req.sources_expected),
                round(recall, 3) if recall is not None else "N/A",
                req.answer_quality,
                req.answer_grounding,
                req.notes,
            ])
    except OSError as e:
        print(f"WARNING: Could not write to evaluations.csv (file locked?): {e}")

    return {"status": "logged", "recall_at_k": recall}

# ── Measurements reset ────────────────────────────────────────────────────────
@app.delete("/measurements/reset")
async def reset_measurements():
    """Clear all logs. Call before starting a new scenario run."""
    for path, headers in [
        (LOG_FILE,     ["timestamp","scenario","endpoint","request_bytes","response_bytes",
                        "total_bytes","end_to_end_ms","ocr_ms","caption_ms","embedding_ms","retrieval_ms","llm_ms"]),
        (EVAL_FILE,    ["timestamp","scenario","query","sources_returned","sources_expected",
                        "recall_at_k","answer_quality","answer_grounding","notes"]),
        (ANSWERS_FILE, ["timestamp","scenario","query","answer","sources","k_requested","relevant_chunks"]),
    ]:
        try:
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(headers)
        except OSError as e:
            print(f"WARNING: Could not reset {path}: {e}")
    return {"status": "cleared"}