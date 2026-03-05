from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Annotated, List
import io
import json
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from dotenv import load_dotenv
import os
from fastapi.middleware.trustedhost import TrustedHostMiddleware

load_dotenv()

app = FastAPI()

# ======== CORS ========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_ngrok_header(request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# ======== MONGODB ========
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["researchdb"]
messages_col = db["messages"]
fs_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="photos")

# ======== ALLOWED IMAGE TYPES (constant instead of duplicating literal) ========
ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/jpg", "image/png")
DEFAULT_CONTENT_TYPE = "image/jpeg"

# ======== WEBSOCKET ========

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        # No list() wrapper needed — iterating a copy isn't required here
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:  # removed unnecessary list() wrap
            try:
                await connection.send_text(message)
            except (RuntimeError, OSError) as e:
                print("Error sending to a client:", e)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from client: {data}")

            try:
                msg = json.loads(data)
                doc = {
                    "type": msg.get("type"),
                    "author": msg.get("author"),
                    "text": msg.get("text"),
                    "url": msg.get("url"),
                    "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
                }
                await messages_col.insert_one(doc)
            except ValueError as e:
                print("Error saving message to MongoDB:", e)

            await manager.broadcast(data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except RuntimeError as e:  # specific exception class
        print("Unexpected error in websocket:", e)
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except RuntimeError:
            pass


@app.get("/")
async def root():
    return {"message": "FastAPI WebSocket chat server is running"}


@app.get("/history")
async def get_history(limit: int = 50):
    """Return the last N messages for a new device joining the chat."""
    cursor = messages_col.find({}, {"_id": 0}).sort("timestamp", 1).limit(limit)
    history = await cursor.to_list(length=limit)
    return {"messages": history}


# ======== IMAGE UPLOAD & LISTING ========

@app.post(
    "/upload-photo",
    responses={400: {"description": "Invalid image type"}},  # document 400
)
async def upload_photo(
    file: Annotated[UploadFile, File()],  # Annotated type hint for FastAPI DI
):
    print(f"/upload-photo called with filename={file.filename}, type={file.content_type}")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    uploaded_at = datetime.now(timezone.utc).isoformat()

    contents = await file.read()

    await fs_bucket.upload_from_stream(
        unique_name,
        io.BytesIO(contents),
        metadata={
            "content_type": file.content_type,
            "uploaded_at": uploaded_at,
        }
    )

    url_path = f"/images/{unique_name}"
    print(f"Uploaded {unique_name} to GridFS")

    return {
        "filename": unique_name,
        "url": url_path,
        "uploaded_at": uploaded_at,
        "content_type": file.content_type,
    }


@app.get(
    "/images/{filename}",
    responses={404: {"description": "Image not found"}},  # document 404
)
async def serve_image(filename: str):
    """Stream an image from GridFS back to the client."""
    try:
        stream = await fs_bucket.open_download_stream_by_name(filename)
        content_type = stream.metadata.get("content_type", DEFAULT_CONTENT_TYPE) if stream.metadata else DEFAULT_CONTENT_TYPE
        contents = await stream.read()
        return StreamingResponse(io.BytesIO(contents), media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Image not found") from e


@app.get("/photos")
async def list_photos():
    """List all photos stored in GridFS."""
    photos = []
    async for grid_out in fs_bucket.find():
        photos.append({
            "filename": grid_out.filename,
            "url": f"/images/{grid_out.filename}",
            "uploaded_at": grid_out.metadata.get("uploaded_at") if grid_out.metadata else None,
        })
    photos.sort(key=lambda x: x["uploaded_at"] or "")
    return {"photos": photos}