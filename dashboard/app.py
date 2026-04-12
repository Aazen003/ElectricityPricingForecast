import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

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
def load_all_metrics():
    query = """
    select *
    from forecast.model_metrics
    order by country, avg_mae
    """
    return pd.read_sql(query, engine)


@st.cache_data
def load_price_history(country):
    query = f"""
    select timestamp, date, hour, price, country
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
    select timestamp, date, hour, actual_price, predicted_price, abs_error, country, model_name
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


@st.cache_data
def load_latest_prices():
    query = """
    select *
    from analytics.latest_prices
    order by country
    """
    df = pd.read_sql(query, engine)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


engine = get_engine()

best_models_df = load_best_models()
all_metrics_df = load_all_metrics()
countries = load_countries()
latest_prices_df = load_latest_prices()

st.sidebar.title("Controls")

selected_country = st.sidebar.selectbox("Select country", countries)

country_metrics = load_metrics(selected_country)
model_options = country_metrics["model_name"].tolist() if not country_metrics.empty else []

selected_model = st.sidebar.selectbox(
    "Select model",
    model_options,
    index=0 if model_options else None
)

history_df = load_price_history(selected_country)
pred_df = load_predictions(selected_country, selected_model) if selected_model else pd.DataFrame()
hourly_df = load_hourly_profile(selected_country)
weekday_df = load_weekday_profile(selected_country)
monthly_df = load_monthly_profile(selected_country)

if not history_df.empty:
    min_date = history_df["timestamp"].dt.date.min()
    max_date = history_df["timestamp"].dt.date.max()
else:
    min_date = None
    max_date = None

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

if start_date and end_date:
    history_df = history_df[
        (history_df["timestamp"].dt.date >= start_date) &
        (history_df["timestamp"].dt.date <= end_date)
    ].copy()

    if not pred_df.empty:
        pred_df = pred_df[
            (pred_df["timestamp"].dt.date >= start_date) &
            (pred_df["timestamp"].dt.date <= end_date)
        ].copy()

best_model_row = best_models_df[best_models_df["country"] == selected_country]

st.title("Electricity Price Forecasting Dashboard")
st.caption("Supabase + SQL + forecasting models + multi-country dashboard")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

if not best_model_row.empty:
    kpi1.metric("Best model", best_model_row.iloc[0]["model_name"])
    kpi2.metric("Best avg MAE", f"{best_model_row.iloc[0]['avg_mae']:.2f}")
    kpi3.metric("Best avg RMSE", f"{best_model_row.iloc[0]['avg_rmse']:.2f}")
    kpi4.metric("Fold wins", int(best_model_row.iloc[0]["fold_wins"]))

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Predictions", "Profiles", "Model Comparison"])

with tab1:
    st.subheader(f"{selected_country.title()} Overview")

    fig_history = px.line(
        history_df,
        x="timestamp",
        y="price",
        title=f"Historical Electricity Prices - {selected_country.title()}"
    )
    st.plotly_chart(
        fig_history,
        use_container_width=True,
        key=f"history_chart_{selected_country}_{start_date}_{end_date}"
    )

    st.subheader("Latest Price Snapshot Across Countries")
    latest_prices_display = latest_prices_df.copy()
    latest_prices_display["country"] = latest_prices_display["country"].str.title()
    st.dataframe(latest_prices_display, use_container_width=True)

    best_model_display = best_models_df.copy()
    best_model_display["country"] = best_model_display["country"].str.title()

    fig_best_mae = px.bar(
        best_model_display,
        x="country",
        y="avg_mae",
        color="model_name",
        title="Best Model MAE by Country"
    )
    st.plotly_chart(
        fig_best_mae,
        use_container_width=True,
        key="best_mae_chart_overview"
    )

with tab2:
    st.subheader(f"Predictions - {selected_country.title()} - {selected_model}")

    if not pred_df.empty:
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=pred_df["timestamp"],
            y=pred_df["actual_price"],
            mode="lines",
            name="Actual"
        ))
        fig_pred.add_trace(go.Scatter(
            x=pred_df["timestamp"],
            y=pred_df["predicted_price"],
            mode="lines",
            name="Predicted"
        ))
        fig_pred.update_layout(
            title=f"Actual vs Predicted - {selected_country.title()} - {selected_model}",
            xaxis_title="Timestamp",
            yaxis_title="Price"
        )
        st.plotly_chart(
            fig_pred,
            use_container_width=True,
            key=f"prediction_chart_{selected_country}_{selected_model}_{start_date}_{end_date}"
        )

        pred_kpi1, pred_kpi2 = st.columns(2)
        pred_kpi1.metric("Prediction rows", len(pred_df))
        pred_kpi2.metric("Average absolute error", f"{pred_df['abs_error'].mean():.2f}")

        pred_df = pred_df.sort_values("timestamp").copy()
        pred_df["rolling_abs_error_24"] = pred_df["abs_error"].rolling(24).mean()

        fig_error = px.line(
            pred_df,
            x="timestamp",
            y="rolling_abs_error_24",
            title="Rolling 24-Hour Absolute Error"
        )
        st.plotly_chart(
            fig_error,
            use_container_width=True,
            key=f"rolling_error_chart_{selected_country}_{selected_model}_{start_date}_{end_date}"
        )

        st.subheader("Prediction Sample")
        st.dataframe(pred_df.tail(100), use_container_width=True)
    else:
        st.info("No prediction data available for the selected filters.")

with tab3:
    st.subheader(f"Price Profiles - {selected_country.title()}")

    col1, col2 = st.columns(2)

    with col1:
        fig_hourly = px.line(
            hourly_df,
            x="hour",
            y="avg_price",
            title="Average Price by Hour",
            markers=True
        )
        st.plotly_chart(
            fig_hourly,
            use_container_width=True,
            key=f"hourly_profile_chart_{selected_country}"
        )

    with col2:
        weekday_map = {
            0.0: "Mon", 1.0: "Tue", 2.0: "Wed", 3.0: "Thu",
            4.0: "Fri", 5.0: "Sat", 6.0: "Sun"
        }
        weekday_df = weekday_df.copy()
        weekday_df["day_label"] = weekday_df["day_of_week"].map(weekday_map)

        fig_weekday = px.line(
            weekday_df,
            x="day_label",
            y="avg_price",
            title="Average Price by Weekday",
            markers=True
        )
        st.plotly_chart(
            fig_weekday,
            use_container_width=True,
            key=f"weekday_profile_chart_{selected_country}"
        )

    fig_monthly = px.line(
        monthly_df,
        x="month",
        y="avg_price",
        title="Average Price by Month",
        markers=True
    )
    st.plotly_chart(
        fig_monthly,
        use_container_width=True,
        key=f"monthly_profile_chart_{selected_country}"
    )

with tab4:
    st.subheader("Model Comparison")

    st.markdown(f"### {selected_country.title()} Metrics")
    st.dataframe(country_metrics, use_container_width=True)

    comparison_df = best_models_df.copy()
    comparison_df["country"] = comparison_df["country"].str.title()

    col1, col2 = st.columns(2)

    with col1:
        fig_country_mae = px.bar(
            comparison_df,
            x="country",
            y="avg_mae",
            color="model_name",
            title="Best Model MAE by Country"
        )
        st.plotly_chart(
            fig_country_mae,
            use_container_width=True,
            key="country_mae_chart_tab4"
        )

    with col2:
        fig_country_rmse = px.bar(
            comparison_df,
            x="country",
            y="avg_rmse",
            color="model_name",
            title="Best Model RMSE by Country"
        )
        st.plotly_chart(
            fig_country_rmse,
            use_container_width=True,
            key="country_rmse_chart_tab4"
        )

    st.markdown("### Full Metrics Table")
    full_metrics_display = all_metrics_df.copy()
    full_metrics_display["country"] = full_metrics_display["country"].str.title()
    st.dataframe(full_metrics_display, use_container_width=True)