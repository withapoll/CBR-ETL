-- журнал проверок качества данных
-- Одна строка == одна проверка в одном запуске

CREATE TABLE dq_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    check_name  TEXT        NOT NULL,
    severity    TEXT        NOT NULL,
    violations  INT         NOT NULL,
    sample      JSONB,      -- первые несколько проблемных строк, чтобы не искать их заново
    CONSTRAINT chk_dq_severity CHECK (severity IN ('error', 'warning', 'info'))
);
