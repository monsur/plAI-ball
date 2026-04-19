"""
Test OpenAI Text-to-Speech against a short two-host excerpt, to evaluate
quality before committing to the V2_COST_PLAN refactor.

Mirrors scripts/test_elevenlabs.py so the two outputs are directly comparable.
Key differences from the ElevenLabs test:
  - Per-speaker TTS calls (OpenAI has no text-to-dialogue equivalent)
  - Uses gpt-4o-mini-tts `instructions` parameter — wires in the previously
    unused tts_abe.txt / tts_bailey.txt prompt files
  - Stitches per-turn audio with pydub, injecting a small gap on speaker switches
  - No seed parameter (OpenAI voices are fixed presets, no drift to bound)

Usage:
  # Default voices (echo for Abe, nova for Bailey):
  uv run python scripts/test_openai_tts.py

  # Try a different pairing:
  uv run python scripts/test_openai_tts.py --abe-voice onyx --bailey-voice shimmer

  # List available voice presets:
  uv run python scripts/test_openai_tts.py --list-voices

Output:
  scripts/output/test_openai_tts.mp3

Compare against:
  scripts/output/test_elevenlabs.mp3  (ElevenLabs text-to-dialogue)
  podcaster/output/20260402/20260402-audio.mp3  (v1 single-host OpenAI)
"""

import argparse
import os
import sys
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydub import AudioSegment

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = REPO_ROOT / "scripts" / "output"
PROMPTS_DIR = REPO_ROOT / "podcaster" / "src" / "prompts"

# gpt-4o-mini-tts voice presets. Listed in the OpenAI TTS docs.
AVAILABLE_VOICES = [
    "alloy", "ash", "ballad", "coral", "echo", "fable",
    "nova", "onyx", "sage", "shimmer", "verse",
]

# Default pairing — echo is what v1 used for Abe; nova is a brighter contrast
# for Bailey. Overridable from the CLI so you can A/B pairings quickly.
DEFAULT_ABE_VOICE = "echo"
DEFAULT_BAILEY_VOICE = "nova"

MODEL = "gpt-4o-mini-tts"

# Silence injected between speaker switches, mirroring the TURN_GAP_MS config
# knob proposed in V2_COST_PLAN.md step 4.
TURN_GAP_MS = 250

# 10 exchanges covering the same beats as scripts/test_elevenlabs.py, but
# written to the updated transcript.txt guidance: no bracket cues — emotion
# carried by word choice, punctuation, and rhythm. This mirrors what the
# real pipeline will emit after the transcript-prompt update.
SAMPLE_DIALOGUE = [
    ("ABE", "Welcome to Play Ball! Big Friday night in the majors. Bailey, I don't even know where to start."),
    ("BAILEY", "Has to be LA, Abe. Freddie Freeman. Bases loaded. Bottom of the ninth. Walk-off single."),
    ("ABE", "Man, did you see that ball drop? That was not hit hard — that was placed."),
    ("BAILEY", "The man just... wills it into the gap. Five go-ahead RBIs in his last six games."),
    ("ABE", "Three walk-offs for the Dodgers this month. In April."),
    ("BAILEY", "Yeah. The rest of the NL West is not having a fun spring."),
    ("ABE", "Alright, AL East — Yankees lost to Boston. Had the lead in the eighth."),
    ("BAILEY", "Bullpen. Again. They're two and a half back already and the division is not slowing down."),
    ("ABE", "Meanwhile the Cubs have won four straight and nobody's talking about it."),
    ("BAILEY", "They're my sleeper pick and I'm sticking with it. Grind you down, take the series. They're real."),
]


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        sys.exit("OPENAI_API_KEY not set — add it to .env")
    return OpenAI(api_key=api_key)


def group_by_speaker(dialogue):
    """Collapse consecutive same-speaker lines into one TTS call.

    Returns a list of (speaker, joined_text) tuples. For the sample dialogue
    every turn alternates, so each group is one line — but the function is
    written to match the planned chunk_inputs() behavior in audio.py, which
    will group longer monologues together.
    """
    groups = []
    for speaker, text in dialogue:
        if groups and groups[-1][0] == speaker:
            groups[-1] = (speaker, groups[-1][1] + " " + text)
        else:
            groups.append((speaker, text))
    return groups


def synthesize(client, text, voice, instructions):
    """Single TTS call → raw MP3 bytes."""
    response = client.audio.speech.create(
        model=MODEL,
        voice=voice,
        input=text,
        instructions=instructions,
        response_format="mp3",
    )
    return response.content


def main():
    parser = argparse.ArgumentParser(description="Test OpenAI TTS for two-host podcast")
    parser.add_argument("--list-voices", action="store_true", help="Print available voices and exit")
    parser.add_argument("--abe-voice", default=DEFAULT_ABE_VOICE,
                        help=f"Voice for Abe (default: {DEFAULT_ABE_VOICE})")
    parser.add_argument("--bailey-voice", default=DEFAULT_BAILEY_VOICE,
                        help=f"Voice for Bailey (default: {DEFAULT_BAILEY_VOICE})")
    args = parser.parse_args()

    if args.list_voices:
        print("Available gpt-4o-mini-tts voices:")
        for v in AVAILABLE_VOICES:
            print(f"  {v}")
        return

    for v in (args.abe_voice, args.bailey_voice):
        if v not in AVAILABLE_VOICES:
            sys.exit(f"Unknown voice: {v}. Run --list-voices to see options.")

    client = get_client()

    voice_map = {"ABE": args.abe_voice, "BAILEY": args.bailey_voice}
    instructions_map = {
        "ABE": (PROMPTS_DIR / "tts_abe.txt").read_text(),
        "BAILEY": (PROMPTS_DIR / "tts_bailey.txt").read_text(),
    }

    groups = group_by_speaker(SAMPLE_DIALOGUE)
    total_chars = sum(len(text) for _, text in groups)
    print(f"\nSynthesizing {len(groups)} turns ({total_chars} chars) with {MODEL}...")
    print(f"Voices — Abe: {args.abe_voice}  Bailey: {args.bailey_voice}")

    output = AudioSegment.empty()
    prev_speaker = None
    for i, (speaker, text) in enumerate(groups, 1):
        print(f"  [{i}/{len(groups)}] {speaker}: {text[:60]}{'...' if len(text) > 60 else ''}")
        mp3_bytes = synthesize(client, text, voice_map[speaker], instructions_map[speaker])
        segment = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")

        if prev_speaker is not None and speaker != prev_speaker:
            output += AudioSegment.silent(duration=TURN_GAP_MS)
        output += segment
        prev_speaker = speaker

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "test_openai_tts.mp3"
    output.export(output_path, format="mp3")

    size_kb = output_path.stat().st_size // 1024
    duration_s = len(output) / 1000
    print(f"\nSaved: {output_path} ({size_kb} KB, {duration_s:.1f}s)")

    # Rough cost estimate: gpt-4o-mini-tts is ~$0.015/minute of audio output,
    # plus ~$0.60/1M input tokens (negligible at this scale).
    est_cost = (duration_s / 60) * 0.015
    print(f"Estimated cost: ~${est_cost:.4f}")

    el = OUTPUT_DIR / "test_elevenlabs.mp3"
    v1 = REPO_ROOT / "podcaster/output/20260402/20260402-audio.mp3"
    print(f"\nCompare:")
    print(f"  OpenAI (two-host, this run):     {output_path}")
    if el.exists():
        print(f"  ElevenLabs (two-host dialogue):  {el}")
    if v1.exists():
        print(f"  v1 OpenAI (single host):         {v1}")


if __name__ == "__main__":
    main()
