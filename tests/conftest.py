"""Общие фикстуры: pytest подхватывает этот файл сам, импортировать его не нужно."""

import json
import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

# брутфорс что .env подхватит какой-нибудь импортированный модуль
load_dotenv()

TESTS_DIR = Path(__file__).resolve().parent
MIGRATIONS = TESTS_DIR.parent / "sql" / "migrations"


@pytest.fixture
def payload():
    """Настоящий ответ ЦБ за 19.09.2026, урезанный до трёх валют.

    Читается заново для каждого теста: тесты его меняют и не должны мешать друг другу.
    """
    text = (TESTS_DIR / "fixtures" / "daily_sample.json").read_text(encoding="utf-8")
    return json.loads(text)


@pytest.fixture(scope="session")
def test_dsn():
    """Тестовая база со свежей схемой один раз на весь прогон."""
    dsn = os.getenv("TEST_PG_DSN")
    if not dsn:
        # локально пропуск удобен, а в CI он дал бы зелёную галочку без проверки главного
        if os.getenv("CI"):
            pytest.fail("В CI должен быть задан TEST_PG_DSN")
        pytest.skip("TEST_PG_DSN не задан — интеграционные тесты пропущены")

    # тесты сносят схему целиком; до рабочей базы они не должны дотянуться ни при каких условиях
    assert "test" in dsn, "TEST_PG_DSN должен указывать на тестовую базу"

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            conn.execute(migration.read_text(encoding="utf-8"))
    return dsn


@pytest.fixture
def db(test_dsn):
    """Пустые таблицы перед каждым интеграционным тестом."""
    with psycopg.connect(test_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE raw_rates, rates, load_log, dq_log RESTART IDENTITY")
    return test_dsn
