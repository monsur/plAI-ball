from pathlib import Path
from podcaster.src import args_helper
from podcaster.src import logger_helper
from podcaster.src.gemini import Gemini
from podcaster.src.openai_api import OpenAIAPI

logger = logger_helper.get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

def get_client(input_model):
    # Supported models. The first model in the list is the default.
    # gpt-4.1 needs Tier 2 access for the prompt token size. But honestly I
    # didn't find gpt-4.1 that much better than gpt-4.1-mini for this task.
    openai_models = ["gpt-5.4-mini", "gpt-4.1-mini", "gpt-4.1"]
    gemini_models = ["gemini-2.5-pro-exp-03-25"]

    if input_model == "OpenAI":
        input_model = openai_models[0]
    elif input_model == "Gemini":
        input_model = gemini_models[0]

    if input_model in openai_models:
        logger.info(f"Using OpenAI model: {input_model}")
        return OpenAIAPI(input_model)
    elif input_model in gemini_models:
        logger.info(f"Using Gemini model: {input_model}")
        return Gemini(input_model)
    else:
        raise ValueError(f"Model {input_model} not supported. Supported models are: {openai_models + gemini_models}")

def run(args):
    system_instructions = (PROMPTS_DIR / "transcript.txt").read_text()

    client = get_client(args.model)

    prompt_text = (Path(args.output_dir) / "prompt.txt").read_text(encoding='utf-8')

    transcript = client.get_response(prompt_text, system_instructions)
    if transcript:
        (Path(args.output_dir) / f"{args.date}-transcript.txt").write_text(transcript, encoding='utf-8')

if __name__ == "__main__":
    run(args_helper.get_args())
