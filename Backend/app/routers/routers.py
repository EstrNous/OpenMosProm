import os
import httpx
from fastapi import APIRouter, HTTPException, status
from dotenv import load_dotenv
from ..schemas import PromptRequest, SimpleAnswer

# Загружаем переменные окружения
load_dotenv()

r = APIRouter()

ML_API_URL = os.getenv('ML_API_URL')

@r.post("/test-ml",response_model=SimpleAnswer)
async def test_func(request: PromptRequest):
    ml_request = {
        "prompt": request.prompt
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ML_API_URL}/api/v1/agent/test-prompt",
                json=ml_request,
                timeout=90.0
            )
            response.raise_for_status()
            return response.json()

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ml service is unavailable: {e}"
        )
