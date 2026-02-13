"""Provide a convenient class interface to the Ollama client. """

import ollama


class OllamaClient:
    def __init__(self, model_name: str):
        self.client = None
        self.model_name = model_name

    def __enter__(self):
        self.client = ollama.Client(host="http://localhost:11434")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # No need to release anything as Ollama does not require manual connection management
        self.client = None
        pass

    def chat(self, model, messages):
        return self.client.chat(model=self.model_name, messages=messages)


if __name__ == "__main__":
    with OllamaClient("gpt-oss:20b") as client:
        response = client.chat(
            model='gpt-oss:20b',
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What's the difference between RAG and fine-tuning?"}
            ]
            )