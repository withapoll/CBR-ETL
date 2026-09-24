"""Модульные тесты повторов: fetch и sleep подменены, тест не ждёт реальных секунд."""

import pytest
import requests

import main


@pytest.fixture(autouse=True)
def fixed_retry_settings(monkeypatch):
    # тест не должен зависеть от того, что написано в чьём-то .env
    monkeypatch.setattr(main, "RETRIES", 3)
    monkeypatch.setattr(main, "BACKOFF_BASE", 2)


def test_network_blip_then_success(monkeypatch):
    calls = []

    def flaky_fetch(day):
        calls.append(day)
        if len(calls) == 1:
            raise requests.ConnectionError("сеть моргнула")
        return {"ok": True}

    # подменяем main.fetch, а не extract.fetch: main импортировал имя к себе,
    # и вызывает именно свою копию ссылки
    monkeypatch.setattr(main, "fetch", flaky_fetch)
    monkeypatch.setattr(main.time, "sleep", lambda seconds: None)

    assert main.fetch_with_retries(None) == {"ok": True}
    assert len(calls) == 2


def test_gives_up_after_all_attempts_with_growing_delays(monkeypatch):
    delays = []

    def broken_fetch(day):
        raise requests.ConnectionError("сети нет")

    monkeypatch.setattr(main, "fetch", broken_fetch)
    monkeypatch.setattr(main.time, "sleep", delays.append)  # не спим, а записываем

    with pytest.raises(requests.ConnectionError):
        main.fetch_with_retries(None)

    assert delays == [2, 4]  # три попытки, между ними две паузы, каждая вдвое длиннее
