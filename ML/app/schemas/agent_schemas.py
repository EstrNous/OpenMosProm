from pydantic import BaseModel
from typing import List, Union


class PromptRequest(BaseModel):
    prompt: str


class SimpleAnswer(BaseModel):
    answer: str


class RAGQueryRequest(BaseModel):
    query: str


class SourceNode(BaseModel):
    text: str
    score: float
    filename: str


class RAGQueryResponse(BaseModel):
    sources: List[SourceNode]


class AgentQueryRequest(BaseModel):
    user_query: str


class AnswerPayload(BaseModel):
    answer_text: str
    sources: List[SourceNode]


class EscalatePayload(BaseModel):
    reason: str
    summary: str
    final_message_for_user: str


class MetaData(BaseModel):
    total_duration_sec: float
    rag_duration_sec: float
    llm_duration_sec: float | None = None


class AgentQueryResponse(BaseModel):
    action_type: str
    payload: Union[AnswerPayload, EscalatePayload]
    metadata: MetaData | None = None
