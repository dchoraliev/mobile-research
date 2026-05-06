from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Annotated
import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import time
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\choralievd\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

load_dotenv()

from search import search, format_context

app = FastAPI()

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


# ── Startup: pre-load the vector store ───────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """
    Pre-load the Chroma vector store and Gemini embeddings when the server
    starts. This avoids a cold-start delay on the first query.
    """
    try:
        from search import _load_vectorstore
        _load_vectorstore()
        print("Vector store ready.")
    except FileNotFoundError:
        print("WARNING: Vector store not found — run ingest.py first.")
    except Exception as e:
        print(f"WARNING: Could not load vector store: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#   WebSocket chat
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
#   OCR endpoint
# ══════════════════════════════════════════════════════════════════════════════

class OCRRequest(BaseModel):
    image_base64: str


class OCRFromStoredRequest(BaseModel):
    filename: str


@app.post("/ocr-from-stored")
async def ocr_from_stored(req: OCRFromStoredRequest):
    """Run OCR on an already-uploaded image by filename."""
    try:
        from PIL import Image
        file_path = os.path.join(UPLOAD_DIR, req.filename)
        if not os.path.isfile(file_path):
            return {"text": "", "error": "File not found"}
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image).strip()
        return {"text": text}
    except Exception as e:
        return {"text": "", "error": str(e)}


def _preprocess_for_ocr(image):
    """
    Preprocess a PIL image to improve pytesseract accuracy on phone photos.
    Phone photos are often high-res colour images; tesseract works best on
    high-contrast grayscale at a moderate DPI.
    """
    from PIL import ImageEnhance, ImageFilter

    # Ensure RGB before converting (handles EXIF-rotated JPEGs etc.)
    image = image.convert("RGB")

    # Scale down very large images — tesseract slows badly above ~3 MP
    # and doesn't gain accuracy. Target ~1500px on the long edge.
    max_side = 1500
    w, h = image.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)))

    # Grayscale + contrast boost
    gray = image.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(2.0)
    gray = ImageEnhance.Sharpness(gray).enhance(2.0)
    gray = gray.filter(ImageFilter.SHARPEN)

    return gray


@app.post("/ocr")
async def ocr_image(req: OCRRequest):
    """Server-side OCR using pytesseract with image preprocessing."""
    try:
        from PIL import Image
        import base64
        import io

        image_data = base64.b64decode(req.image_base64)
        image = Image.open(io.BytesIO(image_data))
        processed = _preprocess_for_ocr(image)

        # --oem 3: LSTM + legacy engine  --psm 11: sparse text (finds text anywhere)
        custom_config = r"--oem 3 --psm 11"
        text = pytesseract.image_to_string(processed, config=custom_config).strip()
        return {"text": text}
    except Exception as e:
        return {"text": "", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#   RAG — semantic search + (LLM placeholder)
# ══════════════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    query: str
    ocr_text: Optional[str] = None
    image_base64: Optional[str] = None
    k: int = 5   # number of chunks to retrieve

# Vision-capable models first — fall back to text-only if image causes an error
MODELS = [
    "google/gemini-2.0-flash-lite-001",
    "openai/gpt-4o-mini",
]

def call_openrouter(question: str, context: str, image_base64: Optional[str] = None) -> str:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    system_prompt = (
        "You are a product research assistant. "
        "Answer the user's question using ONLY the knowledge-base context documents provided below. "
        "Use the image solely to identify the product or read values not captured by OCR — "
        "never use the image as a substitute for knowledge-base information. "
        "Do not use general knowledge to supplement or replace the context. "
        "If the context does not contain a clear answer, say exactly: "
        "'The knowledge base does not have information on this.' "
        "Be concise and direct."
    )
    context_text = f"Context:\n{context}\n\nQuestion: {question}"

    # Build multimodal user message when an image is available
    if image_base64:
        user_content = [
            {"type": "text", "text": context_text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
        ]
    else:
        user_content = context_text

    for model in MODELS:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Model {model} attempt {attempt + 1} failed: {e}")
                time.sleep(2)
    return "LLM unavailable — all providers failed."

@app.post("/query")
async def query_knowledge_base(req: QueryRequest):
    """
    Full RAG query endpoint.

    Pipeline:
      1. Combine user question + OCR text into a single search query
      2. Embed the query with Gemini embedding-001
      3. Search Chroma for the k most semantically similar chunks
      4. Format chunks as XML context
      5. Send context + question to LLM (OpenRouter) — next phase
      6. Return retrieved chunks and formatted context

    """
    # Step 1 — combine query and OCR text
    combined_query = " ".join(filter(None, [req.query, req.ocr_text]))

    # Step 2 + 3 — semantic search
    results = search(combined_query, k=req.k)

    # Step 4 — format context for LLM
    context = format_context(results)

    llm_answer = call_openrouter(
        question=req.query,
        context=context,
        image_base64=req.image_base64 or None,
    )

    context_status = "found" if results else "none"

    return {
        "query":          req.query,
        "ocr_text":       req.ocr_text,
        "context_status": context_status,
        "result_count":   len(results),
        "results":        results,
        "context":        context,
        "sources":        list({r["source"] for r in results}),
        "answer":       llm_answer,
    }


# ── Keep /search as an alias so the frontend doesn't need changes yet ─────────
@app.post("/search")
async def search_alias(req: QueryRequest):
    """Alias for /query — keeps the existing frontend working without changes."""
    return await query_knowledge_base(req)