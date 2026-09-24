#основной файл которой соединяет работу load.py, extract.py & transform.py

'''
псевдокод main.py

main.py — точка входа, сам ничего не считает, только дёргает три модуля по порядку

аргументы командной строки (а не данные из модулей):
  без аргументов    -> сегодня
  --date 2026-09-11 -> одна конкретная дата
  --backfill 90     -> последние 90 дней, включая сегодня

один день:
1. засекаем started_at
2. fetch с повторами: 3 попытки, задержки 2 и 4 сек, повторяем только сеть и 5xx
3. вернулся None -> данных за дату нет (выходной ИЛИ праздник), пишем skipped и идём дальше
4. fetch упал совсем -> failed + текст ошибки
5. rate_date берём из payload, а не из запрошенной даты — ЦБ публикует курс на следующий рабочий день
6. transform -> строки, load(rate_date, payload, rows) одной транзакцией
7. упало на разборе или записи -> failed + текст ошибки
8. всё ок -> success + сколько строк
9. в load_log пишем всегда, отдельной транзакцией; если и она недоступна — пишем в консоль,
   исходную ошибку не прячем

бэкфилл:
  идём от старой даты к свежей, пауза 0.3 сек между запросами (вежливость к чужому API)
  упавшая дата не останавливает остальные, но общий итог становится неуспешным

код возврата процесса: 0 если всё обработано, 1 если был хоть один failed — чтобы планировщик видел
'''

import argparse
import logging
import sys
import time
from datetime import date, datetime, timedelta, timezone

import requests

from config import BACKOFF_BASE, LOG_LEVEL, PAUSE_BETWEEN_DAYS, RETRIES
from extract import fetch
from load import load, log_run
from quality import run_checks
from transform import payload_date, transform

log = logging.getLogger("cbr")


def safe_log_run(*args, **kwargs):
    """уходит load_log, не заслоняя исходную ошибку

    Если недоступнро то остаётся только лог в консоль, а исходная причина не теряется (записьв  журнал невозможно)
    """
    try:
        log_run(*args, **kwargs)
    except Exception as exc:
        log.error("не удалось записать в load_log: %s", exc)


def fetch_with_retries(day):
    """fetch с повторами.повторяем только сетевые ошибки и 5xx: 404 как было так и оставить?"""
    for attempt in range(1, RETRIES + 1):
        try:
            return fetch(day)
        except requests.exceptions.RequestException as exc:
            if attempt == RETRIES:
                raise
            delay = BACKOFF_BASE**attempt
            log.warning(
                "попытка %s из %s не удалась (%s), повтор через %s с",
                attempt, RETRIES, exc, delay,
            )
            time.sleep(delay)


def run_one(day=None):
    """Одна дата: extract -> transform -> load -> запись в load_log.

    True, если день обработан (загружен или пропущен по отсутствию данных)
    """
    started_at = datetime.now(timezone.utc)
    requested = day or date.today()

    try:
        payload = fetch_with_retries(day)
    except requests.exceptions.RequestException as exc:
        log.error("%s: источник недоступен: %s", requested, exc)
        safe_log_run(requested, "failed", 0, str(exc), started_at)
        return False

    if payload is None:
        log.info("%s: данных нет — нерабочий день", requested)
        safe_log_run(requested, "skipped", 0, "нет данных за дату", started_at)
        return True

    # дата берётся из ответа: ЦБ публикует курс на следующий рабочий день
    rate_date = payload_date(payload)

    try:
        rows = transform(payload)
        loaded = load(rate_date, payload, rows)
    except Exception as exc:
        log.exception("%s: загрузка не удалась", rate_date)
        safe_log_run(rate_date, "failed", 0, str(exc), started_at)
        return False

    log.info("%s: загружено строк: %s", rate_date, loaded)
    safe_log_run(rate_date, "success", loaded, None, started_at)
    return True


def run_backfill(days):
    """Последние N дней, включая сегодня, от старой даты к свежей."""
    today = date.today()
    all_ok = True
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        all_ok = run_one(day) and all_ok
        time.sleep(PAUSE_BETWEEN_DAYS)  #эт чтобы мне бан не дали на использщование api если так могут 
    return all_ok


def report_quality():
    """Проверки качества после загрузки

    false, если сработала хоть одна проверка уровня error
    warning и info только пишутся в лог: решение по ним принимает чел которые видит данные
    """
    try:
        results = run_checks()
    except Exception:
        log.exception("проверки качества не выполнились")
        return False

    ok = True
    for r in results:
        if r["violations"] == 0:
            continue
        message = "DQ %s: нарушений %s, пример: %s"
        args = (r["check_name"], r["violations"], r["sample"][:1])
        if r["severity"] == "error":
            log.error(message, *args)
            ok = False
        elif r["severity"] == "warning":
            log.warning(message, *args)
        else:
            log.info(message, *args)

    if ok:
        log.info("DQ: проверок уровня error не сработало")
    return ok


def parse_args():
    parser = argparse.ArgumentParser(description="Загрузка курсов валют ЦБ РФ")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--date", help="дата в формате YYYY-MM-DD, по умолчанию сегодня")
    group.add_argument(
        "--backfill",
        type=int,
        metavar="N",
        help="загрузить последние N дней, включая сегодня",
    )
    return parser.parse_args()


def main():
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    args = parse_args()

    if args.backfill:
        ok = run_backfill(args.backfill)
    elif args.date:
        ok = run_one(date.fromisoformat(args.date))
    else:
        ok = run_one()

    # проверки илут всегда даже если загрузка упала:такк покажут в каком состоянии данные
    dq_ok = report_quality()
    return 0 if ok and dq_ok else 1


if __name__ == "__main__":
    sys.exit(main())
