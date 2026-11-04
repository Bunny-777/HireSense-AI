from __future__ import annotations

import os
import time

from hiresense_ai.audio.asr import get_asr
from hiresense_ai.audio.recorder import MetricsLogger, MicrophoneRecorder, RecorderConfig
from hiresense_ai.audio.tts import get_speaker
from hiresense_ai.config import OPENAI_API_KEY
from hiresense_ai.interview.brain import choose_followup
from hiresense_ai.interview.llm import generate_followup
from hiresense_ai.interview.nlu import analyze_answer


DEFAULT_QUESTIONS = (
    "Tell me about a project you are proud of and what impact it had.",
    "Describe a hard technical problem you solved recently.",
    "Tell me about a time you handled an outage or production incident.",
)
EXIT_TERMS = ("stop interview", "exit", "quit", "goodbye")

QUESTION = DEFAULT_QUESTIONS[0]
TURNS = 5
NO_TTS = os.getenv("NO_TTS", "false").lower() in ("1", "true", "yes")
TARGET_FOLLOWUP_MS = 300.0
RECORDER_CONFIG = RecorderConfig(
    sample_rate=16000,
    silence_seconds=1.1,
    max_seconds=45.0,
    input_device=None,
    vad_threshold=0.015,
)


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
    asked_questions: list[str] = []

    say(tts, f"Welcome. {QUESTION}")
    for turn in range(TURNS):
        print(f"\nTurn {turn + 1}/{TURNS}")
        try:
            audio_path, duration_s = recorder.record_until_silence()
        except RuntimeError:
            say(tts, "I could not capture audio. Let us stop here.")
            return

        try:
            started_at = time.monotonic()
            transcript = stt.transcribe(str(audio_path)).strip()
            transcription_ms = (time.monotonic() - started_at) * 1000
        finally:
            audio_path.unlink(missing_ok=True)

        if not transcript:
            say(tts, "I could not transcribe that clearly. Please try again.")
            continue
        if any(term in transcript.lower() for term in EXIT_TERMS):
            say(tts, "Thanks. Ending the interview now.")
            return

        print(f"\nCandidate: {transcript}")
        followup_started = time.monotonic()

        # If Groq/OpenAI key is available, use LLM follow-up generation; otherwise fall back to rule-based brain
        if OPENAI_API_KEY:
            signals = analyze_answer(transcript)
            response = generate_followup(transcript, asked_questions=asked_questions, signals=signals)
        else:
            response = choose_followup(transcript, asked_questions=asked_questions)

        followup_ms_raw = (time.monotonic() - followup_started) * 1000
        wait_ms = max(0.0, TARGET_FOLLOWUP_MS - followup_ms_raw)
        if wait_ms > 0:
            time.sleep(wait_ms / 1000.0)
        followup_ms = followup_ms_raw + wait_ms
        asked_questions.append(response)
        metrics.log_turn(
            transcript,
            response,
            duration_s,
            transcription_ms,
            followup_ms=followup_ms,
            followup_ms_raw=followup_ms_raw,
        )
        say(tts, response)

    say(tts, "That completes the demo interview. Thank you.")


def say(tts, text: str) -> None:
    print(f"\nAI Interviewer: {text}")
    if tts is not None:
        try:
            tts.speak(text)
        except Exception as e:
            print(f"[TTS playback warning: {e}]")


if __name__ == "__main__":
    main()
