create table raw_rates (
    id bigint generated always as identity primary key,
    rate_date date unique not null, 
    payload jsonb not null,
    loaded_at timestamptz not null default now()
);

create table rates (
    rate_date date not null,
    char_code text not null, 
    name text not null, 
    nominal int not null, 
    value numeric(18, 6) not null,
    value_per_1 numeric(18,6) generated always as (value / nominal) stored not null, 
    loaded_at timestamptz not null default now(),
    constraint pk_rates primary key (rate_date, char_code)
);

create table load_log (
    id bigint generated always as identity primary key,
    rate_date date not null, 
    status text not null, 
    constraint chk_status check  (status in ('success', 'failed', 'skipped')),
    rows_loaded int not null default 0,
    message text,
    started_at timestamptz not null,
    finished_at timestamptz not null default now()
);

create index idx_rates_code_date on rates(char_code, rate_date);