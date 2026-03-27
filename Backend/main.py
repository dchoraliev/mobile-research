from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Annotated
import os
import uuid
import io
import json
from datetime import datetime

from search import search, format_context

app = FastAPI()

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Image storage ──
UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png", "image/jpg")


# ══════════════════════════════════════════════
#   WebSocket chat
# ══════════════════════════════════════════════

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
    return {"message": "FastAPI WebSocket chat server is running"}


# ══════════════════════════════════════════════
#   Photo upload & listing
# ══════════════════════════════════════════════

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


# ══════════════════════════════════════════════
#   RAG — knowledge base search
# ══════════════════════════════════════════════

class SearchRequest(BaseModel):
    query: str
    ocr_text: Optional[str] = None
    max_results: int = 5


@app.post("/search")
async def search_knowledge_base(req: SearchRequest):
    """
    Search the local SQLite FTS5 knowledge base.
    Combines user query and OCR text for better keyword coverage.
    Returns matching chunks and a formatted context string.
    LLM integration is added in the next phase.
    """
    combined = " ".join(filter(None, [req.query, req.ocr_text]))
    results = search(combined, max_results=req.max_results)
    context = format_context(results)

    context_status = (
        "none" if not results
        else "found"
    )

    return {
        "query": req.query,
        "ocr_text": req.ocr_text,
        "context_status": context_status,
        "results": results,
        "context": context,
        "sources": list({r["source"] for r in results}),
        "result_count": len(results),
    }