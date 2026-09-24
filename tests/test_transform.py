"""Модульные тесты разбора: без сети и без базы."""

from datetime import date
from decimal import Decimal

import pytest

from transform import payload_date, transform


def test_payload_date_does_not_shift_timezone():
    # 01:30 по Москве — это 22:30 предыдущего дня по UTC.
    # Пересчёт в UTC дал бы 18-е, а курс действует 19-го.
    assert payload_date({"Date": "2026-09-19T01:30:00+03:00"}) == date(2026, 9, 19)


def test_one_row_per_currency(payload):
    rows = transform(payload)

    assert len(rows) == 3
    assert {row["char_code"] for row in rows} == {"USD", "EUR", "JPY"}


def test_rate_date_comes_from_payload(payload):
    rows = transform(payload)

    assert all(row["rate_date"] == date(2026, 9, 19) for row in rows)


def test_nominal_100_value_is_kept_as_is(payload):
    jpy = next(row for row in transform(payload) if row["char_code"] == "JPY")

    assert jpy["nominal"] == 100
    assert jpy["value"] == Decimal("53.5948")  # цена 100 иен, а не одной — делит база
    assert isinstance(jpy["value"], Decimal)    # не float: точность, ради которой NUMERIC
    assert "value_per_1" not in jpy              # вычисляемую колонку считает база


def test_empty_valute_returns_empty_list(payload):
    payload["Valute"] = {}

    assert transform(payload) == []


def test_missing_valute_raises(payload):
    del payload["Valute"]

    with pytest.raises(ValueError):
        transform(payload)
