-- error: в дате заметно меньше валют, чем обычно — источник или разбор отдали неполный ответ.
-- «Обычно» — медиана по всей истории, порог — 90% от неё.
-- Медиана, а не среднее: одна битая дата не должна сдвигать саму норму.

WITH per_date AS (
    SELECT rate_date, COUNT(*) AS n_currencies
    FROM rates
    GROUP BY rate_date
),
typical AS (
    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY n_currencies) AS median_n
    FROM per_date
)
SELECT p.rate_date, p.n_currencies, t.median_n
FROM per_date p
CROSS JOIN typical t
WHERE p.n_currencies < 0.9 * t.median_n;
