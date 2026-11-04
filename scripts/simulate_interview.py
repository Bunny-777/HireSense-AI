"""
Text-based offline interview simulator for HireSense AI.
Allows testing the interview logic, NLU, and question-selection flow
without requiring OpenAI or ElevenLabs API keys or a microphone.
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()
from hiresense_ai.interview.brain import choose_followup
from hiresense_ai.interview.nlu import analyze_answer
from hiresense_ai.interview.llm import generate_followup
from hiresense_ai.audio.recorder import MetricsLogger

DEFAULT_QUESTIONS = (
    "Tell me about a project you are proud of and what impact it had.",
    "Describe a hard technical problem you solved recently.",
    "Tell me about a time you handled an outage or production incident.",
)
EXIT_TERMS = ("stop interview", "exit", "quit", "goodbye")
TURNS = int(os.getenv("INTERVIEW_TURNS", "5"))


def main():
    print("=" * 60)
    print(" HireSense AI - Offline Interactive Simulator")
    print(" (No OpenAI or ElevenLabs API keys required)")
    print("=" * 60)

    metrics = MetricsLogger("metrics.jsonl")
    asked_questions = []

    current_question = DEFAULT_QUESTIONS[0]
    print(f"\nAI Interviewer: Welcome. {current_question}")

    for turn in range(TURNS):
        print(f"\n--- Turn {turn + 1}/{TURNS} ---")
        try:
            transcript = input("Candidate (type your answer or 'exit' to quit): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting simulator.")
            break

        if not transcript:
            print("AI Interviewer: I could not catch that. Please type your answer.")
            continue

        if any(term in transcript.lower() for term in EXIT_TERMS):
            print("\nAI Interviewer: Thanks. Ending the interview now.")
            break

        started_at = time.monotonic()

        # 1. Rule-based follow-up selection (default mode in live_voice.py)
        brain_response = choose_followup(transcript, asked_questions=asked_questions)

        # 2. NLU signals & fallback template follow-up (used when OpenAI key is absent)
        signals = analyze_answer(transcript)
        llm_response = generate_followup(transcript, asked_questions=asked_questions, signals=signals)

        elapsed_ms = (time.monotonic() - started_at) * 1000

        print(f"\n[NLU Analysis] Detected Topic: '{signals.topic}' | Intent: '{signals.intent}'")
        print(f"AI Interviewer (Rule-based):  {brain_response}")
        print(f"AI Interviewer (NLU-template): {llm_response}")

        selected_response = brain_response
        asked_questions.append(selected_response)

        # Log simulated turn metrics
        metrics.log_turn(
            transcript=transcript,
            response=selected_response,
            recording_seconds=5.0,
            transcription_ms=0.0,
            followup_ms=elapsed_ms,
            followup_ms_raw=elapsed_ms,
        )

    print("\n" + "=" * 60)
    print("Interview finished! Turn metrics saved to metrics.jsonl")
    print("You can view summary stats by running: node scripts/metrics-summary.mjs")
    print("=" * 60)


if __name__ == "__main__":
    main()

