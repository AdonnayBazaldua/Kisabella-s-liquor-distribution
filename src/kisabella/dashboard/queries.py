"""Queries DuckDB parametrizadas para el dashboard Streamlit."""
from datetime import date
from typing import Literal
import duckdb
import polars as pl


def _filter_clause(
    store_filter: list[int] | None,
    date_range: tuple[date, date] | None,
    *,
    exclude_flagged: bool = True,
) -> tuple[str, list]:
    where: list[str] = []
    if exclude_flagged:
        where += ["NOT f.is_anomalous_zero_price", "NOT f.is_cost_missing"]
    params: list = []
    if store_filter:
        placeholders = ",".join(["?"] * len(store_filter))
        where.append(f"f.store_fk IN ({placeholders})")
        params.extend(store_filter)
    if date_range:
        where.append("d.date BETWEEN ? AND ?")
        params.extend([date_range[0], date_range[1]])
    return (" AND ".join(where) if where else "TRUE"), params


_GROUP_SPEC = {
    "product": {"dim": "dim_product", "fk": "product_fk", "key": "brand", "label": "description"},
    "vendor":  {"dim": "dim_vendor",  "fk": "vendor_fk",  "key": "vendor_no", "label": "vendor_name"},
}

_ORDER_BY = {
    "profit": "profit_net DESC",
    "margin": "margin_net_pct DESC NULLS LAST",
}


def top10(
    con: duckdb.DuckDBPyConnection,
    by: Literal["product", "vendor"],
    rank: Literal["profit", "margin"],
    store_filter: list[int] | None = None,
    date_range: tuple[date, date] | None = None,
) -> pl.DataFrame:
    g = _GROUP_SPEC[by]
    where, params = _filter_clause(store_filter, date_range, exclude_flagged=True)
    return con.execute(
        f"""
        SELECT
            g.{g['key']} AS group_key,
            g.{g['label']} AS group_label,
            SUM(f.profit_net) AS profit_net,
            SUM(f.revenue_net) AS revenue_net,
            SUM(f.sales_quantity) AS units_sold,
            CASE WHEN SUM(f.revenue_net) > 0
                 THEN 100.0 * SUM(f.profit_net) / SUM(f.revenue_net)
                 ELSE NULL END AS margin_net_pct
        FROM fact_sales f
        JOIN {g['dim']} g ON f.{g['fk']} = g.{g['key']}
        JOIN dim_date d ON f.date_fk = d.date_id
        WHERE {where}
        GROUP BY g.{g['key']}, g.{g['label']}
        ORDER BY {_ORDER_BY[rank]}
        LIMIT 10
        """,
        params,
    ).pl()


def summary_metrics(
    con: duckdb.DuckDBPyConnection,
    store_filter: list[int] | None = None,
    date_range: tuple[date, date] | None = None,
) -> dict:
    """KPIs de cabecera para el sidebar. Los totales excluyen filas anómalas y
    sin costo derivable; los conteos de flags incluyen sus filas dentro del
    scope de fechas/tienda.
    """
    where, params = _filter_clause(store_filter, date_range, exclude_flagged=False)
    row = con.execute(
        f"""
        SELECT
            SUM(CASE WHEN NOT f.is_anomalous_zero_price AND NOT f.is_cost_missing
                     THEN f.revenue_net ELSE 0 END) AS total_revenue_net,
            SUM(CASE WHEN NOT f.is_anomalous_zero_price AND NOT f.is_cost_missing
                     THEN f.profit_net  ELSE 0 END) AS total_profit_net,
            SUM(CASE WHEN f.is_return                THEN 1 ELSE 0 END) AS n_returns,
            SUM(CASE WHEN f.is_anomalous_zero_price  THEN 1 ELSE 0 END) AS n_anomalies,
            SUM(CASE WHEN f.is_cost_missing          THEN 1 ELSE 0 END) AS n_cost_missing
        FROM fact_sales f
        JOIN dim_date d ON f.date_fk = d.date_id
        WHERE {where}
        """,
        params,
    ).fetchone()
    keys = ["total_revenue_net", "total_profit_net", "n_returns", "n_anomalies", "n_cost_missing"]
    return dict(zip(keys, row))


def get_store_options(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    return con.execute("SELECT store_id, city FROM dim_store ORDER BY store_id").pl()


def get_date_bounds(con: duckdb.DuckDBPyConnection) -> tuple[date, date]:
    lo, hi = con.execute("SELECT MIN(date), MAX(date) FROM dim_date").fetchone()
    return lo, hi
