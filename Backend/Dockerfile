FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app

# Запуск обеих команд через shell
CMD sh -c "python -m app.db.init_db && uvicorn app.main:app --host 0.0.0.0 --port 8000"