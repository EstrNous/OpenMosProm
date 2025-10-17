from pydantic import BaseModel, Optional

class PromptRequest(BaseModel):
    prompt: str

class SimpleAnswer(BaseModel):
    answer: str

class SupportRequest(BaseModel):
    user_message: str
    user_id: str
    timestamp: str
    channel: str = "web"

class TicketCreateIn(BaseModel):
    dialog_id: Optional[int] = None
    type: Optional[str] = None

class TicketOut(BaseModel):
    id: int
    dialog_id: Optional[int]
    status: str
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    type: Optional[str] = None

    class Config:
        orm_mode = True

class EnqueueIn(BaseModel):
    dialog_id: int
    type: Optional[str] = None

class DequeueOut(BaseModel):
    ticket_id: int
    dialog_id: Optional[int]
    status: str

class ResultIn(BaseModel):
    ticket_id: int
    result: Optional[dict] = None
    solved: bool = True