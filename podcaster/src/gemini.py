from google import genai
from google.genai import types
from podcaster.src import logger_helper
from podcaster.src import os_helper

logger = logger_helper.get_logger(__name__)

class Gemini:
    def __init__(self, model):
        self.client = genai.Client(api_key=os_helper.getenv('GEMINI_API_KEY'))
        self.model = model
        self.temperature = 0.2

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
