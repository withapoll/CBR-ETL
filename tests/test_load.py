"""Интеграционные тесты загрузки: идемпотентность живёт в базе, поэтому и проверяется с базой."""

from decimal import Decimal

import psycopg
from psycopg import sql

from load import load
from transform import payload_date, transform


def count_rows(dsn, table):
    # имя таблицы — это идентификатор, а не значение: %s для него не подходит,
    # поэтому sql.Identifier — он экранирует имя так же безопасно
    query = sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))
    with psycopg.connect(dsn) as conn:
        return conn.execute(query).fetchone()[0]


def test_loading_twice_creates_no_duplicates(db, payload):
    day = payload_date(payload)
    rows = transform(payload)

    load(day, payload, rows, dsn=db)
    load(day, payload, rows, dsn=db)

    assert count_rows(db, "raw_rates") == 1
    assert count_rows(db, "rates") == 3


def test_reload_picks_up_corrected_rate(db, payload):
    day = payload_date(payload)
    load(day, payload, transform(payload), dsn=db)

    payload["Valute"]["USD"]["Value"] = 99.9999  # ЦБ поправил курс задним числом
    load(day, payload, transform(payload), dsn=db)

    with psycopg.connect(db) as conn:
        value = conn.execute("SELECT value FROM rates WHERE char_code = 'USD'").fetchone()[0]
    assert value == Decimal("99.9999")  # DO UPDATE подтянул исправление


def test_value_per_1_is_computed_by_database(db, payload):
    load(payload_date(payload), payload, transform(payload), dsn=db)

    with psycopg.connect(db) as conn:
        per_1 = conn.execute(
            "SELECT value_per_1 FROM rates WHERE char_code = 'JPY'"
        ).fetchone()[0]
    assert per_1 == Decimal("0.535948")  # 53.5948 за 100 иен -> за одну
