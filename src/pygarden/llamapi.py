""" Host a LLAMA API server using FastAPI.
HINT: use this in your Dockerfile:
CMD ["uvicorn", "llamapi.llamapi:app", "--host", "0.0.0.0", "--port", "8080"]"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from pygarden.llama_cpp import LlamaCPP


# Define input request schema
class QueryRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 40
    temperature: Optional[float] = 0.0

# Initialize FastAPI app and model instance
app = FastAPI()

def llama_prompt(p: str, tokens=1028) -> str:
    # print(prompt)
    # os.environ["MODEL_PATH"] = '/models/qwen2.5-coder-14b-instruct-q5_k_m.gguf'
    with LlamaCPP(max_tokens=128) as llama:
        res = llama.prompt(p)
    return res


# Define API endpoint
@app.post("/query")
async def query_model(request: QueryRequest):
    try:
        print(f"RUNNING: {request.prompt}")
        output = llama_prompt(request.prompt, request.max_tokens)
        return {"response": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
