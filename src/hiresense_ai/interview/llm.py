from __future__ import annotations

import httpx

from hiresense_ai.config import FOLLOWUP_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from hiresense_ai.interview.nlu import NLUSignals


# ---------------------------------------------------------------------------
# Follow-up question generation
# ---------------------------------------------------------------------------

def generate_followup(transcript: str, asked_questions: list[str], signals: NLUSignals) -> str:
    fallback = _fallback(asked_questions, signals)
    if not OPENAI_API_KEY:
        return fallback

    last_q = asked_questions[-1] if asked_questions else ""
    prompt = (
        "You are a senior technical interviewer.\n"
        "Write ONE concise, high-signal follow-up question tied to the latest answer.\n"
        "Do not ask generic questions like 'tell me more'.\n"
        "Do not repeat or paraphrase the candidate's full answer.\n"
        "Do not repeat the previous question.\n"
        "Return only one question in plain English.\n"
        f"Candidate answer: {transcript}\n"
        f"Detected topic hint: {signals.topic}\n"
        f"Detected intent: {signals.intent}\n"
        f"Previous question to avoid repeating: {last_q}"
    )
    return _call_llm(prompt, fallback, max_tokens=150, validate_question=True, last_q=last_q, transcript=transcript)


# ---------------------------------------------------------------------------
# End-of-interview review and rating
# ---------------------------------------------------------------------------

def generate_review(
    intro_transcript: str,
    conversation: list[dict],
    job_description: str,
) -> dict:
    """
    Generate a structured review and rating based on the full interview.

    Returns a dict with keys:
        summary       - brief overall summary of the candidate
        strengths     - bullet list of strengths observed
        improvements  - bullet list of areas to improve
        rating        - int 1-10 score vs. job description
        rating_reason - one sentence explaining the rating
        recommendation - "Strong Yes" | "Yes" | "Maybe" | "No"
    """
    if not OPENAI_API_KEY:
        return _offline_review()

    convo_text = "\n".join(
        f"Q: {turn['question']}\nA: {turn['answer']}" for turn in conversation
    )

    prompt = f"""You are an expert technical hiring manager.

You just finished interviewing a candidate. Below is their introduction and the full conversation.

---
CANDIDATE INTRODUCTION:
{intro_transcript or "(no introduction provided)"}

INTERVIEW CONVERSATION:
{convo_text}

JOB DESCRIPTION:
{job_description or "Software Engineer - general technical role requiring problem-solving, communication, and project delivery skills."}
---

Please provide a structured evaluation in EXACTLY this format (no extra text):

SUMMARY:
<2-3 sentence overall summary of the candidate>

STRENGTHS:
- <strength 1>
- <strength 2>
- <strength 3>

AREAS FOR IMPROVEMENT:
- <area 1>
- <area 2>

RATING: <integer 1-10>
RATING REASON: <one sentence explaining the score>
RECOMMENDATION: <one of: Strong Yes | Yes | Maybe | No>
"""

    try:
        r = httpx.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": FOLLOWUP_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 600,
            },
            timeout=30,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"] or ""
        return _parse_review(raw)
    except Exception:
        return _offline_review()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call_llm(
    prompt: str,
    fallback: str | None,
    max_tokens: int = 150,
    validate_question: bool = False,
    multiline: bool = False,
    last_q: str = "",
    transcript: str = "",
) -> str:
    try:
        r = httpx.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": FOLLOWUP_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": max_tokens,
            },
            timeout=20,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
        if not raw:
            return fallback or ""
        result = raw.strip() if multiline else _clean_text(raw)
        if validate_question:
            if "?" not in result:
                result = result.rstrip(".! ") + "?"
            if last_q and result.lower().rstrip("?.! ") == last_q.lower().rstrip("?.! "):
                return fallback or result
            if transcript and _too_similar_to_answer(result, transcript):
                return fallback or result
        return result
    except Exception:
        return fallback or ""


