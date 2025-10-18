from fastapi import APIRouter, HTTPException

from app.core import settings

from ...schemas.agent_schemas import (
    PromptRequest, SimpleAnswer,
    RAGQueryRequest, RAGQueryResponse,
    AgentQueryRequest, AgentQueryResponse
)

from ...schemas.task_schemas import TaskSubmitRequest, TaskSubmitResponse

from ...tasks import process_ticket_query

router = APIRouter()


@router.post("/test-prompt", response_model=SimpleAnswer)
def test_simple_prompt(request: PromptRequest):
    if settings.llm_service_instance is None:
        raise HTTPException(status_code=503, detail="LLM service is not initialized yet")

    answer = settings.llm_service_instance.get_simple_response(request.prompt)
    return SimpleAnswer(answer=answer)


@router.post("/rag-query", response_model=RAGQueryResponse)
def test_rag_query(request: RAGQueryRequest):
    if settings.rag_service_instance is None:
        raise HTTPException(status_code=503, detail="RAG service is not initialized yet")

    sources = settings.rag_service_instance.query(request.query)
    return RAGQueryResponse(sources=sources)


@router.post("/process-query", response_model=AgentQueryResponse)
def process_user_query(request: AgentQueryRequest):
    if settings.agent_service_instance is None:
        raise HTTPException(status_code=503, detail="Agent service is not initialized yet")

    result = settings.agent_service_instance.process_query(request.user_query)
    return result


@router.post("/submit-task", response_model=TaskSubmitResponse)
def submit_task(request: TaskSubmitRequest):
    task = process_ticket_query.delay(
        user_query=request.user_query,
        ticket_id=request.ticket_id
    )

    return TaskSubmitResponse(task_id=task.id, status="accepted")
