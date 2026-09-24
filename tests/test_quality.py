"""Интеграционные тесты проверок качества: сами проверки — это SQL, им нужна база."""

import copy

from load import load
from quality import run_checks
from transform import payload_date, transform


def violations(dsn):
    return {r["check_name"]: r["violations"] for r in run_checks(dsn=dsn)}


def load_payload(dsn, payload):
    load(payload_date(payload), payload, transform(payload), dsn=dsn)


def test_empty_database_fails_freshness(db):
    # без COALESCE пустая таблица дала бы MAX = NULL, и проверка молча прошла бы
    assert violations(db)["freshness"] == 1


def test_negative_rate_is_caught(db, payload):
    payload["Valute"]["USD"]["Value"] = -1
    load_payload(db, payload)

    assert violations(db)["non_positive"] == 1


def test_clean_data_has_no_hard_errors(db, payload):
    load_payload(db, payload)
    result = violations(db)

    assert result["non_positive"] == 0
    assert result["missed_publication"] == 0  # одна дата — она же самая ранняя
    assert result["currency_count"] == 0


def test_missed_publication_is_caught(db, payload):
    older = copy.deepcopy(payload)
    older["Date"] = "2026-09-16T11:30:00+03:00"
    older["PreviousDate"] = "2026-09-15T11:30:00+03:00"

    load_payload(db, older)    # 16-е — самая ранняя дата, её не проверяем
    load_payload(db, payload)  # 19-е, а источник говорит: предыдущая была 18-го

    assert violations(db)["missed_publication"] == 1
