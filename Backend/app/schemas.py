from pydantic import BaseModel

class PromptRequest(BaseModel):
    prompt: str

class SimpleAnswer(BaseModel):
    answer: str

class SupportRequest(BaseModel):
    user_message: str
    user_id: str
    timestamp: str
    channel: str = "web"