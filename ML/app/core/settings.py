import logging
import os
from dotenv import load_dotenv
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from ..services.rag_service import RAGService
from ..services.llm_service import LLMService
from ..services.agent_service import AgentService

llm_service_instance: LLMService | None = None
rag_service_instance: RAGService | None = None
agent_service_instance: AgentService | None = None


async def setup_services():
    global llm_service_instance, rag_service_instance, agent_service_instance
    logging.info("Начинаю инициализацию сервисов...")

    load_dotenv()

    embed_model = HuggingFaceEmbedding(
        model_name=os.getenv("EMBED_MODEL_NAME"),
        query_instruction="query: ",
        text_instruction="passage: "
    )

    llm = OpenAI(
        model="gpt-3.5-turbo",

        api_base=os.getenv("OLLAMA_URL", "http://ollama:11434") + "/v1",
        api_key="dummy_key",
        request_timeout=120.0,
    )

    llm_service_instance = LLMService(llm=llm)
    rag_service_instance = RAGService(embed_model=embed_model)  # <-- Больше не передаём llm
    agent_service_instance = AgentService(
        llm_service=llm_service_instance,
        rag_service=rag_service_instance
    )
    logging.info("Все сервисы успешно инициализированы.")


async def shutdown_services():
    logging.info("Сервисы остановлены.")
