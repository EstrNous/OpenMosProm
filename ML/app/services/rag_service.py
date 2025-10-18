import os
import logging
from typing import List

from dotenv import load_dotenv
import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.schemas.agent_schemas import SourceNode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

DB_DIR = "./db"
COLLECTION_NAME = "knowledge_base_main"
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", 3))


class RAGService:
    def __init__(self, embed_model: HuggingFaceEmbedding):
        logging.info("Инициализация RAGService...")

        db = chromadb.PersistentClient(path=DB_DIR)
        chroma_collection = db.get_collection(COLLECTION_NAME)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=embed_model,
        )

        self.retriever = self.index.as_retriever(
            similarity_top_k=TOP_K_RESULTS
        )

        logging.info("RAGService готов к работе.")

    def query(self, user_query: str) -> List[SourceNode]:
        logging.info(f"Выполняется RAG-поиск по запросу: '{user_query}'")

        nodes_with_scores = self.retriever.retrieve(user_query)

        if not nodes_with_scores:
            logging.warning("Релевантных документов не найдено.")
            return []

        results = []
        for node in nodes_with_scores:
            source_node = SourceNode(
                text=node.get_content(),
                score=node.get_score(),
                filename=node.metadata.get("file_name", "N/A"),
            )
            results.append(source_node)

        logging.info(f"Найдено {len(results)} релевантных источников.")
        return results
