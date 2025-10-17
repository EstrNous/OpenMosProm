import os
import logging

from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
)
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.join(SCRIPT_DIR, "knowledge_base")
DB_DIR = os.path.join(SCRIPT_DIR, "db")
COLLECTION_NAME = "knowledge_base_main"
EMBED_MODEL_NAME = os.getenv("embed_model_name", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
CHUNK_SIZE = int(os.getenv("chunk_size", 512))
CHUNK_OVERLAP = int(os.getenv("chunk_overlap", 64))


def create_or_update_index():
    logging.info("запуск процесса индексации базы знаний...")

    reader = SimpleDirectoryReader(KB_DIR, recursive=True)
    documents = reader.load_data()
    if not documents:
        logging.warning("в папке knowledge_base не найдено документов. индексация прервана.")
        return
    logging.info(f"загружено документов: {len(documents)}")

    logging.info(f"загрузка embedding-модели: {EMBED_MODEL_NAME}")
    embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)

    splitter = SemanticSplitterNodeParser(
        buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embed_model
    )

    logging.info(f"инициализация/подключение к chromadb в папке: {DB_DIR}")
    db = chromadb.PersistentClient(path=DB_DIR)
    chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    logging.info("создание индекса... этот процесс может занять некоторое время.")
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=[splitter],
        embed_model=embed_model,
        show_progress=True,
    )
    logging.info(f"индексация успешно завершена. коллекция '{COLLECTION_NAME}' готова к работе.")
    return index


if __name__ == "__main__":
    create_or_update_index()