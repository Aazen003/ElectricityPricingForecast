import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine
from urllib.parse import quote_plus

st.set_page_config(page_title="Electricity Price Forecasting Dashboard", layout="wide")

@st.cache_resource
def get_engine():
    return create_engine(st.secrets["SUPABASE_DB_URL"])

@st.cache_data
def load_countries():
    query = """
    select distinct country
    from raw.electricity_prices_long
    order by country
    """
    return pd.read_sql(query, engine)["country"].tolist()

@st.cache_data
def load_best_models():
    query = """
    select *
    from analytics.best_model_by_country
    order by country
    """
    return pd.read_sql(query, engine)

@st.cache_data
def load_metrics(country):
    query = f"""
    select *
    from forecast.model_metrics
    where country = '{country}'
    order by avg_mae
    """
    return pd.read_sql(query, engine)

@st.cache_data
def load_price_history(country):
    query = f"""
    select timestamp, price, country
    from raw.electricity_prices_long
    where country = '{country}'
    order by timestamp, hour
    """
    df = pd.read_sql(query, engine)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

@st.cache_data
def load_predictions(country, model_name):
    query = f"""
    select timestamp, actual_price, predicted_price, abs_error, country, model_name
    from forecast.predictions
    where country = '{country}'
      and model_name = '{model_name}'
    order by timestamp, hour
    """
    df = pd.read_sql(query, engine)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

@st.cache_data
def load_hourly_profile(country):
    query = f"""
    select country, hour, avg_price
    from analytics.country_hourly_profile
    where country = '{country}'
    order by hour
    """
    return pd.read_sql(query, engine)

@st.cache_data
def load_weekday_profile(country):
    query = f"""
    select country, day_of_week, avg_price
    from analytics.country_weekday_profile
    where country = '{country}'
    order by day_of_week
    """
    return pd.read_sql(query, engine)

@st.cache_data
def load_monthly_profile(country):
    query = f"""
    select country, month, avg_price
    from analytics.country_monthly_profile
    where country = '{country}'
    order by month
    """
    return pd.read_sql(query, engine)

engine = get_engine()

best_models_df = load_best_models()
countries = load_countries()

st.sidebar.title("Controls")

selected_country = st.sidebar.selectbox("Select country", countries)

country_metrics = load_metrics(selected_country)

model_options = country_metrics["model_name"].tolist() if not country_metrics.empty else []
default_model_index = 0

selected_model = st.sidebar.selectbox(
    "Select model",
    model_options,
    index=default_model_index
)

history_df = load_price_history(selected_country)
pred_df = load_predictions(selected_country, selected_model) if selected_model else pd.DataFrame()
hourly_df = load_hourly_profile(selected_country)
weekday_df = load_weekday_profile(selected_country)
monthly_df = load_monthly_profile(selected_country)

best_model_row = best_models_df[best_models_df["country"] == selected_country]

st.title("Electricity Price Forecasting Dashboard")
st.caption("Multi-country electricity price analysis, forecasting, and model comparison")

st.subheader(f"{selected_country.title()} Overview")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

if not best_model_row.empty:
    kpi1.metric("Best model", best_model_row.iloc[0]["model_name"])
    kpi2.metric("Best avg MAE", f"{best_model_row.iloc[0]['avg_mae']:.2f}")
    kpi3.metric("Best avg RMSE", f"{best_model_row.iloc[0]['avg_rmse']:.2f}")
    kpi4.metric("Fold wins", int(best_model_row.iloc[0]["fold_wins"]))

st.subheader("Historical Prices")

fig_history = px.line(
    history_df,
    x="timestamp",
    y="price",
    title=f"Historical Electricity Prices - {selected_country.title()}"
)
st.plotly_chart(fig_history, use_container_width=True)

st.subheader("Actual vs Predicted")

if not pred_df.empty:
    fig_pred = px.line(
        pred_df,
        x="timestamp",
        y=["actual_price", "predicted_price"],
        title=f"Actual vs Predicted - {selected_country.title()} - {selected_model}"
    )
    st.plotly_chart(fig_pred, use_container_width=True)

    pred_kpi1, pred_kpi2 = st.columns(2)
    pred_kpi1.metric("Prediction rows", len(pred_df))
    pred_kpi2.metric("Average absolute error", f"{pred_df['abs_error'].mean():.2f}")

st.subheader("Model Metrics")
st.dataframe(country_metrics, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    fig_hourly = px.line(
        hourly_df,
        x="hour",
        y="avg_price",
        title=f"Average Price by Hour - {selected_country.title()}",
        markers=True
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

with col2:
    weekday_map = {
        0.0: "Mon", 1.0: "Tue", 2.0: "Wed", 3.0: "Thu",
        4.0: "Fri", 5.0: "Sat", 6.0: "Sun"
    }
    weekday_df["day_label"] = weekday_df["day_of_week"].map(weekday_map)

    fig_weekday = px.line(
        weekday_df,
        x="day_label",
        y="avg_price",
        title=f"Average Price by Weekday - {selected_country.title()}",
        markers=True
    )
    st.plotly_chart(fig_weekday, use_container_width=True)

st.subheader("Monthly Profile")

fig_monthly = px.line(
    monthly_df,
    x="month",
    y="avg_price",
    title=f"Average Price by Month - {selected_country.title()}",
    markers=True
)
st.plotly_chart(fig_monthly, use_container_width=True)

st.subheader("Best Model by Country")
st.dataframe(best_models_df, use_container_width=True)