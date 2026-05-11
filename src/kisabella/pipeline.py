"""Orchestrator del pipeline: Bronze -> Silver -> Gold -> DuckDB.

Ejecutar como: python -m kisabella.pipeline

Hace streaming de Silver (ventas enriquecidas) y fact_sales a parquet vía
LazyFrame de Polars para que el dataset completo de 12M+ filas quepa en
RAM modesta. DuckDB ingesta el parquet resultante con su reader nativo
(sin materialización Python del fact table).
"""
import logging
import os
import sys

# Activar el new streaming engine: sink_parquet sobre nuestro chain de
# join+with_columns no está soportado por el standard engine en Polars 1.18.
os.environ.setdefault("POLARS_NEW_STREAMING", "1")

import polars as pl  # noqa: E402  (la env var debe setearse antes del import)

from kisabella import config
from kisabella.bronze import ingest
from kisabella.silver.clean import flag_sales
from kisabella.silver.enrich import compute_cost_basis, enrich_sales
from kisabella.gold.dimensions import (
    build_dim_product, build_dim_vendor, build_dim_store, build_dim_date,
)
from kisabella.gold.fact import build_fact_sales
from kisabella.gold.load import load_to_duckdb

log = logging.getLogger(__name__)


def run() -> None:
    log.info("=== pipeline start ===")

    log.info("--- bronze: csv -> parquet ---")
    ingest.ingest_all()

    log.info("--- silver: cost basis + enriched stream ---")
    sales_path = config.PARQUET_DIR / "sales.parquet"
    purchases = pl.read_parquet(config.PARQUET_DIR / "purchases.parquet")
    catalog = pl.read_parquet(config.PARQUET_DIR / "price_catalog.parquet")

    cost = compute_cost_basis(purchases, catalog, pl.scan_parquet(sales_path))
    log.info(
        "cost basis    rows=%d  sources=%s",
        cost.height,
        {r["cost_source"]: r["len"] for r in cost.group_by("cost_source").len().to_dicts()},
    )

    silver_path = config.PARQUET_DIR / "silver_sales.parquet"
    enrich_sales(flag_sales(pl.scan_parquet(sales_path)), cost).sink_parquet(silver_path)
    log.info("silver wrote %s", silver_path)

    log.info("--- gold: dims + fact + duckdb load ---")
    beg_inv = pl.read_parquet(config.PARQUET_DIR / "beg_inv.parquet")
    end_inv = pl.read_parquet(config.PARQUET_DIR / "end_inv.parquet")

    dim_product = build_dim_product(catalog)
    dim_vendor = build_dim_vendor(pl.scan_parquet(sales_path))
    dim_store = build_dim_store(beg_inv, end_inv)
    dim_date = build_dim_date()

    fact_path = config.PARQUET_DIR / "fact_sales.parquet"
    build_fact_sales(pl.scan_parquet(silver_path), dim_date).sink_parquet(fact_path)
    log.info("gold fact wrote %s", fact_path)

    load_to_duckdb(
        {
            "fact_sales": fact_path,
            "dim_product": dim_product,
            "dim_vendor": dim_vendor,
            "dim_store": dim_store,
            "dim_date": dim_date,
        },
        config.WAREHOUSE_PATH,
    )
    log.info("=== pipeline complete: %s ===", config.WAREHOUSE_PATH)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    run()


if __name__ == "__main__":
    main()
