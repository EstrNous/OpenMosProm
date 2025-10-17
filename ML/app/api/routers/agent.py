from fastapi import APIRouter
from ...schemas.agent_schemas import PromptRequest, SimpleAnswer
from ...services.llm_service import llm_service

router = APIRouter()


@router.post("/test-prompt", response_model=SimpleAnswer)
def test_simple_prompt(request: PromptRequest):
    answer = llm_service.get_simple_response(request.prompt)
    return SimpleAnswer(answer=answer)
