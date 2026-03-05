# Research Chat App

A React Native chat application with photo sharing, backed by FastAPI and MongoDB Atlas.

---

## Project Structure

```
Research/
├── Backend/
│   ├── venv/
│   ├── main.py        # Production server (WebSocket + photo upload + MongoDB)
│   ├── echo.py        # Simple echo server for local testing
│   ├── .env           # MongoDB credentials (never commit this)
│   └── requirements.txt
└── Frontend/
    ├── App.js          # Production app
    ├── echo.js         # Minimal test app (pairs with echo.py)
    ├── config.js       # Backend URL config (local vs Render)
    └── styles/
        ├── app.styles.js
        └── echo.styles.js
```

---

## 1. Backend Setup

### 1.1 Create and activate the virtual environment

```bash
cd Research/Backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 1.2 Install dependencies

```bash
pip install -r requirements.txt
```

### 1.3 Create the `.env` file

Create a file called `.env` in `Backend/` with your MongoDB connection string:

```
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
```

> Never commit `.env` to Git. It is already listed in `.gitignore`.
> For production (Render), add `MONGO_URI` as an environment variable in the Render dashboard instead.

---

## 2. Running the Backend

### Option A — Production server (with MongoDB)

```bash
uvicorn main:app --reload --port 8089
```

### Option B — Echo server (no database, for testing WebSocket only)

```bash
uvicorn echo:app --reload --port 8089
```

> Do not run both at the same time — they use the same port.

---

## 3. Exposing the Backend to Your Phone (ngrok)

Since the app runs on a physical device, you need to expose your local server. Install ngrok from [ngrok.com/download](https://ngrok.com/download), then:

### 3.1 Link your ngrok account (one-time setup)

```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

Get your token from [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).

### 3.2 Start the tunnel (in a separate terminal)

```bash
ngrok http 8089
```

You will see a forwarding URL like:
```
https://your-subdomain.ngrok-free.app -> http://localhost:8089
```

Copy the subdomain (e.g. `your-subdomain.ngrok-free.app`) for the next step.

---

## 4. Frontend Setup

### 4.1 Install dependencies

```bash
cd Research/Frontend
npm install
```

### 4.2 Configure `config.js`

Open `Frontend/config.js` and choose your setup:

**Local development via ngrok:**
```js
const NGROK = "your-subdomain.ngrok-free.app"; // paste your ngrok subdomain
const LOCAL_HTTP = `https://${NGROK}`;
const LOCAL_WS   = `wss://${NGROK}/ws`;
const USE_LOCAL  = true;
```

**Production (Render):**
```js
const USE_LOCAL = false;
```

> `PROD_HTTP` and `PROD_WS` already point to the Render deployment and do not need to be changed.

---

## 5. Running the Frontend

```bash
npx expo start --tunnel
```

Scan the QR code with the **Expo Go** app on your phone.

---

## 6. Full Local Development Checklist

Run each of these in a separate terminal:

| Terminal | Command |
|----------|---------|
| 1 | `cd Backend && venv\Scripts\activate && uvicorn main:app --reload --port 8089` |
| 2 | `ngrok http 8089` |
| 3 | `cd Frontend && npx expo start --tunnel` |

Then update `config.js` with the ngrok URL from Terminal 2 and scan the QR from Terminal 3.

---

## 7. MongoDB

The app uses **MongoDB Atlas** (`researchdb`) with the following collections:

| Collection | Contents |
|------------|----------|
| `messages` | All chat messages (text and photo_select events) |
| `photos.files` | Photo metadata (GridFS) |
| `photos.chunks` | Photo binary data (GridFS) |

Collections are created automatically on first use — no manual setup needed in Atlas.

---

## 8. Deploying to Render

1. Push your `Backend/` code to a GitHub repository
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set the build command to: `pip install -r requirements.txt`
4. Set the start command to: `uvicorn main:app --host 0.0.0.0 --port 8089`
5. Add `MONGO_URI` as an environment variable in the Render dashboard
6. Set `USE_LOCAL = false` in `config.js` to point the app at Render
