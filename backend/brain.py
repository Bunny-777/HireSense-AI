from __future__ import annotations


def choose_followup(transcript: str, asked_questions: list[str]) -> str:
    """Offline rule-based question selector fallback when no LLM API key is configured."""
    text = transcript.lower()
    if any(k in text for k in ("outage", "incident", "failure", "rollback", "bug")):
        candidates = [
            "How did you debug this, and what was the first signal you checked?",
            "What root cause did you confirm, and how did you prevent it from happening again?",
            "What trade-off did you make during the fix, and why?",
        ]
    elif any(k in text for k in ("model", "llm", "classifier", "prompt", "rag", "vector")):
        candidates = [
            "How did you plan this, and what tools did you use?",
            "How did you evaluate output quality before deployment?",
            "What did you change after the first test results?",
        ]
    elif any(k in text for k in ("deployed", "deployment", "cloud", "streamlit", "release", "docker", "k8s", "aws")):
        candidates = [
            "How did you plan the deployment, and what stack did you use?",
            "What risks did you expect before release, and how did you handle them?",
            "What was the hardest part during deployment, and how did you solve it?",
        ]
    else:
        candidates = [
            "What was your role in this project, and which key architectural decisions were yours?",
            "How did you test that your implementation worked as expected under load?",
        ]

    asked = {q.lower().rstrip("?.! ") for q in asked_questions}
    for q in candidates:
        if q.lower().rstrip("?.! ") not in asked:
            return q
    return candidates[0]

