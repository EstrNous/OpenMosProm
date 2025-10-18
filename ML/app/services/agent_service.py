import logging
from typing import Dict, Any
import time

from .llm_service import LLMService
from .rag_service import RAGService
from ..schemas.agent_schemas import SourceNode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", 0.65))


class AgentService:
    def __init__(self, llm_service: LLMService, rag_service: RAGService):
        self._llm_service = llm_service
        self._rag_service = rag_service

    def process_query(self, user_query: str) -> Dict[str, Any]:
        logging.info(f"--- Начало обработки запроса: '{user_query}' ---")
        start_time = time.time()

        rag_start_time = time.time()
        sources = self._rag_service.query(user_query)
        rag_duration = time.time() - rag_start_time

        if not sources:
            logging.warning("RAG не вернул источников. Переход к эскалации.")
            return self._escalate(user_query, "Не найдено релевантных документов в базе знаний.", start_time,
                                  rag_duration)

        highest_score = max(source['score'] for source in sources)
        logging.info(f"Наивысшая оценка релевантности: {highest_score:.2f}")

        if highest_score < RAG_CONFIDENCE_THRESHOLD:
            logging.warning(
                f"Оценка релевантности ({highest_score:.2f}) ниже порога ({RAG_CONFIDENCE_THRESHOLD}). Эскалация.")
            return self._escalate(user_query,
                                  f"Недостаточная уверенность в найденных документах (score: {highest_score:.2f}).",
                                  start_time, rag_duration)

        filtered_sources = [source for source in sources if source['score'] >= RAG_CONFIDENCE_THRESHOLD]

        logging.info("Найдена релевантная информация. Генерация ответа...")
        context = "\n---\n".join([source['text'] for source in filtered_sources])

        llm_start_time = time.time()
        final_answer = self._llm_service.get_rag_based_answer(user_query, context)
        llm_duration = time.time() - llm_start_time

        total_duration = time.time() - start_time
        logging.info("Ответ сгенерирован. Формирование финального результата.")
        return {
            "action_type": "answer",
            "payload": {
                "answer_text": final_answer,
                "sources": [SourceNode(**s) for s in filtered_sources]
            },
            "metadata": {
                "total_duration_sec": round(total_duration, 2),
                "rag_duration_sec": round(rag_duration, 2),
                "llm_duration_sec": round(llm_duration, 2)
            }
        }

    @staticmethod
    def _escalate(user_query: str, reason: str, start_time: float, rag_duration: float) -> Dict[str, Any]:
        logging.info("Формирование ответа для эскалации...")
        summary = f"Пользователь спросил: '{user_query}'. Агент не смог найти ответ."
        total_duration = time.time() - start_time
        return {
            "action_type": "escalate",
            "payload": {
                "reason": reason,
                "summary": summary,
                "final_message_for_user": "К сожалению, я не смог найти точный ответ на ваш вопрос. Передаю ваше обращение специалисту."
            },
            "metadata": {
                "total_duration_sec": round(total_duration, 2),
                "rag_duration_sec": round(rag_duration, 2),
                "llm_duration_sec": None
            }
        }
