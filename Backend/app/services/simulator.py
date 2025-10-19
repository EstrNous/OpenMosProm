# app/services/simulator.py
import asyncio
import os
import random
import httpx
from datetime import datetime
from typing import List
import aiofiles
import logging

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger("user-simulator")
if not logger.handlers:
    import sys
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(stream=sys.stdout, level=log_level,
                        format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

class UserSimulator:
    def __init__(self, requests_file: str, backend_url: str, min_interval: float = 0.5, max_interval: float = 2.0):
        """
        requests_file: путь к файлу с примерами обращений (одна строка = одно обращение)
        backend_url: базовый URL backend (например http://backend:8000)
        min_interval/max_interval: пауза между отправками
        max_requests: опциональный предел на количество отправок (None — бесконечно, пока есть lines)
        """
        self.requests: List[str] = []
        self.requests_file = requests_file
        self.backend_url = backend_url.rstrip("/")
        self.is_running = False
        self.sent_count = 0
        self.min_interval = float(os.getenv("INTERVAL_LOWER", min_interval))
        self.max_interval = float(os.getenv("INTERVAL_UPPER", max_interval))

        logger.info("UserSimulator init: requests_file=%s backend_url=%s interval=[%s, %s]",
                    self.requests_file, self.backend_url, self.min_interval, self.max_interval)

    async def load_requests(self):
        """Загрузка реальных обращений из файла"""
        try:
            async with aiofiles.open(self.requests_file, 'r', encoding='utf-8') as f:
                lines = await f.readlines()
                self.requests = [line.strip() for line in lines if line.strip()]
                logger.info("Loaded %d requests from %s", len(self.requests), self.requests_file)
        except FileNotFoundError:
            logger.error("Requests file not found: %s", self.requests_file)
            self.requests = []
        except Exception as e:
            logger.exception("Failed to load requests file %s: %s", self.requests_file, e)
            self.requests = []

    async def start_simulation(self):
        """Запуск симуляции реальных пользователей"""
        await self.load_requests()
        if not self.requests:
            logger.warning("No requests to simulate; aborting simulation start.")
            return

        self.is_running = True
        self.sent_count = 0
        start_time = datetime.now()
        logger.info("Starting simulation at %s (total_requests=%d)", start_time.isoformat(), len(self.requests))

        try:
            while self.is_running and self.requests:
                request_text = self.requests.pop(random.randrange(len(self.requests)))
                self.sent_count += 1
                seq_no = self.sent_count

                # отправляем, не блокируя основной цикл
                try:
                    await self.send_support_request(seq_no, request_text)
                except Exception:
                    logger.exception("Unexpected error while sending request #%s", seq_no)

                # sleep random interval
                sleep_for = random.uniform(self.min_interval, self.max_interval)
                logger.debug("Sleeping for %.3fs before next request (seq=%s).", sleep_for, seq_no)
                await asyncio.sleep(sleep_for)

        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info("Simulation stopped. total_sent=%d elapsed_seconds=%.1f", self.sent_count, elapsed)
            self.is_running = False

    async def send_support_request(self, seq_no: int, message: str):
        """Отправка запроса в систему как реальный пользователь"""
        trimmed = message if len(message) <= 300 else (message[:300] + "...")
        payload = {
            "user_message": message,
            "user_id": f"user_{random.randint(1000, 9999)}",
            "timestamp": datetime.utcnow().isoformat(),
            "channel": "web"
        }

        url = f"{self.backend_url}/support/process"
        logger.debug("Sending request #%s to %s: %s", seq_no, url, trimmed)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
                status = response.status_code
                if status == 200 or status == 201:
                    logger.info("Sent request #%s OK (status=%s) payload_preview=%s", seq_no, status, trimmed)
                else:
                    # логируем тело ответа (обрезанное) для диагностики
                    content = (response.text[:500] + '...') if response.text and len(response.text) > 500 else response.text
                    logger.warning("Send failed (seq=%s) status=%s response=%s", seq_no, status, content)
        except httpx.RequestError as e:
            logger.warning("HTTP error while sending request #%s to %s: %s", seq_no, url, e)
        except Exception as e:
            logger.exception("Unexpected error in send_support_request (seq=%s): %s", seq_no, e)

    def stop_simulation(self):
        self.is_running = False
        logger.info("Simulation stopping requested. Sent so far: %d", self.sent_count)
