import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

st.set_page_config(
    page_title="Electricity Price Forecasting Dashboard",
    layout="wide"
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stMetric"] {
            background-color: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            padding: 14px;
            border-radius: 14px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def style_line_chart(fig, x_title="", y_title="Price"):
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=55, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
        xaxis_title=x_title,
        yaxis_title=y_title,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.10)")
    return fig


engine = get_engine()

best_models_df = load_best_models()
all_metrics_df = load_all_metrics()
countries = load_countries()
latest_prices_df = load_latest_prices()

st.sidebar.title("Controls")

selected_country = st.sidebar.selectbox("Country", countries)

country_metrics = load_metrics(selected_country)
model_options = country_metrics["model_name"].tolist() if not country_metrics.empty else []

selected_model = st.sidebar.selectbox(
    "Model",
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
    "Historical date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

forecast_window = st.sidebar.selectbox(
    "Prediction window",
    ["Last 7 days", "Last 14 days", "Last 30 days", "Full selected range"],
    index=1
)

show_raw_table = st.sidebar.checkbox("Show data tables", value=False)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

if start_date and end_date:
    history_df = history_df[
        (history_df["timestamp"].dt.date >= start_date) &
        (history_df["timestamp"].dt.date <= end_date)
    ].copy()

pred_display_note = None

if not pred_df.empty:
    pred_min_date = pred_df["timestamp"].dt.date.min()
    pred_max_date = pred_df["timestamp"].dt.date.max()

    overlap_start = max(start_date, pred_min_date) if start_date else pred_min_date
    overlap_end = min(end_date, pred_max_date) if end_date else pred_max_date

    if overlap_start <= overlap_end:
        pred_df = pred_df[
            (pred_df["timestamp"].dt.date >= overlap_start) &
            (pred_df["timestamp"].dt.date <= overlap_end)
        ].copy()
        pred_display_note = (
            f"Showing prediction data from {overlap_start} to {overlap_end}. "
            f"Available prediction range for {selected_country.title()} is {pred_min_date} to {pred_max_date}."
        )
    else:
        pred_df = pred_df[
            (pred_df["timestamp"].dt.date >= pred_min_date) &
            (pred_df["timestamp"].dt.date <= pred_max_date)
        ].copy()
        pred_display_note = (
            f"Your selected historical date range has no prediction rows. "
            f"Showing the available prediction window instead: {pred_min_date} to {pred_max_date}."
        )

if not pred_df.empty:
    if forecast_window == "Last 7 days":
        pred_df = pred_df.tail(24 * 7).copy()
    elif forecast_window == "Last 14 days":
        pred_df = pred_df.tail(24 * 14).copy()
    elif forecast_window == "Last 30 days":
        pred_df = pred_df.tail(24 * 30).copy()

best_model_row = best_models_df[best_models_df["country"] == selected_country]

st.title("Electricity Price Forecasting Dashboard")
st.markdown(
    f"""
    This dashboard analyzes **hourly electricity prices** for six countries and compares forecasting models.
    For **{selected_country.title()}**, it shows historical behavior, recent forecast performance, and recurring patterns by hour, weekday, and month.
    """
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

if not best_model_row.empty:
    kpi1.metric("Best model", best_model_row.iloc[0]["model_name"])
    kpi2.metric("Average MAE", f"{best_model_row.iloc[0]['avg_mae']:.2f}")
    kpi3.metric("Average RMSE", f"{best_model_row.iloc[0]['avg_rmse']:.2f}")
    kpi4.metric("Fold wins", int(best_model_row.iloc[0]["fold_wins"]))

st.info(
    "How to read this dashboard: start with Overview for the big picture, use Forecast Performance to compare actual vs predicted prices, then use Patterns to understand when prices are usually high or low."
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Forecast Performance", "Patterns", "Model Comparison"]
)

with tab1:
    st.subheader(f"{selected_country.title()} overview")

    overview_col1, overview_col2 = st.columns([2, 1])

    with overview_col1:
        fig_history = go.Figure()
        fig_history.add_trace(
            go.Scatter(
                x=history_df["timestamp"],
                y=history_df["price"],
                mode="lines",
                name="Historical price",
                line=dict(width=1.5, color="#7cc0ff")
            )
        )
        fig_history.update_layout(title=f"Historical electricity prices - {selected_country.title()}")
        fig_history = style_line_chart(fig_history, x_title="Time")
        st.plotly_chart(
            fig_history,
            use_container_width=True,
            key=f"history_chart_{selected_country}_{start_date}_{end_date}"
        )

    with overview_col2:
        latest_country = latest_prices_df[latest_prices_df["country"] == selected_country].copy()
        if not latest_country.empty:
            latest_price = latest_country.iloc[0]["price"]
            latest_time = latest_country.iloc[0]["timestamp"]
            st.metric("Latest available price", f"{latest_price:.2f}")
            st.caption(f"Latest timestamp: {latest_time}")

        if not history_df.empty:
            st.metric("Selected rows", len(history_df))
            st.metric("Average price", f"{history_df['price'].mean():.2f}")
            st.metric("Peak price", f"{history_df['price'].max():.2f}")
            st.metric("Lowest price", f"{history_df['price'].min():.2f}")

    st.subheader("Best model by country")
    best_model_display = best_models_df.copy()
    best_model_display["country"] = best_model_display["country"].str.title()

    fig_best_mae = px.bar(
        best_model_display,
        x="country",
        y="avg_mae",
        color="model_name",
        title="Lowest average MAE by country"
    )
    fig_best_mae = style_line_chart(fig_best_mae, x_title="Country", y_title="Average MAE")
    st.plotly_chart(
        fig_best_mae,
        use_container_width=True,
        key="best_mae_chart_overview"
    )

    st.subheader("Latest price snapshot across countries")
    latest_prices_display = latest_prices_df.copy()
    latest_prices_display["country"] = latest_prices_display["country"].str.title()
    latest_prices_display = latest_prices_display[["country", "timestamp", "price"]]
    st.dataframe(latest_prices_display, use_container_width=True)

with tab2:
    st.subheader(f"Forecast performance - {selected_country.title()} - {selected_model}")

    if pred_display_note:
        st.caption(pred_display_note)

    if not pred_df.empty:
        pred_df = pred_df.sort_values("timestamp").copy()
        pred_df["rolling_abs_error_24"] = pred_df["abs_error"].rolling(24).mean()

        forecast_start = pred_df["timestamp"].min()

        fig_pred = go.Figure()
        fig_pred.add_trace(
            go.Scatter(
                x=pred_df["timestamp"],
                y=pred_df["actual_price"],
                mode="lines",
                name="Actual",
                line=dict(width=1.6, color="rgba(220,220,220,0.95)")
            )
        )
        fig_pred.add_trace(
            go.Scatter(
                x=pred_df["timestamp"],
                y=pred_df["predicted_price"],
                mode="lines",
                name="Predicted",
                line=dict(width=1.2, color="#1f8fff")
            )
        )
        fig_pred.add_vline(
            x=forecast_start,
            line_width=1,
            line_dash="dash",
            line_color="rgba(255,255,255,0.5)"
        )
        fig_pred.add_annotation(
            x=forecast_start,
            y=max(pred_df["actual_price"].max(), pred_df["predicted_price"].max()),
            text="Forecast window",
            showarrow=False,
            yshift=15,
            font=dict(size=11)
        )
        fig_pred.update_layout(
            title=f"Actual vs predicted prices - {selected_country.title()}",
        )
        fig_pred = style_line_chart(fig_pred, x_title="Time")
        st.plotly_chart(
            fig_pred,
            use_container_width=True,
            key=f"prediction_chart_{selected_country}_{selected_model}_{start_date}_{end_date}_{forecast_window}"
        )

        fc1, fc2, fc3 = st.columns(3)
        fc1.metric("Prediction rows", len(pred_df))
        fc2.metric("Average absolute error", f"{pred_df['abs_error'].mean():.2f}")
        fc3.metric("Max absolute error", f"{pred_df['abs_error'].max():.2f}")

        fig_error = go.Figure()
        fig_error.add_trace(
            go.Scatter(
                x=pred_df["timestamp"],
                y=pred_df["rolling_abs_error_24"],
                mode="lines",
                name="Rolling 24h absolute error",
                line=dict(width=1.8, color="#ff8c42")
            )
        )
        fig_error.update_layout(title="Rolling 24-hour forecast error")
        fig_error = style_line_chart(fig_error, x_title="Time", y_title="Absolute error")
        st.plotly_chart(
            fig_error,
            use_container_width=True,
            key=f"rolling_error_chart_{selected_country}_{selected_model}_{start_date}_{end_date}_{forecast_window}"
        )

        if show_raw_table:
            st.subheader("Prediction sample")
            st.dataframe(
                pred_df[["timestamp", "actual_price", "predicted_price", "abs_error"]].tail(100),
                use_container_width=True
            )
    else:
        st.info("No prediction data is available for the selected model.")

with tab3:
    st.subheader(f"Recurring price patterns - {selected_country.title()}")

    col1, col2 = st.columns(2)

    with col1:
        fig_hourly = go.Figure()
        fig_hourly.add_trace(
            go.Scatter(
                x=hourly_df["hour"],
                y=hourly_df["avg_price"],
                mode="lines+markers",
                name="Average price by hour",
                line=dict(width=2, color="#00c2ff"),
                marker=dict(size=5)
            )
        )
        fig_hourly.update_layout(title="Average price by hour")
        fig_hourly = style_line_chart(fig_hourly, x_title="Hour")
        st.plotly_chart(
            fig_hourly,
            use_container_width=True,
            key=f"hourly_profile_chart_{selected_country}"
        )

    with col2:
        weekday_map = {
            0.0: "Mon",
            1.0: "Tue",
            2.0: "Wed",
            3.0: "Thu",
            4.0: "Fri",
            5.0: "Sat",
            6.0: "Sun",
        }
        weekday_df = weekday_df.copy()
        weekday_df["day_label"] = weekday_df["day_of_week"].map(weekday_map)

        fig_weekday = go.Figure()
        fig_weekday.add_trace(
            go.Scatter(
                x=weekday_df["day_label"],
                y=weekday_df["avg_price"],
                mode="lines+markers",
                name="Average price by weekday",
                line=dict(width=2, color="#2bd67b"),
                marker=dict(size=6)
            )
        )
        fig_weekday.update_layout(title="Average price by weekday")
        fig_weekday = style_line_chart(fig_weekday, x_title="Weekday")
        st.plotly_chart(
            fig_weekday,
            use_container_width=True,
            key=f"weekday_profile_chart_{selected_country}"
        )

    fig_monthly = go.Figure()
    fig_monthly.add_trace(
        go.Scatter(
            x=monthly_df["month"],
            y=monthly_df["avg_price"],
            mode="lines+markers",
            name="Average price by month",
            line=dict(width=2, color="#b47cff"),
            marker=dict(size=7)
        )
    )
    fig_monthly.update_layout(title="Average price by month")
    fig_monthly = style_line_chart(fig_monthly, x_title="Month")
    st.plotly_chart(
        fig_monthly,
        use_container_width=True,
        key=f"monthly_profile_chart_{selected_country}"
    )

with tab4:
    st.subheader("Model comparison")

    st.markdown(f"### {selected_country.title()} model metrics")
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
            title="Best model average MAE by country"
        )
        fig_country_mae = style_line_chart(fig_country_mae, x_title="Country", y_title="Average MAE")
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
            title="Best model average RMSE by country"
        )
        fig_country_rmse = style_line_chart(fig_country_rmse, x_title="Country", y_title="Average RMSE")
        st.plotly_chart(
            fig_country_rmse,
            use_container_width=True,
            key="country_rmse_chart_tab4"
        )

    if show_raw_table:
        st.markdown("### Full metrics table")
        full_metrics_display = all_metrics_df.copy()
        full_metrics_display["country"] = full_metrics_display["country"].str.title()
        st.dataframe(full_metrics_display, use_container_width=True)