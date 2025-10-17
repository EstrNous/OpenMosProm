import requests
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL")
MODEL_NAME = os.getenv("MODEL_NAME")


class LLMService:
    @staticmethod
    def get_simple_response(prompt: str) -> str:
        if not OLLAMA_URL:
            raise ValueError("не задана переменная окружения OLLAMA_URL")

        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.RequestException as e:
            print(f"ошибка при обращении к ollama: {e}")
            return "извините, сервис llm временно недоступен"


llm_service = LLMService()
