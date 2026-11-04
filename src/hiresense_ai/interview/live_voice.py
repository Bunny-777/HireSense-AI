from __future__ import annotations

import os
import time

from hiresense_ai.audio.asr import get_asr
from hiresense_ai.audio.recorder import MetricsLogger, MicrophoneRecorder, RecorderConfig
from hiresense_ai.audio.tts import get_speaker
from hiresense_ai.config import OPENAI_API_KEY
from hiresense_ai.interview.brain import choose_followup
from hiresense_ai.interview.llm import generate_followup, generate_review
from hiresense_ai.interview.nlu import analyze_answer


TURNS = int(os.getenv("INTERVIEW_TURNS", "5"))
NO_TTS = os.getenv("NO_TTS", "false").lower() in ("1", "true", "yes")
JOB_DESCRIPTION = os.getenv(
    "JOB_DESCRIPTION",
    "Software Engineer - requires strong problem-solving, system design, communication, and project delivery skills.",
)
TARGET_FOLLOWUP_MS = 300.0
RECORDER_CONFIG = RecorderConfig(
    sample_rate=16000,
    silence_seconds=1.1,
    max_seconds=60.0,
    input_device=None,
    vad_threshold=0.015,
)
EXIT_TERMS = ("stop interview", "exit", "quit", "goodbye")
PROJECT_OPENER = "Thank you for introducing yourself. Could you walk me through a project you are most proud of and what impact it had?"


def main() -> None:
    recorder = MicrophoneRecorder(RECORDER_CONFIG)
    try:
        stt = get_asr()
    except RuntimeError as e:
        print(f"\n[Configuration Notice]: {e}")
        print("You can test without live microphone using the text simulator:")
        print("  python scripts/simulate_interview.py\n")
        return

    tts = get_speaker(no_tts=NO_TTS)
    metrics = MetricsLogger()
    conversation: list[dict] = []   # {question, answer} for the final review
    asked_questions: list[str] = []

    # ------------------------------------------------------------------
    # PHASE 1: Introduction
    # ------------------------------------------------------------------
    say(tts, "Welcome to your HireSense AI mock interview. I am your AI interviewer today. Please go ahead and introduce yourself.")

    intro_transcript = _listen(recorder, stt, tts)
    if intro_transcript is None:
        return
    if _wants_exit(intro_transcript):
        say(tts, "No problem. Feel free to come back when you are ready. Goodbye!")
        return

    print(f"\nCandidate: {intro_transcript}")
    say(tts, PROJECT_OPENER)

    # ------------------------------------------------------------------
    # PHASE 2: Project deep-dive questions
    # ------------------------------------------------------------------
    for turn in range(TURNS):
        print(f"\n--- Turn {turn + 1} of {TURNS} ---")

        transcript = _listen(recorder, stt, tts)
        if transcript is None:
            return
        if _wants_exit(transcript):
            say(tts, "Understood. Ending the interview early. Let me compile your feedback now.")
            break

        print(f"\nCandidate: {transcript}")

        followup_started = time.monotonic()
        if OPENAI_API_KEY:
            signals = analyze_answer(transcript)
            response = generate_followup(transcript, asked_questions=asked_questions, signals=signals)
        else:
            response = choose_followup(transcript, asked_questions=asked_questions)
        followup_ms_raw = (time.monotonic() - followup_started) * 1000

        # Pad to target latency for natural feel
        wait_ms = max(0.0, TARGET_FOLLOWUP_MS - followup_ms_raw)
        if wait_ms > 0:
            time.sleep(wait_ms / 1000.0)
        followup_ms = followup_ms_raw + wait_ms

        conversation.append({"question": asked_questions[-1] if asked_questions else PROJECT_OPENER, "answer": transcript})
        asked_questions.append(response)
        metrics.log_turn(transcript, response, 0.0, 0.0, followup_ms=followup_ms, followup_ms_raw=followup_ms_raw)

        # On the last turn, don't ask another question — wrap up instead
        if turn == TURNS - 1:
            say(tts, "That was a great session. Those are all my questions for today. Let me put together your feedback now, please hold on.")
        else:
            say(tts, response)

    # Capture the final answer if we asked the last follow-up question
    if len(conversation) < TURNS:
        last_transcript = _listen(recorder, stt, tts)
        if last_transcript and not _wants_exit(last_transcript):
            print(f"\nCandidate: {last_transcript}")
            conversation.append({"question": asked_questions[-1] if asked_questions else PROJECT_OPENER, "answer": last_transcript})

    # ------------------------------------------------------------------
    # PHASE 3: Conclusion — generate and present review + rating
    # ------------------------------------------------------------------
    _present_review(tts, intro_transcript, conversation)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _listen(
    recorder: MicrophoneRecorder,
    stt,
    tts,
) -> str | None:
    """Record from mic, transcribe, and return text. Returns None on fatal error."""
    try:
        audio_path, _ = recorder.record_until_silence()
    except RuntimeError:
        say(tts, "I could not capture audio. Please check your microphone and try again.")
        return None
    try:
        transcript = stt.transcribe(str(audio_path)).strip()
    finally:
        audio_path.unlink(missing_ok=True)
    return transcript or ""


def _wants_exit(text: str) -> bool:
    return any(term in text.lower() for term in EXIT_TERMS)


def _present_review(tts, intro_transcript: str, conversation: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("  Generating your personalised interview review...")
    print("=" * 60)

    review = generate_review(intro_transcript, conversation, JOB_DESCRIPTION)

    # Speak a short summary
    spoken_summary = (
        f"Here is your interview feedback. {review['summary']} "
        f"Overall I would rate you {review['rating']} out of 10. "
        f"My recommendation is: {review['recommendation']}."
    )
    say(tts, spoken_summary)

    # Print the full detailed report
    print("\n" + "=" * 60)
    print("  INTERVIEW REVIEW REPORT")
    print("=" * 60)
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


def say(tts, text: str) -> None:
    print(f"\nAI Interviewer: {text}")
    if tts is not None:
        try:
            tts.speak(text)
        except Exception as e:
            print(f"[TTS playback warning: {e}]")


if __name__ == "__main__":
    main()
