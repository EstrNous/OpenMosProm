import asyncio
import os
import random
import httpx
from datetime import datetime
from typing import List
import aiofiles


class UserSimulator:
    def __init__(self, requests_file: str, backend_url: str):
        self.requests = []
        self.requests_file = requests_file
        self.backend_url = backend_url
        self.is_running = False
        self.sent_count = 0
        self.interval = [float(os.getenv("INTERVAL_LOWER", 0.2)), float(os.getenv("INTERVAL_UPPER", 0.4))]

    async def load_requests(self):
        """Загрузка реальных обращений из файла"""
        async with aiofiles.open(self.requests_file, 'r', encoding='utf-8') as f:
            lines = await f.readlines()
            self.requests = [line.strip() for line in lines if line.strip()]

    async def start_simulation(self):
        """Запуск симуляции реальных пользователей"""
        await self.load_requests()
        self.is_running = True
        self.sent_count = 0

        print(f"Запуск симуляции с {len(self.requests)} обращениями")

        while self.is_running and self.requests:
            request_text = random.choice(self.requests)
            self.sent_count += 1

            await self.send_support_request(request_text)

            await asyncio.sleep(random.uniform(self.interval[0], self.interval[1]))

    async def send_support_request(self, message: str):
        """Отправка запроса в систему как реальный пользователь"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/support/process",
                    json={
                        "user_message": message,
                        "user_id": f"user_{random.randint(1000, 9999)}",
                        "timestamp": datetime.now().isoformat(),
                        "channel": "web"
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    print(f"Отправлено обращение {self.sent_count}: {message[:50]}...")
                else:
                    print(f"Ошибка отправки: {response.status_code}")

        except Exception as e:
            print(f"Ошибка при отправке запроса: {e}")

    def stop_simulation(self):
        self.is_running = False
        print(f"Симуляция остановлена. Всего отправлено: {self.sent_count}")
