from pydantic import BaseModel

class PromptRequest(BaseModel):
    prompt: str

class SimpleAnswer(BaseModel):
    answer: str