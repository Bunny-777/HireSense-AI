from __future__ import annotations

import httpx

from hiresense_ai.config import FOLLOWUP_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from hiresense_ai.interview.nlu import NLUSignals


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
    payload = {
        "model": FOLLOWUP_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 150,
    }
    try:
        r = httpx.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        raw_content = r.json()["choices"][0]["message"]["content"]
        if not raw_content:
            return fallback
        q = _clean_question(raw_content)
        if "?" not in q:
            q = q.rstrip(".! ") + "?"
        if q.lower().rstrip("?.! ") == last_q.lower().rstrip("?.! "):
            return fallback
        if _too_similar_to_answer(q, transcript):
            return fallback
        return q
    except Exception:
        return fallback


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


def _clean_question(text: str) -> str:
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
