"""Characterization tests for the Gold layer.

Verify the four dimension builders and fact_sales construction against
the same fixtures as Silver.
"""
from datetime import date
import polars as pl

from kisabella.silver.clean import flag_sales
from kisabella.silver.enrich import compute_cost_basis, enrich_sales
from kisabella.gold.dimensions import (
    build_dim_product, build_dim_vendor, build_dim_store, build_dim_date,
)
from kisabella.gold.fact import build_fact_sales


def test_dim_product_pk_is_unique(price_catalog):
    dim = build_dim_product(price_catalog)
    assert dim["brand"].n_unique() == dim.height
    assert dim.columns == ["brand", "description", "size", "volume", "classification"]


def test_dim_vendor_drops_rows_with_null_vendor_number(sales):
    sales_with_null = sales.with_columns(
        pl.when(pl.col("Brand") == 500).then(None).otherwise(pl.col("VendorNo")).alias("VendorNo")
    )
    dim = build_dim_vendor(sales_with_null)
    assert dim["vendor_no"].null_count() == 0
    # Original sales had vendors {10, 20, 30, 40, 50}; after nulling vendor for brand 500
    # we expect {10, 20, 30, 40} only.
    assert sorted(dim["vendor_no"].to_list()) == [10, 20, 30, 40]


def test_dim_store_union_includes_stores_only_present_in_end_inv(beg_inv, end_inv):
    # beg_inv has stores 1, 2, 3. end_inv adds store 4 (mid-year opening, like PEMBROKE).
    dim = build_dim_store(beg_inv, end_inv)
    assert sorted(dim["store_id"].to_list()) == [1, 2, 3, 4]
    # Each store has the expected city.
    by_id = {row["store_id"]: row["city"] for row in dim.to_dicts()}
    assert by_id == {1: "TOWNA", 2: "TOWNB", 3: "TOWNC", 4: "TOWND"}


def test_dim_date_generates_contiguous_date_ids():
    dim = build_dim_date(date(2016, 1, 1), date(2016, 1, 5))
    assert dim.height == 5
    assert dim["date_id"].to_list() == [0, 1, 2, 3, 4]
    assert dim["date"].to_list() == [
        date(2016, 1, 1), date(2016, 1, 2), date(2016, 1, 3),
        date(2016, 1, 4), date(2016, 1, 5),
    ]
    assert dim["month"].unique().to_list() == [1]
    assert dim["quarter"].unique().to_list() == [1]


def test_fact_sales_preserves_row_count_and_maps_fks(sales, purchases, price_catalog):
    flagged = flag_sales(sales)
    cost = compute_cost_basis(purchases, price_catalog, flagged)
    enriched = enrich_sales(flagged, cost)
    dim_date = build_dim_date(date(2016, 1, 1), date(2016, 12, 31))

    fact = build_fact_sales(enriched, dim_date).collect()

    # Row count preserved.
    assert fact.height == sales.height

    # FK columns mapped from the source columns, not invented.
    assert fact["product_fk"].to_list() == sales["Brand"].to_list()
    assert fact["vendor_fk"].to_list() == sales["VendorNo"].to_list()
    assert fact["store_fk"].to_list() == sales["Store"].to_list()

    # All sales are on 2016-01-15, which is date_id 14 in a year starting 2016-01-01.
    assert fact["date_fk"].unique().to_list() == [14]
