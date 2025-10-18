import os
import logging

from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from llama_index.readers.file import PyMuPDFReader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.join(SCRIPT_DIR, "knowledge_base")
DB_DIR = "/app/db"
COLLECTION_NAME = "knowledge_base_main"
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "intfloat/multilingual-e5-large")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 512))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 64))


def create_or_update_index():
    logging.info("запуск процесса индексации базы знаний...")

    file_extractor = {
        ".pdf": PyMuPDFReader()
    }
    reader = SimpleDirectoryReader(
        KB_DIR,
        recursive=True,
        file_extractor=file_extractor
    )

    documents = reader.load_data()

    if not documents:
        logging.warning("в папке knowledge_base не найдено документов. индексация прервана.")
        return
    logging.info(f"загружено документов: {len(documents)}")

    logging.info(f"загрузка embedding-модели: {EMBED_MODEL_NAME}")
    embed_model = HuggingFaceEmbedding(
        model_name=EMBED_MODEL_NAME,
        query_instruction="query: ",
        text_instruction="passage: "
    )

    splitter = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    logging.info(f"инициализация/подключение к chromadb в папке: {DB_DIR}")
    db_client = chromadb.PersistentClient(path=DB_DIR)

    existing_collections = [c.name for c in db_client.list_collections()]
    if COLLECTION_NAME in existing_collections:
        logging.info(f"Найдена существующая коллекция '{COLLECTION_NAME}'. Удаляю её для переиндексации...")
        db_client.delete_collection(name=COLLECTION_NAME)
        logging.info("Коллекция успешно удалена.")
    else:
        logging.info("Существующая коллекция не найдена, будет создана новая.")

    chroma_collection = db_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    logging.info("создание индекса... этот процесс может занять некоторое время.")
    index = VectorStoreIndex.from_documents(
        documents,
        transformations=[splitter],
        embed_model=embed_model,
        storage_context=storage_context,
        show_progress=True,
    )
    logging.info(f"индексация успешно завершена. коллекция '{COLLECTION_NAME}' готова к работе.")
    return index


if __name__ == "__main__":
    create_or_update_index()
