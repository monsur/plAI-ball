import os
import re
from io import BytesIO
from pathlib import Path
from elevenlabs import ElevenLabs
from pydub import AudioSegment
from podcaster.src import args_helper
from podcaster.src import logger_helper

logger = logger_helper.get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

VOICE_MAP = {
    "ABE":    os.getenv("ABE_VOICE_ID"),
    "BAILEY": os.getenv("BAILEY_VOICE_ID"),
}
ELEVENLABS_MODEL  = os.getenv("ELEVENLABS_MODEL", "eleven_v3")
AUDIO_CHUNK_SIZE  = int(os.getenv("AUDIO_CHUNK_SIZE", "1900"))
PAUSE_DURATION_MS = int(os.getenv("PAUSE_DURATION_MS", "1000"))

SPEAKER_LINE = re.compile(r"^(ABE|BAILEY):\s+(.+)$")
PAUSE_LINE = re.compile(r"^\[PAUSE\]\s*$")


def parse_transcript(text):
    """Parse a transcript into (speaker, text) tuples and pause sentinels.

    Returns a list of tuples:
        ('ABE', 'spoken text...')
        ('BAILEY', 'spoken text...')
        ('PAUSE', None)
    Blank lines, headers, and any line not matching the expected format are skipped.
    """
    segments = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if PAUSE_LINE.match(line):
            segments.append(('PAUSE', None))
            continue
        m = SPEAKER_LINE.match(line)
        if m:
            segments.append((m.group(1), m.group(2)))
    return segments


def chunk_inputs(segments, max_chars=None):
    """Group consecutive (speaker, text) pairs into chunks under max_chars.

    PAUSE sentinels are emitted as standalone chunks so silence can be injected
    between dialogue groups. Grouping minimizes the number of TTS calls, which
    reduces audible stitching seams in the final output.
    """
    if max_chars is None:
        max_chars = AUDIO_CHUNK_SIZE

    chunks = []
    current = []
    current_len = 0
    for seg in segments:
        speaker, text = seg
        if speaker == 'PAUSE':
            if current:
                chunks.append(current)
                current = []
                current_len = 0
            chunks.append([seg])
            continue

        text_len = len(text)
        if current and current_len + text_len > max_chars:
            chunks.append(current)
            current = []
            current_len = 0
        current.append(seg)
        current_len += text_len

    if current:
        chunks.append(current)
    return chunks


def run(args):
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    transcript_path = Path(args.output_dir) / f"{args.date}-transcript.txt"
    transcript = transcript_path.read_text(encoding='utf-8')

    segments = parse_transcript(transcript)
    chunks = chunk_inputs(segments, max_chars=AUDIO_CHUNK_SIZE)

    output = AudioSegment.empty()
    try:
        for chunk in chunks:
            if len(chunk) == 1 and chunk[0][0] == 'PAUSE':
                output += AudioSegment.silent(duration=PAUSE_DURATION_MS)
                continue

            inputs = [
                {"text": text, "voice_id": VOICE_MAP[speaker]}
                for speaker, text in chunk
            ]
            audio_bytes = b"".join(client.text_to_dialogue.convert(
                inputs=inputs,
                model_id=ELEVENLABS_MODEL,
            ))
            output += AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")

        out_path = Path(args.output_dir) / f"{args.date}-audio.mp3"
        output.export(out_path, format="mp3")
    except Exception as e:
        logger.error(f"Error generating audio: {e}")


if __name__ == "__main__":
    run(args_helper.get_args())
