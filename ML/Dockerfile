from python:3.12-slim

workdir /app

copy ./requirements.txt /app/
run pip install --no-cache-dir -r requirements.txt

copy ./app /app/app

copy ./entrypoint.sh /app/entrypoint.sh
run chmod +x /app/entrypoint.sh

entrypoint ["/app/entrypoint.sh"]

cmd ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]