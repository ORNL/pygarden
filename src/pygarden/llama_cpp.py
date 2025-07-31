"""
A Base Class to Instantiate LLM in Python. Set your own environment variable MODEL_PATH to load your
model of choice located at that path. Obtain an appropritate GGUF Model from Huggingface.
Example usage:
CLI:
    uv run python -m pygarden.llama_cpp --prompt "What is the capital of France?"
In code:
    with LlamaCPP() as llama:
        print(llama.prompt("What is the capital of France?"))
"""

import argparse
import os
import sys
from contextlib import contextmanager

from llama_cpp import Llama

from pygarden.env import check_environment as ce


MAX_TOKENS = ce('MAX_TOKENS', 32)


@contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


class LlamaCPP:
    """
    A base class to instantiate and interact with a GGUF-format LLaMA model in Python.

    Loads the model from a file specified by the ``MODEL_PATH`` environment variable.
    Intended for use with context management to safely load and unload the model.
    """

    def __init__(self, max_tokens=None, **kwargs):
        """
        Initialize the LlamaCPP interface.

        Loads the model path from the environment variable ``MODEL_PATH`` or defaults to
        ``~/models/llama.gguf``. Raises an error if the model file does not exist.

        :raises FileNotFoundError: If the model file cannot be found at the resolved path.
        """
        self.model_path = os.path.expanduser(os.getenv("MODEL_PATH", "~/models/llama.gguf"))
        self.llm = None
        self.kwargs = kwargs
        self.max_tokens = max_tokens if max_tokens else MAX_TOKENS
        if not os.path.exists(self.model_path):
            print(
                f"Model file not found: {self.model_path}. \
                    Please download the model and set the environment variable MODEL_PATH."
            )
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

    def __enter__(self):
        """
        Load the LLaMA model and return the initialized instance.

        Used when entering a context manager block (i.e., ``with LlamaCPP() as model:``).
        Suppresses backend stderr output during model load.

        :return: The initialized instance of LlamaCPP.
        :rtype: LlamaCPP
        """
        with (suppress_stderr()):
            self.llm = Llama(self.model_path)
            if self.max_tokens is None:
                self.max_tokens = self.llm.n_ctx()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Clean up and release model resources when exiting the context.

        Resets internal state and allows exceptions to propagate.

        :param exc_type: The exception type (if any).
        :type exc_type: type
        :param exc_value: The exception instance (if any).
        :type exc_value: BaseException
        :param traceback: The traceback object (if any).
        :type traceback: types.TracebackType
        :return: False to indicate any exceptions should be propagated.
        :rtype: bool
        """
        self.llm = None
        pass

    def prompt(self, prompt):
        """
        Generate a response from the LLaMA model based on the given prompt.

        :param prompt: The input prompt to send to the model.
        :type prompt: str
        :return: The generated text response from the model.
        :rtype: str
        :raises RuntimeError: If the model has not been initialized (i.e., used outside of a context manager).
        """
        if self.llm is None:
            raise RuntimeError("Model is not loaded. Use this class in a context manager (`with` block).")
        with suppress_stderr():
            output = self.llm(f"Q: {prompt}\nA:", max_tokens=self.max_tokens)

        res = output["choices"][0]["text"]
        return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a prompt through a LLaMA GGUF model.")
    parser.add_argument("--prompt", type=str, required=True,
                        help="The prompt to send to the model.")
    parser.add_argument("--tokens", type=int, default=None,
                        help="The max number of tokens to generate. Defaults to n_ctx.")
    args = parser.parse_args()

    with LlamaCPP(max_tokens=args.tokens) as llama:
        print(llama.prompt(args.prompt))
    sys.exit(0)
