from langchain.agents import Tool, AgentExecutor
from openai import OpenAI
from prompts import prompt_template
from dotenv import load_dotenv
import os

load_dotenv()
model_name = os.getenv("OPENAI_MODEL")
api_key = os.getenv("OPENAI_API_KEY")

response = client.responses.create(model="gpt-6-astra", input="Write a short bedtime story about a unicorn.")

print(response.output_text)


class WriterAgent(question: str):

    def __init__(self, self.question: str) -> None:
        self.model_name = model_name
        self.question = question
        self.client = OpenAI(model=self.model_name, 
                            api_key=api_key) 

    def generate_text(self, max_length: int = 100) -> str:
        response = self.client.responses.create(
            model=self.model_name,
            input=prompt_template.format(question=self.question),
            max_tokens=max_length
        )
        return response.output_text