from __future__ import annotations

import time

from hiresense_ai.audio.asr import ElevenLabsASR
from hiresense_ai.audio.recorder import MetricsLogger, MicrophoneRecorder, RecorderConfig
from hiresense_ai.audio.tts import ElevenLabsSpeaker
from hiresense_ai.interview.brain import choose_followup


DEFAULT_QUESTIONS = (
    "Tell me about a project you are proud of and what impact it had.",
    "Describe a hard technical problem you solved recently.",
    "Tell me about a time you handled an outage or production incident.",
)
EXIT_TERMS = ("stop interview", "exit", "quit", "goodbye")

QUESTION = DEFAULT_QUESTIONS[0]
TURNS = 5
NO_TTS = False
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
    stt = ElevenLabsASR()
    tts = None if NO_TTS else ElevenLabsSpeaker()
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


def say(tts: ElevenLabsSpeaker | None, text: str) -> None:
    print(f"\nAI Interviewer: {text}")
    if tts is not None:
        tts.speak(text)


if __name__ == "__main__":
    main()
