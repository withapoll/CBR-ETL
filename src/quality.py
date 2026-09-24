"""Проверки качества данных.

Каждая проверкаЖ sql-файл в sql/quality который возвращает проблемные строки
0 строк то проверка пройдена. итог каждой проверки пишется в dq_log
"""

import json
from functools import partial
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from config import PG_DSN

QUALITY_DIR = Path(__file__).resolve().parent.parent / "sql" / "quality"

# имя файла -> левел проблемы; порядок словаря = порядок запуска
CHECKS = {
    "non_positive": "error",
    "missed_publication": "error",
    "freshness": "error",
    "currency_count": "error",
    "rate_jump": "warning",
    "nominal_change": "info",
}

SAMPLE_SIZE = 5  # сколько проблемных строк сохранять в dq_log для разбора

INSERT_DQ = """
    INSERT INTO dq_log (check_name, severity, violations, sample)
    VALUES (%(check_name)s, %(severity)s, %(violations)s, %(sample)s)
"""

# даты и Decimal в JSON не сериализуются сами превращаем их в строки
_dumps = partial(json.dumps, default=str, ensure_ascii=False)


def run_checks(dsn=PG_DSN):
    """гоняем все проверки, пишем итоги в dq_log и ретёрним их списком."""
    results = []
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for name, severity in CHECKS.items():
                sql = (QUALITY_DIR / f"{name}.sql").read_text(encoding="utf-8")
                cur.execute(sql)
                rows = cur.fetchall()
                sample = rows[:SAMPLE_SIZE]

                cur.execute(
                    INSERT_DQ,
                    {
                        "check_name": name,
                        "severity": severity,
                        "violations": len(rows),
                        "sample": Json(sample, dumps=_dumps) if rows else None,
                    },
                )
                results.append(
                    {
                        "check_name": name,
                        "severity": severity,
                        "violations": len(rows),
                        "sample": sample,
                    }
                )
    return results


if __name__ == "__main__":
    for r in run_checks():
        status = "OK" if r["violations"] == 0 else f"{r['violations']} нарушений"
        print(f"[{r['severity']:>7}] {r['check_name']:<20} {status}")
        for row in r["sample"]:
            print(f"          {row}")
