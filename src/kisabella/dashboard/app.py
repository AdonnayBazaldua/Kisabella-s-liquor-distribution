"""Dashboard de analytics Kisabella's LLC.

Ejecutar: streamlit run src/kisabella/dashboard/app.py
"""
import altair as alt
import duckdb
import streamlit as st

from kisabella import config
from kisabella.dashboard import queries

st.set_page_config(page_title="Kisabella's LLC", layout="wide")

# Fira Sans para texto UI, Fira Code para tablas y métricas numéricas (cifras tabulares).
st.markdown(
    "<link href='https://fonts.googleapis.com/css2?family=Fira+Code:wght@500&"
    "family=Fira+Sans:wght@400;500;600;700&display=swap' rel='stylesheet'>"
    "<style>"
    "html, body, [class*='st-'] { font-family: 'Fira Sans', sans-serif; }"
    "[data-testid='stMetricValue'], [data-testid='stDataFrame'] { "
    "font-family: 'Fira Code', monospace; font-variant-numeric: tabular-nums; }"
    "</style>",
    unsafe_allow_html=True,
)


@st.cache_resource
def _open_db():
    if not config.WAREHOUSE_PATH.exists():
        st.error(f"Warehouse no encontrado en {config.WAREHOUSE_PATH}. "
                 "Corre `python -m kisabella.pipeline` primero.")
        st.stop()
    return duckdb.connect(str(config.WAREHOUSE_PATH), read_only=True)


def _render_top10(con, by, rank, title, value_col, value_label, store_filter, date_range):
    st.subheader(title)
    df = queries.top10(con, by=by, rank=rank, store_filter=store_filter, date_range=date_range)
    if df.is_empty():
        st.info("Sin datos para los filtros seleccionados.")
        return
    st.dataframe(df.drop("group_key"), use_container_width=True, hide_index=True)
    chart = (
        alt.Chart(df.to_pandas())
        .mark_bar(color="#1E40AF")
        .encode(
            x=alt.X(f"{value_col}:Q", title=value_label),
            y=alt.Y("group_label:N", sort="-x", title=None),
        )
        .properties(height=320)
    )
    st.altair_chart(chart, use_container_width=True)


con = _open_db()

# Sidebar: filtros + resumen de KPIs
st.sidebar.title("Kisabella's LLC")
st.sidebar.caption("Analytics 2016 — Top SKUs y Vendors por Profit y Margin")

stores = queries.get_store_options(con)
store_labels = {r["store_id"]: f"{r['store_id']} - {r['city']}" for r in stores.to_dicts()}
selected_stores = st.sidebar.multiselect(
    "Tiendas",
    options=stores["store_id"].to_list(),
    format_func=lambda s: store_labels[s],
    placeholder="Todas",
)
store_filter = selected_stores or None

lo, hi = queries.get_date_bounds(con)
selected_range = st.sidebar.date_input(
    "Rango de fechas", value=(lo, hi), min_value=lo, max_value=hi
)
date_range = (
    selected_range
    if isinstance(selected_range, tuple) and len(selected_range) == 2
    else None
)

m = queries.summary_metrics(con, store_filter, date_range)
st.sidebar.divider()
st.sidebar.metric("Revenue neto", f"${m['total_revenue_net']:,.0f}")
st.sidebar.metric("Profit neto", f"${m['total_profit_net']:,.0f}")
st.sidebar.caption(
    f"Devoluciones: {m['n_returns']:,}  -  "
    f"Anomalias excluidas: {m['n_anomalies']:,}  -  "
    f"Sin costo derivable: {m['n_cost_missing']:,}"
)

# Cuerpo
st.title("Top 10 mas rentables")
st.caption(
    "Metrica primaria: profit neto (revenue - ExciseTax - costo). "
    "Margen ponderado por revenue."
)

tab_products, tab_vendors = st.tabs(["Productos (SKU)", "Marcas (Vendor)"])

with tab_products:
    c1, c2 = st.columns(2)
    with c1:
        _render_top10(con, "product", "profit", "Top 10 por Profit$ neto",
                      "profit_net", "Profit neto ($)", store_filter, date_range)
    with c2:
        _render_top10(con, "product", "margin", "Top 10 por Margin% neto",
                      "margin_net_pct", "Margen neto (%)", store_filter, date_range)

with tab_vendors:
    c1, c2 = st.columns(2)
    with c1:
        _render_top10(con, "vendor", "profit", "Top 10 por Profit$ neto",
                      "profit_net", "Profit neto ($)", store_filter, date_range)
    with c2:
        _render_top10(con, "vendor", "margin", "Top 10 por Margin% neto",
                      "margin_net_pct", "Margen neto (%)", store_filter, date_range)
