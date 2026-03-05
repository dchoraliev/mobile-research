from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# (Optional) CORS for normal HTTP calls – not required for WebSocket itself
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "FastAPI WebSocket server is running"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Accept incoming WebSocket connection
    await websocket.accept()
    print("Client connected")

    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            print(f"Received from client: {data}")

            # Echo back (you can process/transform here)
            response = f"Server echo: {data}"
            await websocket.send_text(response)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print("Unexpected error:", e)
        try:
            await websocket.close()
        except:
            pass
