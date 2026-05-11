"""Gold: construye fact_sales con FKs a todas las dims y métricas precomputadas.

Granularidad: una fila por línea de venta (sin agregación contra Silver).
Contrato lazy-only para el input enriched para que el orchestrator pueda
hacer sink directo del fact a parquet sin materializar nunca 12M+ filas.
"""
import polars as pl


def build_fact_sales(
    enriched: pl.DataFrame | pl.LazyFrame,
    dim_date: pl.DataFrame,
) -> pl.LazyFrame:
    # Sin sale_id surrogate: las queries no lo usan, y `with_row_index` rompe el
    # streaming engine. Si una PK numérica fuera necesaria downstream, DuckDB
    # puede agregarla al ingest con ROW_NUMBER().
    return (
        enriched.lazy()
        .join(
            dim_date.lazy().select("date_id", "date"),
            left_on="SalesDate",
            right_on="date",
            how="left",
        )
        .select(
            pl.col("InventoryId").alias("inventory_fk"),
            pl.col("Brand").alias("product_fk"),
            pl.col("VendorNo").alias("vendor_fk"),
            pl.col("Store").alias("store_fk"),
            pl.col("date_id").alias("date_fk"),
            pl.col("SalesQuantity").alias("sales_quantity"),
            pl.col("revenue_gross"),
            pl.col("revenue_net"),
            pl.col("ExciseTax").alias("excise_tax"),
            pl.col("total_cost"),
            pl.col("profit_gross"),
            pl.col("profit_net"),
            pl.col("is_return"),
            pl.col("is_anomalous_zero_price"),
            pl.col("is_cost_missing"),
            pl.col("cost_source"),
        )
    )
