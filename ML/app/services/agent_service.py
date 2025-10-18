import logging
import time
from typing import Dict, Any, List

from .llm_service import LLMService
from .rag_service import RAGService
from .classifier_service import ClassifierService
import os

from ..schemas.agent_schemas import SourceNode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", 0.65))


class AgentService:
    def __init__(self, llm_service: LLMService, rag_service: RAGService, classifier_service: ClassifierService):
        self._llm_service = llm_service
        self._rag_service = rag_service
        self._classifier_service = classifier_service

    def process_query(self, user_query: str) -> Dict[str, Any]:
        logging.info(f"--- Начало быстрой обработки запроса: '{user_query}' ---")
        start_time = time.time()

        category = self._classifier_service.predict(user_query)
        logging.info(f"Запрос классифицирован как: '{category}'")

        if category == "Мусор":
            logging.info("Категория 'Мусор', немедленная эскалация.")
            return self._escalate(
                user_query=user_query,
                reason="Запрос классифицирован как нерелевантный.",
                category=category,
                start_time=start_time
            )

        sources: List[SourceNode] = self._rag_service.query(user_query)

        if sources and sources[0].score >= RAG_CONFIDENCE_THRESHOLD:
            logging.info(f"Найдено релевантное решение в Базе Знаний (score: {sources[0].score:.2f}).")

            best_source = sources[0]
            processing_time = time.time() - start_time

            return {
                "action_type": "answer",
                "payload": {
                    "category": category,
                    "summary": best_source.text,
                    "sources": sources
                },
                "metadata": {
                    "processing_time_sec": round(processing_time, 2)
                }
            }
        else:
            logging.info("В Базе Знаний не найдено подходящего решения. Эскалация.")
            return self._escalate(
                user_query=user_query,
                reason="Релевантное решение в Базе Знаний не найдено.",
                category=category,
                start_time=start_time
            )

    @staticmethod
    def _escalate(user_query: str, reason: str, category: str, start_time: float) -> Dict[str, Any]:
        processing_time = time.time() - start_time
        summary = f"Запрос отнесен к категории '{category}'. Требуется ручная обработка."

        return {
            "action_type": "escalate",
            "payload": {
                "category": category,
                "summary": summary,
                "reason": reason
            },
            "metadata": {
                "processing_time_sec": round(processing_time, 2)
            }
        }