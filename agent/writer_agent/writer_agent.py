from langchain.agents import Tool, AgentExecutor
from openai import OpenAI
import yaml
from prompts import DEFAULT_PROMPT

client = OpenAI()

data = yaml.safe_load(open("data/config.yaml"))

response = client.responses.create(model="gpt-6-astra", input="Write a short bedtime story about a unicorn.")

print(response.output_text)


class WriterAgent(question: str):

    def __init__(self, self.question: str, model_name: str = "gpt4o-mini") -> None:
        self.model_name = model_name
        self.question = question

    def generate_text(self, prompt: str, max_length: int = 50) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt")
        output = self.model.generate(**inputs, max_length=max_length)
        generated_text = self.tokenizer.decode(output[0], skip_special_tokens=True)
        return generated_text