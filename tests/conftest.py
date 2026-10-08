"""Общие фикстуры: pytest подхватывает этот файл сам, импортировать его не нужно."""

import json
import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

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


def _ensure_database(dsn, db_name):
    """Создаёт тестовую базу, если её ещё нет.

    На чистой машине её никто не создавал. Подключаемся к служебной базе postgres
    на том же сервере: создать базу, находясь в ней самой, нельзя.
    """
    admin_dsn = make_conninfo(dsn, dbname="postgres")
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)
        ).fetchone()
        if not exists:
            # имя базы — идентификатор, поэтому sql.Identifier, а не %s
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))


@pytest.fixture(scope="session")
def test_dsn():
    """Тестовая база со свежей схемой один раз на весь прогон."""
    dsn = os.getenv("TEST_PG_DSN")
    if not dsn:
        # локально пропуск удобен, а в CI он дал бы зелёную галочку без проверки главного
        if os.getenv("CI"):
            pytest.fail("В CI должен быть задан TEST_PG_DSN")
        pytest.skip("TEST_PG_DSN не задан — интеграционные тесты пропущены")

    # тесты сносят схему целиком; до рабочей базы они не должны дотянуться ни при каких условиях.
    # Проверяем именно имя базы, а не всю строку: слово test могло оказаться в пароле или хосте
    db_name = conninfo_to_dict(dsn)["dbname"]
    assert "test" in db_name, "TEST_PG_DSN должен указывать на тестовую базу"

    _ensure_database(dsn, db_name)

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
