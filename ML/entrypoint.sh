#!/bin/bash
set -e

echo "Проверка наличия индекса ChromaDB..."

if [ ! -d "/app/db/chroma.sqlite3" ] && [ ! -f "/app/db/.initialized" ]; then
    echo "Индекс не найден. Запуск индексации базы знаний..."
    python /app/indexer.py

    # Создаём маркер успешной индексации
    touch /app/db/.initialized
    echo "Индексация завершена."
else
    echo "Индекс уже существует, пропускаю индексацию."
fi

echo "Запуск ML API сервиса..."
exec "$@"
