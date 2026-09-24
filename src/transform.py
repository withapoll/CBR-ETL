'''на входе словарь из fetch, на выходе список строк, готовых к вставке
    сюда потом буду тестить сохранённный jsonчик
'''

'''
псевдокод
берём данные из extract, вызовом данные аргументом
законяем это всё в словарь ( в список словарей)
пробегаемся по Valute, берём значения как данные а ключ для того чтобы их разложить по словарю
делаем форматирование date через datetime.fromisoformat("2026-09-11T11:30:00+03:00").date() 
создаём обработку пустого списка если он есть

далее пойдём взаимодействие данных с файлом load.py
'''

from datetime import datetime
from decimal import Decimal


def payload_date(payload):
    """Дата, на которую действует курс. Берём из ответа, а не из даты запроса."""
    return datetime.fromisoformat(payload["Date"]).date()


def transform(payload):
    """Превращаексм ответ API ЦБ в список словарей по одному на валюту."""
    if "Valute" not in payload:
        raise ValueError("В ответе нет ключа 'Valute': структура источника изменилась")

    valute = payload["Valute"]
    if not valute:
        return []

    rate_date = payload_date(payload)

    rows = []
    for info in valute.values():
        rows.append(
            {
                "rate_date": rate_date,
                "char_code": info["CharCode"],
                "name": info["Name"],
                "nominal": info["Nominal"],
                "value": Decimal(str(info["Value"])), # замена для теста  info["Value"]
            }
        )

    return rows


if __name__ == "__main__":
    from datetime import date

    from extract import fetch

    rows = transform(fetch(date(2026, 9, 11)))
    print(f"строк: {len(rows)}")
    for row in rows[:3]:
        print(row)
