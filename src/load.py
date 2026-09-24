'''запись в базу: сырой ответ в raw_rates, разобранные строки в rates'''

'''
псевдокод
принимаем отформатированные данные из transform через аргументы + payload
первые на очереди raw_rates сырые данные, далее разбираем строки в rates
делаем транзацию если данные пришли все то Commit и завершаем, нет - Rollback
обновляем то, что может измениться в источнике: value, name, nominal. И loaded_at в бд
делаем связку с докер контейнером по портам и обратку для них
'''

import psycopg
from psycopg.types.json import Json

from config import PG_DSN

INSERT_RAW = """
    INSERT INTO raw_rates (rate_date, payload)
    VALUES (%(rate_date)s, %(payload)s)
    ON CONFLICT (rate_date) DO UPDATE
       SET payload = EXCLUDED.payload,
           loaded_at = NOW()
"""

INSERT_RATE = """
    INSERT INTO rates (rate_date, char_code, name, nominal, value)
    VALUES (%(rate_date)s, %(char_code)s, %(name)s, %(nominal)s, %(value)s)
    ON CONFLICT (rate_date, char_code) DO UPDATE
       SET name = EXCLUDED.name,
           nominal = EXCLUDED.nominal,
           value = EXCLUDED.value,
           loaded_at = NOW()
"""
# для теста ON CONFLICT (rate_date, char_code) DO NOTHTING

INSERT_LOG = """
    INSERT INTO load_log (rate_date, status, rows_loaded, message, started_at)
    VALUES (%(rate_date)s, %(status)s, %(rows_loaded)s, %(message)s, %(started_at)s)
"""


def load(rate_date, payload, rows, dsn=PG_DSN):
    """ сырой ответ и разобранные строки в одной транзакции

    на выоходле количество строк, записанных в rates
    """
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(INSERT_RAW, {"rate_date": rate_date, "payload": Json(payload)})
            if rows:
                cur.executemany(INSERT_RATE, rows)
    # выход из with: COMMIT, если исключения не было, иначе ROLLBACK
    return len(rows)


def log_run(rate_date, status, rows_loaded, message, started_at, dsn=PG_DSN):
    """пишем итог запуска в load_log

    потдельной, потому что откат неудачной загрузки не должен стирать запись о ней
    """
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                INSERT_LOG,
                {
                    "rate_date": rate_date,
                    "status": status,
                    "rows_loaded": rows_loaded,
                    "message": message,
                    "started_at": started_at,
                },
            )


if __name__ == "__main__":
    from datetime import date

    from extract import fetch
    from transform import payload_date, transform

    payload = fetch(date(2026, 9, 11))
    rows = transform(payload)
    loaded = load(payload_date(payload), payload, rows)
    print(f"записано строк: {loaded}")
