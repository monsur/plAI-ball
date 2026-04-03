from openai import OpenAI
from podcaster.src import os_helper

class OpenAIAPI:
   def __init__(self, model):
      self.client = OpenAI(api_key=os_helper.getenv('OPENAI_API_KEY'))
      self.model = model
      self.temperature = 0.2

   def get_response(self, prompt, system_instructions):
      try:
         response = self.client.chat.completions.create(
            model=self.model,
            messages=[
               {
                  "role": "system",
                  "content": system_instructions
               },
               {
                  "role": "user",
                  "content": prompt
               }
            ], temperature=self.temperature)
         return response.choices[0].message.content
      except Exception as e:
         print(f"Error generating summary: {e}")
         return None