def _parse_review(raw: str) -> dict:
    """Parse the structured LLM review output into a dict."""
    # Normalize unicode dashes, quotes, etc. that Windows cp1252 can't encode
    raw = (
        raw.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
        .replace("\u2019", "'").replace("\u2018", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u202f", " ").replace("\u00a0", " ")
        .encode("ascii", "ignore").decode("ascii")
    )
    result = {
        "summary": "",
        "strengths": [],
        "improvements": [],
        "rating": 0,
        "rating_reason": "",
        "recommendation": "Maybe",
    }
    if not raw:
        return _offline_review()

    section = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("SUMMARY:"):
            section = "summary"
            tail = line[len("SUMMARY:"):].strip()
            if tail:
                result["summary"] = tail
        elif line.startswith("STRENGTHS:"):
            section = "strengths"
        elif line.startswith("AREAS FOR IMPROVEMENT:"):
            section = "improvements"
        elif line.startswith("RATING:"):
            section = None
            try:
                result["rating"] = int(line.split(":")[1].strip().split()[0])
            except (ValueError, IndexError):
                result["rating"] = 5
        elif line.startswith("RATING REASON:"):
            section = None
            result["rating_reason"] = line[len("RATING REASON:"):].strip()
        elif line.startswith("RECOMMENDATION:"):
            section = None
            result["recommendation"] = line[len("RECOMMENDATION:"):].strip()
        elif section == "summary" and line:
            result["summary"] = (result["summary"] + " " + line).strip()
        elif section == "strengths" and line.startswith("-"):
            result["strengths"].append(line[1:].strip())
        elif section == "improvements" and line.startswith("-"):
            result["improvements"].append(line[1:].strip())

    return result


def _offline_review() -> dict:
    return {
        "summary": "Interview completed. Set OPENAI_API_KEY (Groq) in .env for a detailed AI review.",
        "strengths": ["Completed the interview session"],
        "improvements": ["Add Groq API key to enable AI-powered review"],
        "rating": 0,
        "rating_reason": "No LLM key configured for evaluation.",
        "recommendation": "N/A",
    }


def _fallback(asked: list[str], signals: NLUSignals) -> str:
    intent_templates = {
        "impact": [
            f"For {signals.topic}, what baseline and final metric prove your impact?",
            f"For {signals.topic}, which action you owned caused the biggest measurable change?",
            f"For {signals.topic}, how did you isolate your contribution from team-wide changes?",
        ],
        "incident": [
            f"For {signals.topic}, what root cause did you validate and how?",
            f"For {signals.topic}, what permanent fix prevented recurrence?",
            f"For {signals.topic}, what was your first debugging step and why?",
        ],
        "ml": [
            f"For {signals.topic}, what offline and online metrics did you require before launch?",
            f"For {signals.topic}, what trade-off did you make between quality, latency, and cost?",
            f"For {signals.topic}, what failure mode did you test hardest before shipping?",
        ],
        "delivery": [
            f"For {signals.topic}, what deployment risk did you mitigate first?",
            f"For {signals.topic}, what release strategy did you choose and why?",
            f"For {signals.topic}, what rollback plan did you define before launch?",
        ],
        "validation": [
            f"For {signals.topic}, how did you measure wrong-answer rate before and after fixes?",
            f"For {signals.topic}, what test cases caught the highest-risk failures?",
            f"For {signals.topic}, what acceptance threshold did you require before release?",
        ],
        "general": [
            f"For {signals.topic}, which decision was yours alone and what alternatives did you reject?",
            f"For {signals.topic}, how did you validate that your final approach was correct?",
            f"For {signals.topic}, what trade-off mattered most and why?",
        ],
    }
    options = intent_templates.get(signals.intent, intent_templates["general"])
    if signals.likely_non_english:
        options.append("Could you restate that briefly in English with one concrete example?")

    asked_norm = {q.lower().rstrip("?.! ") for q in asked}
    asked_styles = {_style_key(q) for q in asked}
    for q in options:
        if q.lower().rstrip("?.! ") in asked_norm:
            continue
        if _style_key(q) in asked_styles:
            continue
        return q
    return options[0]


def _clean_text(text: str) -> str:
    cleaned = text.strip().splitlines()[0].strip().strip('"')
    return (
        cleaned.replace("\u202f", " ")
        .replace("\u00a0", " ")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _too_similar_to_answer(question: str, answer: str) -> bool:
    q_words = [w.lower().strip(".,!?") for w in question.split() if len(w.strip(".,!?")) > 3]
    a_words = [w.lower().strip(".,!?") for w in answer.split() if len(w.strip(".,!?")) > 3]
    if not q_words or not a_words:
        return False
    overlap = len(set(q_words) & set(a_words)) / max(1, len(set(q_words)))
    return overlap >= 0.75


def _style_key(q: str) -> str:
    lowered = q.lower()
    if "baseline and final metric" in lowered:
        return "metric_baseline"
    if "root cause" in lowered:
        return "root_cause"
    if "offline and online metrics" in lowered:
        return "ml_eval"
    if "deployment risk" in lowered:
        return "deploy_risk"
    if "test cases" in lowered or "acceptance threshold" in lowered:
        return "validation"
    if "trade-off" in lowered:
        return "tradeoff"
    if "decision was yours" in lowered:
        return "ownership"
    return "generic"
