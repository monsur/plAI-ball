import os
from pathlib import Path
from openai import OpenAI
from podcaster.src import args_helper
from podcaster.src import logger_helper

logger = logger_helper.get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

def run(args):
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    content = (Path(args.output_dir) / f"{args.date}-transcript.txt").read_text(encoding='utf-8')

    try:
        speech_file_path = Path(args.output_dir) / f"{args.date}-audio.mp3"

        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="echo",
            input=content,
            instructions=(PROMPTS_DIR / "tts_voice.txt").read_text(),
        ) as response:
            response.stream_to_file(speech_file_path)
    except Exception as e:
        logger.error(f"Error generating summary: {e}")

if __name__ == "__main__":
    run(args_helper.get_args())
