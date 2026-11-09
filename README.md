# HireSense AI

An AI-powered technical interview preparation and candidate evaluation web application.

HireSense AI allows candidates and hiring teams to:
- Upload job descriptions (PDF, DOCX, or text)
- Conduct interactive, multi-stage technical interviews (Introduction, Technical Questions, Deep-Dive Projects)
- Stream interview questions and follow-ups with real-time SSE (Server-Sent Events)
- Receive structured evaluation verdicts (Rating, Summary, Strengths, Improvement Areas, Recommendation)

---

## Architecture & Project Structure

The project is structured into two clean directories:

```text
HireSense-AI/
├── backend/                  # FastAPI backend server
│   ├── brain.py              # Follow-up interview question logic & fallbacks
│   ├── config.py             # App environment & LLM configuration
│   ├── main.py               # FastAPI API endpoints & SSE streaming
│   ├── requirements.txt      # Python backend dependencies
│   └── .env.example          # Backend environment variables template
├── frontend/                 # React + TypeScript + Vite web app
│   ├── src/
│   │   ├── components/       # StartScreen, InterviewScreen, ResultScreen
│   │   ├── api.ts            # REST & SSE streaming API client
│   │   ├── App.tsx           # Main application state machine
│   │   ├── types.ts          # TypeScript models & types
│   │   └── main.tsx          # Application entrypoint
│   ├── package.json          # Node dependencies and build scripts
│   └── vite.config.ts        # Vite configuration & backend proxy
├── run_app.bat               # One-click launcher for both backend & frontend
├── run_backend.bat           # Launcher for FastAPI backend
├── run_frontend.bat          # Launcher for React frontend
└── README.md
```

---

## Getting Started

### 1. Environment Configuration

Copy the example configuration to `.env`:

```bash
cp backend/.env.example .env
```

Configure your LLM provider in `.env` (Groq is recommended for ultra-low latency, or OpenAI):

```env
# For Groq:
OPENAI_API_KEY=gsk_your_groq_api_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
FOLLOWUP_MODEL=llama-3.3-70b-versatile

# Or for OpenAI:
# OPENAI_API_KEY=sk-your_openai_api_key_here
# OPENAI_BASE_URL=https://api.openai.com/v1
# FOLLOWUP_MODEL=gpt-4o-mini
```

*(Note: HireSense AI also includes an offline rule-based fallback mode if no API key is provided).*

---

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Backend API will be live at `http://127.0.0.1:8000`.

---

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend UI will be live at `http://localhost:5173`.

---

### Quick Launch (Windows)

Double click `run_app.bat` to launch both backend and frontend servers simultaneously in dedicated windows.
