"""Silver: marca devoluciones y anomalías de precio cero sobre las ventas.

Per CONTEXT.md:
- Una devolución es cualquier venta con SalesQuantity < 0 (se preserva e incluye en profit).
- Una anomalía es SalesPrice == 0 AND SalesQuantity > 0 (se excluye del ranking).

Solo agrega columnas booleanas; nunca elimina filas. Contrato lazy-only:
el orchestrator transmite los flags hacia el resto de la cadena Silver.
"""
import polars as pl


def flag_sales(sales: pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    return sales.lazy().with_columns(
        (pl.col("SalesQuantity") < 0).alias("is_return"),
        ((pl.col("SalesPrice") == 0) & (pl.col("SalesQuantity") > 0)).alias("is_anomalous_zero_price"),
    )
