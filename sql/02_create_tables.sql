drop table if exists raw.electricity_prices_long cascade;
drop table if exists features.electricity_price_features cascade;
drop table if exists forecast.model_metrics cascade;
drop table if exists forecast.predictions cascade;

create table raw.electricity_prices_long (
    date text not null,
    hour text not null,
    timestamp timestamp not null,
    country text not null,
    price double precision,
    primary key (country, date, hour)
);

create table features.electricity_price_features (
    date text not null,
    hour text not null,
    timestamp timestamp not null,
    country text not null,
    price double precision,
    hour_num integer,
    day_of_week integer,
    month integer,
    is_weekend integer,
    lag_1 double precision,
    lag_24 double precision,
    lag_168 double precision,
    rolling_mean_24 double precision,
    rolling_std_24 double precision,
    rolling_mean_168 double precision,
    rolling_std_168 double precision,
    target_t_plus_1 double precision,
    primary key (country, date, hour)
);

create table forecast.model_metrics (
    country text not null,
    model_name text not null,
    avg_mae double precision,
    avg_rmse double precision,
    fold_wins integer,
    evaluation_type text,
    primary key (country, model_name, evaluation_type)
);

create table forecast.predictions (
    date text not null,
    hour text not null,
    timestamp timestamp not null,
    country text not null,
    model_name text not null,
    actual_price double precision,
    predicted_price double precision,
    abs_error double precision,
    primary key (country, model_name, date, hour)
);

create index if not exists idx_raw_country_timestamp
on raw.electricity_prices_long (country, timestamp);

create index if not exists idx_features_country_timestamp
on features.electricity_price_features (country, timestamp);

create index if not exists idx_forecast_predictions_country_timestamp
on forecast.predictions (country, timestamp);