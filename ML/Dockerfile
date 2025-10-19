FROM python:3.12-slim

WORKDIR /app

# Установка curl для healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app
COPY ./indexer.py /app/indexer.py
COPY ./knowledge_base /app/knowledge_base
COPY ./app/models/classifier.joblib /app/app/models/classifier.joblib
COPY ./entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
