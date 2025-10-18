from python:3.12-slim

workdir /app

copy ./requirements.txt /app/
run pip install --no-cache-dir -r requirements.txt

copy ./app /app/app
copy ./indexer.py /app/indexer.py
copy ./knowledge_base /app/knowledge_base

cmd ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]