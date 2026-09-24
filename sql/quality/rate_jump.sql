-- warning: курс за единицу изменился больше чем на 20% к предыдущей публикации
-- Может быть реальным событием (девальвация) те может ошибкой источника. пусть решает чел который видит данные
-- Смотрим на value_per_1: смена номинала сама по себе скачка не даёт пример из данных цб 
--гонконгский доллар: номинал прыгал три раза за неделю (10 → 1 → 10 → 1) а скачков курса у него нет
-- Проверяем только то, что загружено за последние сутки. Иначе одна старая аномалия будет кричать в каждом запуске и на предупреждения перестанут смотреть
-- loaded_at обновляется при перезагрузке поэтому бэкфилл тоже попадает в проверку
-- LAG считается по всей истории, а фильтр снаружи: тк предыдущая строка может быть старой

SELECT char_code, rate_date, prev_value, value_per_1, change_pct
FROM (
    SELECT
        char_code,
        rate_date,
        value_per_1,
        loaded_at,
        LAG(value_per_1) OVER w AS prev_value,
        ROUND(
            (value_per_1 - LAG(value_per_1) OVER w) * 100.0
            / NULLIF(LAG(value_per_1) OVER w, 0),
            2
        ) AS change_pct
    FROM rates
    WINDOW w AS (PARTITION BY char_code ORDER BY rate_date)
) t
WHERE ABS(change_pct) > 20
  AND loaded_at >= NOW() - INTERVAL '1 day';
