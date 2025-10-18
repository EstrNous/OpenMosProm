import requests
import os
from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL")
MODEL_NAME = os.getenv("MODEL_NAME")


class LLMService:
    def __init__(self, llm: OpenAI):
        self._llm = llm

    @staticmethod
    def _send_request(prompt: str) -> str:
        if not OLLAMA_URL:
            raise ValueError("Не задана переменная окружения OLLAMA_URL")

        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_ctx": 2048
                    }
                },
                timeout=180
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.RequestException as e:
            print(f"Ошибка при обращении к Ollama: {e}")
            return "Извините, сервис LLM временно недоступен."

    def get_simple_response(self, prompt: str) -> str:
        return self._send_request(prompt)

    def get_rag_based_answer(self, user_query: str, context: str) -> str:
        prompt = f"""
            Ты — полезный ассистент службы поддержки. Твоя задача — ответить на вопрос пользователя, опираясь ИСКЛЮЧИТЕЛЬНО на предоставленный ниже контекст. Не придумывай ничего от себя. Если в контексте нет прямого ответа, вежливо сообщи об этом. Старайся писать не в общем, а более конкретно по шагам, если информации из базы знаний для этого достаточно.
            
            КОНТЕКСТ:
            ---
            {context}
            ---
            
            ВОПРОС ПОЛЬЗОВАТЕЛЯ:
            {user_query}
            
            ОТВЕТ:
            """
        return self._send_request(prompt)
