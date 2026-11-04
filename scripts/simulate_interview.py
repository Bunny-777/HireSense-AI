"""
Text-based offline interview simulator for HireSense AI.
Runs the full structured interview flow (Intro → Questions → Review + Rating)
using typed input instead of a microphone.
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

from hiresense_ai.interview.brain import choose_followup
from hiresense_ai.interview.nlu import analyze_answer
from hiresense_ai.interview.llm import generate_followup, generate_review
from hiresense_ai.audio.recorder import MetricsLogger
from hiresense_ai.config import OPENAI_API_KEY

TURNS = int(os.getenv("INTERVIEW_TURNS", "5"))
EXIT_TERMS = ("stop interview", "exit", "quit", "goodbye")
JOB_DESCRIPTION = os.getenv(
    "JOB_DESCRIPTION",
    "Software Engineer - requires strong problem-solving, system design, communication, and project delivery skills.",
)
PROJECT_OPENER = "Thank you for introducing yourself. Could you walk me through a project you are most proud of and what impact it had?"


def say(text: str) -> None:
    print(f"\nAI Interviewer: {text}")


def listen(prompt: str = "You: ") -> str:
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        return "exit"


def wants_exit(text: str) -> bool:
    return any(term in text.lower() for term in EXIT_TERMS)


def main():
    print("=" * 60)
    print("  HireSense AI — Text Simulator")
    print(f"  Mode: {'LLM (Groq)' if OPENAI_API_KEY else 'Rule-based (offline)'}")
    print(f"  Interview rounds: {TURNS}")
    print("  Type 'exit' at any time to end the interview early")
    print("=" * 60)

    metrics = MetricsLogger("metrics.jsonl")
    conversation: list[dict] = []
    asked_questions: list[str] = []

    # ------------------------------------------------------------------
    # PHASE 1: Introduction
    # ------------------------------------------------------------------
    say("Welcome to your HireSense AI mock interview. I am your AI interviewer today. Please go ahead and introduce yourself.")
    intro = listen("You (intro): ")

    if wants_exit(intro):
        say("No problem. Feel free to come back when you are ready. Goodbye!")
        return

    say(PROJECT_OPENER)

    # ------------------------------------------------------------------
    # PHASE 2: Project deep-dive
    # ------------------------------------------------------------------
    for turn in range(TURNS):
        print(f"\n--- Turn {turn + 1} of {TURNS} ---")
        transcript = listen("You: ")

        if not transcript:
            say("I didn't catch that — please type your answer.")
            continue

        if wants_exit(transcript):
            say("Understood. Ending the interview early. Compiling your feedback now...")
            break

        started_at = time.monotonic()
        if OPENAI_API_KEY:
            signals = analyze_answer(transcript)
            response = generate_followup(transcript, asked_questions=asked_questions, signals=signals)
            print(f"  [NLU] Topic: '{signals.topic}' | Intent: '{signals.intent}'")
        else:
            signals = analyze_answer(transcript)
            response = choose_followup(transcript, asked_questions=asked_questions)
            print(f"  [NLU] Topic: '{signals.topic}' | Intent: '{signals.intent}' (rule-based mode)")

        elapsed_ms = (time.monotonic() - started_at) * 1000
        conversation.append({
            "question": asked_questions[-1] if asked_questions else PROJECT_OPENER,
            "answer": transcript,
        })
        asked_questions.append(response)

        metrics.log_turn(
            transcript=transcript,
            response=response,
            recording_seconds=5.0,
            transcription_ms=0.0,
            followup_ms=elapsed_ms,
            followup_ms_raw=elapsed_ms,
        )

        if turn == TURNS - 1:
            say("That was a great session. Those are all my questions for today. Let me put together your feedback now.")
        else:
            say(response)

    # Capture final answer after last follow-up question
    if asked_questions and len(conversation) < TURNS:
        final = listen("You (final answer): ")
        if final and not wants_exit(final):
            conversation.append({"question": asked_questions[-1], "answer": final})

    # ------------------------------------------------------------------
    # PHASE 3: Review + Rating
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Generating your personalised interview review...")
    print("=" * 60)

    review = generate_review(intro, conversation, JOB_DESCRIPTION)

    print(f"\n SUMMARY\n  {review['summary']}")

    print("\n STRENGTHS")
    for s in review["strengths"]:
        print(f"  + {s}")

    print("\n AREAS FOR IMPROVEMENT")
    for i in review["improvements"]:
        print(f"  ~ {i}")

    print(f"\n RATING          : {review['rating']} / 10")
    print(f" RATING REASON   : {review['rating_reason']}")
    print(f" RECOMMENDATION  : {review['recommendation']}")
    print("\n" + "=" * 60)
    print("  Metrics saved to metrics.jsonl")
    print("  Run  node scripts/metrics-summary.mjs  to view latency stats")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
