import requests
from datetime import date

from config import HTTP_TIMEOUT

BASE_URL = "https://www.cbr-xml-daily.ru"


def fetch(day=None):
    if day is None:
        url = f"{BASE_URL}/daily_json.js"
    else:
        url = f"{BASE_URL}/archive/{day.strftime("%Y/%m/%d")}/daily_json.js"

    resp = requests.get(url, timeout=HTTP_TIMEOUT)

    if resp.status_code == 404:
        return None

    resp.raise_for_status()
    return resp.json()   


if __name__ == "__main__":
    '''tests '''
    print(fetch(date(2026, 9, 11)))  #пятиница
    print(fetch(date(2026, 9, 13)))  #воскресение
    print(fetch())                    #сегодня 