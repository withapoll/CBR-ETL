-- Волатильность валют: стандартное отклонение изменений курса в процентах
-- Считаем по изменениям а не по самому курсу: сырой разброс зависит от масштаба (доллар ~84 ₽, иена ~0,55 ₽) а процентные изменения сравнимы между валютами
-- Зерно: одна строка на валюту за весь период.

WITH changes AS (
    -- логику сделал как в daily changes но без ROUND: округлять до агрегации нельзя ошибки округления попадут в результат
    SELECT
        char_code,
        (value_per_1 - LAG(value_per_1) OVER w) * 100.0
            / NULLIF(LAG(value_per_1) OVER w, 0) AS change_pct
    FROM rates
    WINDOW w AS (PARTITION BY char_code ORDER BY rate_date)
)
SELECT
    char_code,
    ROUND(STDDEV_SAMP(change_pct), 4) AS volatility_pct,
    COUNT(change_pct)                 AS n_changes  
FROM changes
GROUP BY char_code
HAVING COUNT(change_pct) >= 20
ORDER BY volatility_pct DESC;
