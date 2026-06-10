from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NLUSignals:
    topic: str
    intent: str
    likely_non_english: bool


def analyze_answer(text: str) -> NLUSignals:
    lower = text.lower()
    intent = "general"
    if any(k in lower for k in ("outage", "incident", "failure", "rollback", "bug", "downtime")):
        intent = "incident"
    elif any(k in lower for k in ("model", "llm", "classifier", "prompt", "bias", "hallucination")):
        intent = "ml"
    elif any(k in lower for k in ("improved", "reduced", "increased", "percent", "%", "latency", "cost", "revenue", "accuracy", "faster")):
        intent = "impact"
    elif any(k in lower for k in ("deployed", "deployment", "released", "launched", "streamlit", "cloud")):
        intent = "delivery"
    elif any(k in lower for k in ("tested", "testing", "validation", "eval", "qa", "wrong answers")):
        intent = "validation"

    topic = _extract_topic(lower)
    likely_non_english = any(ord(ch) > 127 and ch.isalpha() for ch in text)
    return NLUSignals(topic=topic, intent=intent, likely_non_english=likely_non_english)


def _extract_topic(lower: str) -> str:
    patterns = [
        r"\b(ai chatbot|chatbot|streamlit app|streamlit chatbot|rag pipeline|vector database|operating system)\b",
        r"\b(e-?commerce website|interview system|voice agent|automation workflow)\b",
    ]
    for p in patterns:
        m = re.search(p, lower)
        if m:
            return m.group(1)
    words = [w.strip(".,!?") for w in lower.split()]
    content = [w for w in words if len(w) > 3]
    return " ".join(content[:4]) if content else "the project"
