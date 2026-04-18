"""
Test ElevenLabs Text-to-Dialogue API against a short excerpt of our transcript.

NOTE: The create_podcast (Studio) API requires enterprise whitelisting and is not
available on standard plans. This test uses the text-to-dialogue endpoint instead,
which accepts our pre-written ABE:/BAILEY: script and is available on standard plans.

Usage:
  # Step 1: list available voices and pick two IDs
  uv run python scripts/test_elevenlabs.py --list-voices

  # Step 2: run the test
  uv run python scripts/test_elevenlabs.py --abe-voice <ID> --bailey-voice <ID>

Outputs to scripts/output/:
  test_elevenlabs.mp3  — ElevenLabs Text-to-Dialogue, first ~10 exchanges

Compare against the existing v1 OpenAI single-host file:
  podcaster/output/20260402/20260402-audio.mp3
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs import ElevenLabs

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = REPO_ROOT / "scripts" / "output"
OUR_TRANSCRIPT = REPO_ROOT / "podcaster/output/20260402/20260402-transcript.txt"

# Text-to-Dialogue limit is 2,000 chars per request.
# We take the first N exchanges as a representative sample.
MAX_EXCHANGES = 10

# Hardcoded sample used when the transcript has no ABE:/BAILEY: tags (v1 format).
# Gives a feel for two-host banter quality without needing a v2 transcript.
SAMPLE_DIALOGUE = [
    ("ABE", "[excited] Welcome to Play Ball! Big Friday night in the majors. Bailey, I don't even know where to start."),
    ("BAILEY", "[excited] Has to be LA, Abe. Freddie Freeman. Bases loaded. Bottom of the ninth. Walk-off single."),
    ("ABE", "[surprised] Did you see that ball drop? That was not hit hard — that was placed."),
    ("BAILEY", "[laughs] The man just... wills it into the gap. That's five go-ahead RBIs in his last six games."),
    ("ABE", "Three walk-offs for the Dodgers this month. In April."),
    ("BAILEY", "Yeah. [sighs] The rest of the NL West is not having a fun spring."),
    ("ABE", "Alright, AL East — Yankees lost to Boston. Had the lead in the eighth."),
    ("BAILEY", "[sighs] Bullpen. Again. They're two and a half back already and the division is not slowing down."),
    ("ABE", "Meanwhile the Cubs have won four straight and nobody's talking about it."),
    ("BAILEY", "[excited] They're my sleeper pick and I'm sticking with it. Grind you down, take the series. They're real."),
]


def get_client():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("ELEVENLABS_API_KEY not set — add it to .env")
    return ElevenLabs(api_key=api_key)


def list_voices(client):
    voices = client.voices.get_all()
    print(f"\n{'Name':<28} {'Voice ID':<28} Category")
    print("-" * 70)
    for v in sorted(voices.voices, key=lambda x: x.name):
        print(f"{v.name:<28} {v.voice_id:<28} {v.category or ''}")


def parse_transcript(text, abe_voice_id, bailey_voice_id):
    """Parse ABE:/BAILEY: tagged transcript into text-to-dialogue inputs."""
    voice_map = {"ABE": abe_voice_id, "BAILEY": bailey_voice_id}
    inputs = []
    for line in text.splitlines():
        m = re.match(r"^(ABE|BAILEY):\s+(.+)", line.strip())
        if m:
            speaker, speech = m.group(1), m.group(2)
            inputs.append({"text": speech, "voice_id": voice_map[speaker]})
    return inputs


def main():
    parser = argparse.ArgumentParser(description="Test ElevenLabs Text-to-Dialogue API")
    parser.add_argument("--list-voices", action="store_true", help="Print available voices and exit")
    parser.add_argument("--abe-voice", help="Voice ID for Abe (host)")
    parser.add_argument("--bailey-voice", help="Voice ID for Bailey (guest)")
    parser.add_argument("--exchanges", type=int, default=MAX_EXCHANGES,
                        help=f"Number of exchanges to include (default: {MAX_EXCHANGES})")
    args = parser.parse_args()

    client = get_client()

    if args.list_voices:
        list_voices(client)
        return

    if not args.abe_voice or not args.bailey_voice:
        parser.error("--abe-voice and --bailey-voice required. Run --list-voices to browse options.")

    transcript = OUR_TRANSCRIPT.read_text()
    inputs = parse_transcript(transcript, args.abe_voice, args.bailey_voice)

    if not inputs:
        print(f"No ABE:/BAILEY: lines found in transcript (v1 format) — using built-in sample dialogue.")
        inputs = [
            {"text": text, "voice_id": args.abe_voice if speaker == "ABE" else args.bailey_voice}
            for speaker, text in SAMPLE_DIALOGUE
        ]

    sample = inputs[:args.exchanges]
    total_chars = sum(len(i["text"]) for i in sample)
    print(f"\nSending {len(sample)} exchanges ({total_chars} chars) to ElevenLabs Text-to-Dialogue...")
    print(f"Voices — Abe: {args.abe_voice}  Bailey: {args.bailey_voice}")

    audio = client.text_to_dialogue.convert(
        inputs=sample,
        model_id="eleven_v3",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "test_elevenlabs.mp3"
    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    size_kb = output_path.stat().st_size // 1024
    print(f"Saved: {output_path} ({size_kb} KB)")

    v1 = REPO_ROOT / "podcaster/output/20260402/20260402-audio.mp3"
    print(f"\nCompare:")
    print(f"  v1 (OpenAI, single host): {v1}")
    print(f"  EL (text-to-dialogue):    {output_path}")


if __name__ == "__main__":
    main()
