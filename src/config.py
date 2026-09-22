"""место в проекте которое читает переменные окружения"""

import os

from dotenv import load_dotenv

load_dotenv()  # подхватывает .env, если он есть; в CI переменные приходят из окружения


def _require(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Не задана переменная {name}. Скопируй .env.example в .env и заполни его."
        )
    return value


PG_DSN = _require("PG_DSN")

# значния по дефолту
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", 10))
RETRIES = int(os.getenv("RETRIES", 3))
BACKOFF_BASE = float(os.getenv("BACKOFF_BASE", 2))
PAUSE_BETWEEN_DAYS = float(os.getenv("PAUSE_BETWEEN_DAYS", 0.3))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
