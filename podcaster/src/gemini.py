import os
from google import genai
from google.genai import types
from podcaster.src import logger_helper

logger = logger_helper.get_logger(__name__)

class Gemini:
    def __init__(self, model):
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = model
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    def get_response(self, prompt, system_instructions):
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=[system_instructions],
                    temperature=self.temperature
                ),
            )
            return response.text
        except Exception as e:
            logger.exception("Error generating summary")
            return None
