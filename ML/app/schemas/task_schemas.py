from pydantic import BaseModel


class TaskSubmitRequest(BaseModel):
    user_query: str
    dialog_id: str


class TaskSubmitResponse(BaseModel):
    dialog_id: str
    status: str
