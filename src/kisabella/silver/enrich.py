"""Silver: cost basis y enriquecimiento con métricas de profit.

Contrato lazy-only para entradas tipo sales (12M+ filas en producción).
`compute_cost_basis` devuelve un DataFrame eager porque cost es chico (~270K filas).
`enrich_sales` devuelve un LazyFrame para que el orchestrator pueda hacer
sink_parquet sin materializar las 12M+ filas enriquecidas en memoria de Python.
"""
import polars as pl


def compute_cost_basis(
    purchases: pl.DataFrame,
    price_catalog: pl.DataFrame,
    sales: pl.DataFrame | pl.LazyFrame,
) -> pl.DataFrame:
    purch_avg = (
        purchases.lazy()
        .filter(pl.col("Quantity") > 0)
        .group_by("InventoryId")
        .agg(
            (pl.col("PurchasePrice") * pl.col("Quantity")).sum().alias("_w"),
            pl.col("Quantity").sum().alias("_q"),
        )
        .with_columns((pl.col("_w") / pl.col("_q")).alias("cost_purch"))
        .select("InventoryId", "cost_purch")
    )

    cat_cost = (
        price_catalog.lazy()
        .group_by("Brand")
        .agg(pl.col("PurchasePrice").mean().alias("cost_catalog"))
    )

    return (
        sales.lazy().select("InventoryId", "Brand").unique()
        .join(purch_avg, on="InventoryId", how="left")
        .join(cat_cost, on="Brand", how="left")
        .with_columns(
            pl.coalesce("cost_purch", "cost_catalog").alias("cost_unit"),
            pl.when(pl.col("cost_purch").is_not_null()).then(pl.lit("purchases_avg"))
              .when(pl.col("cost_catalog").is_not_null()).then(pl.lit("catalog_brand"))
              .otherwise(pl.lit("missing"))
              .alias("cost_source"),
        )
        .select("InventoryId", "cost_unit", "cost_source")
        .collect()
    )


def enrich_sales(
    sales: pl.DataFrame | pl.LazyFrame,
    cost: pl.DataFrame,
) -> pl.LazyFrame:
    return (
        sales.lazy()
        .join(cost.lazy(), on="InventoryId", how="left")
        .with_columns(
            (pl.col("cost_source") == "missing").alias("is_cost_missing"),
            (pl.col("cost_unit") * pl.col("SalesQuantity")).alias("total_cost"),
            pl.col("SalesDollars").alias("revenue_gross"),
            (pl.col("SalesDollars") - pl.col("ExciseTax")).alias("revenue_net"),
        )
        .with_columns(
            (pl.col("revenue_gross") - pl.col("total_cost")).alias("profit_gross"),
            (pl.col("revenue_net") - pl.col("total_cost")).alias("profit_net"),
        )
    )
