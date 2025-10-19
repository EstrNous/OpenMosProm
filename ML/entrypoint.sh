#!/bin/bash
set -e

echo "Проверка наличия индекса ChromaDB..."

# Создаём директорию, если её нет
mkdir -p /app/db

if [ ! -f "/app/db/.initialized" ]; then
    echo "Индекс не найден. Запуск индексации базы знаний..."
    
    if python /app/indexer.py; then
        # Создаём маркер успешной индексации
        touch /app/db/.initialized
        echo "Индексация завершена успешно."
    else
        echo "ОШИБКА: Индексация не удалась!"
        exit 1
    fi
else
    echo "Индекс уже существует (найден файл .initialized), пропускаю индексацию."
fi

echo "Запуск ML API сервиса..."
exec "$@"
