create or replace view analytics.country_price_summary as
select
    country,
    count(*) as row_count,
    min(timestamp) as min_timestamp,
    max(timestamp) as max_timestamp,
    avg(price) as avg_price,
    min(price) as min_price,
    max(price) as max_price
from raw.electricity_prices_long
group by country;

create or replace view analytics.country_feature_summary as
select
    country,
    count(*) as row_count,
    min(timestamp) as min_timestamp,
    max(timestamp) as max_timestamp,
    avg(target_t_plus_1) as avg_target,
    min(target_t_plus_1) as min_target,
    max(target_t_plus_1) as max_target
from features.electricity_price_features
group by country;

create or replace view analytics.latest_prices as
select distinct on (country)
    country,
    date,
    hour,
    timestamp,
    price
from raw.electricity_prices_long
order by country, timestamp desc, hour desc;

create or replace view analytics.country_hourly_profile as
select
    country,
    hour,
    avg(price) as avg_price
from raw.electricity_prices_long
group by country, hour
order by country, hour;

create or replace view analytics.country_weekday_profile as
select
    country,
    extract(dow from timestamp) as day_of_week,
    avg(price) as avg_price
from raw.electricity_prices_long
group by country, extract(dow from timestamp)
order by country, day_of_week;

create or replace view analytics.country_monthly_profile as
select
    country,
    extract(month from timestamp) as month,
    avg(price) as avg_price
from raw.electricity_prices_long
group by country, extract(month from timestamp)
order by country, month;

create or replace view analytics.best_model_by_country as
select distinct on (country)
    country,
    model_name,
    avg_mae,
    avg_rmse,
    fold_wins,
    evaluation_type
from forecast.model_metrics
order by country, avg_mae asc;

create or replace view analytics.prediction_summary as
select
    country,
    model_name,
    count(*) as row_count,
    avg(abs_error) as avg_abs_error,
    min(timestamp) as min_timestamp,
    max(timestamp) as max_timestamp
from forecast.predictions
group by country, model_name;

create or replace view analytics.latest_prediction_snapshot as
select distinct on (country, model_name)
    country,
    model_name,
    date,
    hour,
    timestamp,
    actual_price,
    predicted_price,
    abs_error
from forecast.predictions
order by country, model_name, timestamp desc, hour desc;