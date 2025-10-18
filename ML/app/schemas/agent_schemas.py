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
    category: str
    summary: str
    sources: List[SourceNode]


class EscalatePayload(BaseModel):
    category: str
    summary: str
    reason: str


class MetaData(BaseModel):
    processing_time_sec: float


class AgentQueryResponse(BaseModel):
    action_type: str
    payload: Union[AnswerPayload, EscalatePayload]
    metadata: MetaData
