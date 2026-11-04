"""
HireSense AI - FastAPI Backend Server
Wraps the interview intelligence engine and exposes REST + SSE endpoints
for the web UI.
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, List, Literal

from dotenv import load_dotenv

# Ensure the HireSense-AI source is in python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# Load environment variables (.env in repo root)
load_dotenv(REPO_ROOT / ".env")

import docx
import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import pypdf

from hiresense_ai.config import FOLLOWUP_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from hiresense_ai.interview.brain import choose_followup
from hiresense_ai.interview.nlu import analyze_answer

app = FastAPI(title="HireSense AI API", version="1.0.0")

# Enable CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: Literal["assistant", "candidate", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stage: Literal["intro", "questions", "projects", "verdict"] = "intro"
    job_description: str = ""
    turns_in_stage: int = 0


class VerdictRequest(BaseModel):
    conversation: List[dict]  # list of {"question": str, "answer": str}
    job_description: str
    intro: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_text_from_file(filename: str, content: bytes) -> str:
    """Extract plain text from PDF, DOCX, or text files."""
    name_lower = filename.lower()
    if name_lower.endswith(".pdf"):
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages_text).strip()
    elif name_lower.endswith(".docx"):
        doc = docx.Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
    else:
        # Fallback to UTF-8 text/markdown
        return content.decode("utf-8", errors="ignore").strip()


def build_system_prompt(stage: str, job_description: str) -> str:
    jd_snippet = job_description[:2000] if job_description else "General Software Engineer role."
    if stage == "intro":
        return (
            "You are a professional, friendly, and rigorous technical interviewer for the following job description:\n\n"
            f"=== JOB DESCRIPTION ===\n{jd_snippet}\n========================\n\n"
            "The candidate is introducing themselves. Acknowledge their introduction briefly in 1 warm sentence, "
            "and immediately transition into asking your first role-specific technical question based on the job description. "
            "Keep your response concise (maximum 3 sentences)."
        )
    elif stage == "questions":
        return (
            "You are a professional technical interviewer for the following job description:\n\n"
            f"=== JOB DESCRIPTION ===\n{jd_snippet}\n========================\n\n"
            "Ask ONE sharp, high-signal technical question to evaluate the candidate against the core skills in the job description. "
            "Do not ask generic questions. Do not repeat previous questions. Return ONLY your question."
        )
    elif stage == "projects":
        return (
            "You are a senior technical interviewer deep-diving into the candidate's real-world projects.\n"
            "Analyze the candidate's technical claim. Ask ONE concise follow-up question testing their technical depth, "
            "trade-offs, debugging, architecture, or measurable impact. "
            "Do not praise excessively or summarize their full answer. Return ONLY your question."
        )
    else:
        return "You are an expert technical interviewer. Ask a concise, high-signal follow-up question."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "has_openai_key": bool(OPENAI_API_KEY),
        "model": FOLLOWUP_MODEL,
        "base_url": OPENAI_BASE_URL,
    }


@app.post("/api/upload-jd")
async def upload_jd(
    file: UploadFile | None = File(None),
    text: str = Form(""),
):
    """Handle JD upload via file (PDF, DOCX, TXT) or pasted text."""
    if file and file.filename:
        file_bytes = await file.read()
        extracted = extract_text_from_file(file.filename, file_bytes)
        if not extracted:
            raise HTTPException(status_code=400, detail="Could not extract text from uploaded file.")
        return {"jd_text": extracted, "filename": file.filename}
    elif text.strip():
        return {"jd_text": text.strip(), "filename": "pasted_text.txt"}
    else:
        raise HTTPException(status_code=400, detail="Please provide either a file or pasted text.")


@app.post("/api/start")
async def start_interview():
    """Initial greeting when the candidate clicks Start Interview."""
    return {
        "message": (
            "Welcome! I am your AI technical interviewer today. "
            "To get started, please introduce yourself and tell me a bit about your technical background and experience."
        ),
        "stage": "intro",
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Non-streaming chat fallback."""
    reply = ""
    next_stage = req.stage

    # Determine stage progression
    # Intro: 1 turn -> then Questions (2 turns) -> then Projects (2 turns) -> Verdict
    if req.stage == "intro":
        next_stage = "questions"
    elif req.stage == "questions":
        if req.turns_in_stage >= 2:
            next_stage = "projects"
    elif req.stage == "projects":
        if req.turns_in_stage >= 2:
            next_stage = "verdict"

    system_prompt = build_system_prompt(req.stage, req.job_description)

    messages = [{"role": "system", "content": system_prompt}]
    for m in req.messages[-6:]:
        messages.append({"role": m.role if m.role != "candidate" else "user", "content": m.content})

    if OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post(
                    f"{OPENAI_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": FOLLOWUP_MODEL,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 200,
                    },
                )
                res.raise_for_status()
                data = res.json()
                reply = data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            reply = f"Thank you for sharing that. Could you describe a challenging technical problem you solved recently?"
    else:
        # Rule-based fallback
        last_answer = req.messages[-1].content if req.messages else ""
        reply = choose_followup(last_answer, [])

    return {
        "reply": reply,
        "stage": next_stage,
        "is_complete": next_stage == "verdict",
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream AI responses token-by-token using Server-Sent Events (SSE)."""
    next_stage = req.stage
    if req.stage == "intro":
        next_stage = "questions"
    elif req.stage == "questions":
        if req.turns_in_stage >= 2:
            next_stage = "projects"
    elif req.stage == "projects":
        if req.turns_in_stage >= 2:
            next_stage = "verdict"

    system_prompt = build_system_prompt(req.stage, req.job_description)
    messages = [{"role": "system", "content": system_prompt}]
    for m in req.messages[-6:]:
        messages.append({"role": m.role if m.role != "candidate" else "user", "content": m.content})

    async def event_generator() -> AsyncGenerator[str, None]:
        full_reply = []
        if OPENAI_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream(
                        "POST",
                        f"{OPENAI_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                        json={
                            "model": FOLLOWUP_MODEL,
                            "messages": messages,
                            "temperature": 0.3,
                            "max_tokens": 200,
                            "stream": True,
                        },
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    delta = chunk["choices"][0]["delta"].get("content", "")
                                    if delta:
                                        full_reply.append(delta)
                                        yield f"data: {json.dumps({'type': 'token', 'text': delta})}\n\n"
                                except Exception:
                                    continue
            except Exception as e:
                fallback_msg = "Could you walk me through a specific architecture or system you built?"
                yield f"data: {json.dumps({'type': 'token', 'text': fallback_msg})}\n\n"
                full_reply.append(fallback_msg)
        else:
            last_answer = req.messages[-1].content if req.messages else ""
            reply = choose_followup(last_answer, [])
            yield f"data: {json.dumps({'type': 'token', 'text': reply})}\n\n"
            full_reply.append(reply)

        # Emit completion metadata
        yield f"data: {json.dumps({'type': 'done', 'stage': next_stage, 'is_complete': next_stage == 'verdict'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/verdict")
async def generate_verdict(req: VerdictRequest):
    """
    Generate final evaluation against the Job Description.
    Returns: verdict, summary, strengths, gaps, rating, and reasoning.
    """
    convo_lines = []
    for item in req.conversation:
        q = item.get("question", "")
        a = item.get("answer", "")
        convo_lines.append(f"Interviewer: {q}\nCandidate: {a}")
    convo_text = "\n\n".join(convo_lines)

    prompt = f"""You are a technical hiring manager evaluating an interview for this job:

=== JOB DESCRIPTION ===
{req.job_description or "Software Engineer - general technical role"}
========================

CANDIDATE INTRODUCTION:
{req.intro or "Provided during chat."}

FULL INTERVIEW TRANSCRIPT:
{convo_text}

Provide your structured final verdict in EXACTLY this format:

VERDICT: <Recommend OR Don't recommend>
RATING: <integer 1 to 10>
SUMMARY: <2-3 sentence clear summary of the candidate's performance>
STRENGTHS:
- <strength 1>
- <strength 2>
- <strength 3>
GAPS:
- <gap or area of improvement 1>
- <gap or area of improvement 2>
REASONING: <1-2 sentences explaining why this verdict was reached>
"""

    if not OPENAI_API_KEY:
        return {
            "verdict": "Recommend",
            "rating": 7,
            "summary": "The candidate answered technical questions and demonstrated foundational problem-solving skills.",
            "strengths": ["Clear communication", "Relevant technical exposure"],
            "gaps": ["Could provide deeper architectural trade-offs"],
            "reasoning": "Demonstrated core competency for the position.",
        }

    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            res = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": FOLLOWUP_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 600,
                },
            )
            res.raise_for_status()
            raw = res.json()["choices"][0]["message"]["content"]
            return parse_verdict(raw)
    except Exception as e:
        return {
            "verdict": "Recommend",
            "rating": 7,
            "summary": "The candidate participated in the interview session and answered questions in their domain.",
            "strengths": ["Practical hands-on experience", "Direct communication"],
            "gaps": ["Add more details on scalability and edge cases"],
            "reasoning": "Solid baseline performance during the interview.",
        }


def parse_verdict(raw: str) -> dict:
    data = {
        "verdict": "Recommend",
        "rating": 7,
        "summary": "",
        "strengths": [],
        "gaps": [],
        "reasoning": "",
    }
    section = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("VERDICT:"):
            val = line[len("VERDICT:"):].strip()
            data["verdict"] = "Don't recommend" if "don't" in val.lower() or "not" in val.lower() else "Recommend"
        elif line.startswith("RATING:"):
            try:
                num = int(line[len("RATING:"):].strip().split()[0].split("/")[0])
                data["rating"] = min(10, max(1, num))
            except Exception:
                data["rating"] = 7
        elif line.startswith("SUMMARY:"):
            section = "summary"
            tail = line[len("SUMMARY:"):].strip()
            if tail:
                data["summary"] = tail
        elif line.startswith("STRENGTHS:"):
            section = "strengths"
        elif line.startswith("GAPS:"):
            section = "gaps"
        elif line.startswith("REASONING:"):
            section = None
            data["reasoning"] = line[len("REASONING:"):].strip()
        elif section == "summary" and line:
            data["summary"] = (data["summary"] + " " + line).strip()
        elif section == "strengths" and line.startswith("-"):
            data["strengths"].append(line[1:].strip())
        elif section == "gaps" and line.startswith("-"):
            data["gaps"].append(line[1:].strip())

    if not data["summary"]:
        data["summary"] = "Candidate completed the technical interview."
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
