-- Изменение курса к предыдущей публикации, в процентах.
-- "Предыдущая" это предыдущая строка той же валюты а не календарное "вчера": после выходных вторник сравнивается с субботой.

SELECT
    char_code,
    rate_date,
    value_per_1,
    LAG(value_per_1) OVER w AS prev_value,
    ROUND(
        (value_per_1 - LAG(value_per_1) OVER w) * 100.0
        / NULLIF(LAG(value_per_1) OVER w, 0),
        3
    ) AS change_pct
FROM rates
WINDOW w AS (PARTITION BY char_code ORDER BY rate_date)
ORDER BY char_code, rate_date;
