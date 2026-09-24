-- info: ЦБ сменил номинал валюты
-- Само по себе не ошибка: value_per_1 делит на номинал и курс за единицу остаётся ровным 
-- Но событие стоит видеть: у гонконского доллара в июле номинал менялся три раза за неделю
-- Как и в rate_jump, смотрим только загруженное за последние сутки

SELECT char_code, rate_date, old_nominal, nominal AS new_nominal
FROM (
    SELECT
        char_code,
        rate_date,
        nominal,
        loaded_at,
        LAG(nominal) OVER (PARTITION BY char_code ORDER BY rate_date) AS old_nominal
    FROM rates
) t
WHERE old_nominal <> nominal
  AND loaded_at >= NOW() - INTERVAL '1 day';
