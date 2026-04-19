import os
import re
from io import BytesIO
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment
from podcaster.src import args_helper
from podcaster.src import config
from podcaster.src import logger_helper

logger = logger_helper.get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

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
    """Group consecutive same-speaker segments into chunks under max_chars.

    Each non-PAUSE chunk contains exactly one speaker: a speaker switch
    forces a new chunk even if the size limit isn't reached. This matches
    the per-host TTS pipeline, where each chunk becomes a single
    `client.audio.speech.create(voice=...)` call.

    PAUSE sentinels are emitted as standalone chunks so silence can be injected
    between dialogue groups.
    """
    if max_chars is None:
        max_chars = config.AUDIO_CHUNK_SIZE

    chunks = []
    current = []
    current_speaker = None
    current_len = 0
    for seg in segments:
        speaker, text = seg
        if speaker == 'PAUSE':
            if current:
                chunks.append(current)
                current = []
                current_speaker = None
                current_len = 0
            chunks.append([seg])
            continue

        text_len = len(text)
        speaker_switch = current and speaker != current_speaker
        too_large = current and current_len + text_len > max_chars
        if speaker_switch or too_large:
            chunks.append(current)
            current = []
            current_len = 0
        current.append(seg)
        current_speaker = speaker
        current_len += text_len

    if current:
        chunks.append(current)
    return chunks


def run(args):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    transcript_path = Path(args.output_dir) / f"{args.date}-transcript.txt"
    transcript = transcript_path.read_text(encoding='utf-8')

    segments = parse_transcript(transcript)
    chunks = chunk_inputs(segments, max_chars=config.AUDIO_CHUNK_SIZE)

    voice_map = {"ABE": config.ABE_VOICE, "BAILEY": config.BAILEY_VOICE}
    instructions_map = {
        "ABE": (PROMPTS_DIR / "tts_abe.txt").read_text(encoding="utf-8"),
        "BAILEY": (PROMPTS_DIR / "tts_bailey.txt").read_text(encoding="utf-8"),
    }

    output = AudioSegment.empty()
    prev_speaker = None
    try:
        for chunk in chunks:
            if len(chunk) == 1 and chunk[0][0] == 'PAUSE':
                output += AudioSegment.silent(duration=config.PAUSE_DURATION_MS)
                prev_speaker = None
                continue

            speaker = chunk[0][0]
            text = " ".join(line for _, line in chunk)

            if prev_speaker is not None and speaker != prev_speaker:
                output += AudioSegment.silent(duration=config.TURN_GAP_MS)

            response = client.audio.speech.create(
                model=config.OPENAI_TTS_MODEL,
                voice=voice_map[speaker],
                input=text,
                instructions=instructions_map[speaker],
                response_format="mp3",
            )
            output += AudioSegment.from_file(BytesIO(response.content), format="mp3")
            prev_speaker = speaker

        out_path = Path(args.output_dir) / f"{args.date}-audio.mp3"
        output.export(out_path, format="mp3")
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise


if __name__ == "__main__":
    run(args_helper.get_args())
