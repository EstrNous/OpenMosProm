from pydantic import BaseModel


class TaskSubmitRequest(BaseModel):
    user_query: str
    ticket_id: str


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
