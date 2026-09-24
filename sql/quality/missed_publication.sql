-- error: пропущенная публикация
-- Источник сам говорит, какая публикация была предыдущей (поле PreviousDate)
-- Если её нет в сыром слое мы её пропустили. Ихзначельно хотел календарь выходных и праздников но он тут не нужен: его уже учёл сам ЦБ
-- Дату берём как её написал источник (первые 10 символов), без пересчёта часового пояса
-- Самую раннюю дату не проверяем: предыдущую и не загружали

SELECT
    r.rate_date,
    LEFT(r.payload->>'PreviousDate', 10)::date AS missing_date
FROM raw_rates r
WHERE r.rate_date > (SELECT MIN(rate_date) FROM raw_rates)
  AND NOT EXISTS (
      SELECT 1
      FROM raw_rates p
      WHERE p.rate_date = LEFT(r.payload->>'PreviousDate', 10)::date
  );
