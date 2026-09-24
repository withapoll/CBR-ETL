"""Модульные тесты fetch: сеть подменена, проверяем реакцию на ответы, а не сам ЦБ."""

from datetime import date

import pytest
import requests

import extract


class FakeResponse:
    """Притворяется ответом requests: только то, чем пользуется fetch."""

    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def fake_get(status_code, data=None, seen_urls=None):
    """Фальшивый requests.get: запоминает адрес и возвращает заготовленный ответ."""

    def _get(url, timeout):
        if seen_urls is not None:
            seen_urls.append(url)
        return FakeResponse(status_code, data)

    return _get


def test_404_means_no_data(monkeypatch):
    monkeypatch.setattr(extract.requests, "get", fake_get(404))

    assert extract.fetch(date(2026, 9, 13)) is None


def test_server_error_raises(monkeypatch):
    monkeypatch.setattr(extract.requests, "get", fake_get(500))

    with pytest.raises(requests.HTTPError):
        extract.fetch(date(2026, 9, 11))


def test_archive_url_has_leading_zeros(monkeypatch):
    seen = []
    monkeypatch.setattr(extract.requests, "get", fake_get(200, {}, seen))

    extract.fetch(date(2026, 7, 3))

    assert seen == ["https://www.cbr-xml-daily.ru/archive/2026/07/03/daily_json.js"]


def test_no_date_uses_daily_url(monkeypatch):
    seen = []
    monkeypatch.setattr(extract.requests, "get", fake_get(200, {}, seen))

    extract.fetch()

    assert seen == ["https://www.cbr-xml-daily.ru/daily_json.js"]
