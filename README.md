# HireSense AI

Voice-based AI interview agent for running short mock technical interviews with:

- microphone capture and simple VAD
- ElevenLabs speech-to-text
- rule-based or LLM-assisted follow-up generation
- optional ElevenLabs text-to-speech playback
- per-turn latency and transcript logging

## Project Structure

```text
HireSense_AI/
├── scripts/
│   └── metrics-summary.mjs
├── src/
│   └── hiresense_ai/
│       ├── audio/
│       │   ├── asr.py
│       │   ├── recorder.py
│       │   └── tts.py
│       ├── interview/
│       │   ├── brain.py
│       │   ├── live_voice.py
│       │   ├── llm.py
│       │   ├── nlu.py
│       │   └── vad.py
│       └── config.py
├── pyproject.toml
├── package.json
└── README.md
```

## Requirements

- Python 3.11+
- Node.js 18+ for the metrics summary utility
- working microphone/audio input
- ElevenLabs API key
- OpenAI API key only if you want LLM-generated follow-up questions

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
python3 -m pip install -e .
```

3. Add a `.env` file in the project root:

```env
ELEVENLABS_API_KEY=your_elevenlabs_key
OPENAI_API_KEY=your_openai_key

# Optional overrides
FOLLOWUP_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
ELEVENLABS_STT_LANGUAGE=en
ELEVENLABS_STT_MODEL=scribe_v1
ELEVENLABS_TTS_MODEL=eleven_turbo_v2
ELEVENLABS_VOICE_ID=m5qndnI7u4OAdXhH0Mr5
```

4. Optional: install Node.js dependencies if you later add more JS tooling. The current repo utility runs with built-in Node modules only.

## Run

After the editable install above, run:

```bash
python -m hiresense_ai.interview.live_voice
```

Without installing the package, run:

```bash
PYTHONPATH=src python -m hiresense_ai.interview.live_voice
```

You can also use the package entrypoint:

```bash
hiresense-live
```

## Node Utility

The repository now includes a Node.js script for inspecting `metrics.jsonl`:

```bash
npm run metrics:summary
```

You can also pass a custom metrics file:

```bash
node scripts/metrics-summary.mjs path/to/metrics.jsonl
```

## How It Works

1. `audio/recorder.py` listens on the microphone and stops after silence is detected.
2. `audio/asr.py` sends the recorded audio to ElevenLabs STT.
3. `interview/live_voice.py` decides whether to exit, retry, or continue the interview loop.
4. Follow-up questions come from:
   - `interview/brain.py` for local rule-based logic used by the current entrypoint
   - `interview/llm.py` plus `interview/nlu.py` if you choose to wire in LLM-based follow-up generation
5. `audio/tts.py` speaks the interviewer response back to the user.
6. `MetricsLogger` appends turn data to `metrics.jsonl`.

## Notes

- The current runnable entrypoint is [`src/hiresense_ai/interview/live_voice.py`](/Users/dhruvdiwakirti/HireSense_AI/src/hiresense_ai/interview/live_voice.py).
- Runtime metrics are written to `metrics.jsonl` in the repository root.
- If `OPENAI_API_KEY` is missing, LLM follow-up generation should fall back to local logic where used.

## Cleanup Applied

- removed the stale nested `allystack/` duplicate project
- grouped runtime code under `src/hiresense_ai/`
- separated audio adapters from interview logic
- added a Node.js metrics summary utility for repository tooling
- standardized the README around the new package layout
