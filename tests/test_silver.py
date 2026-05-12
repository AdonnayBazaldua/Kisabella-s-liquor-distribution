"""Characterization tests for the Silver layer.

Verify observed behavior of flag_sales, compute_cost_basis, enrich_sales
against hand-crafted fixtures with known expected outputs.
"""
import math
import polars as pl

from kisabella.silver.clean import flag_sales
from kisabella.silver.enrich import compute_cost_basis, enrich_sales


def test_negative_quantity_flagged_as_return(sales):
    flagged = flag_sales(sales).collect()
    return_rows = flagged.filter(pl.col("is_return")).select("InventoryId", "SalesQuantity")
    assert return_rows.height == 1
    assert return_rows["InventoryId"][0] == "1_TOWNA_400"
    assert return_rows["SalesQuantity"][0] == -1


def test_zero_price_with_positive_quantity_flagged_as_anomaly(sales):
    flagged = flag_sales(sales).collect()
    anom = flagged.filter(pl.col("is_anomalous_zero_price"))
    assert anom.height == 1
    assert anom["InventoryId"][0] == "1_TOWNA_400"
    assert anom["SalesQuantity"][0] == 2
    assert anom["SalesPrice"][0] == 0.0


def test_cost_basis_weighted_avg_from_purchases(sales, purchases, price_catalog):
    cost = compute_cost_basis(purchases, price_catalog, sales)
    row = cost.filter(pl.col("InventoryId") == "1_TOWNA_100").row(0, named=True)
    # Expected: (6.00 * 10 + 8.00 * 5) / (10 + 5) = 100 / 15 = 6.6667
    assert math.isclose(row["cost_unit"], 100 / 15, rel_tol=1e-6)
    assert row["cost_source"] == "purchases_avg"


def test_cost_basis_falls_back_to_catalog_when_inventory_absent_from_purchases(
    sales, purchases, price_catalog,
):
    cost = compute_cost_basis(purchases, price_catalog, sales)
    row = cost.filter(pl.col("InventoryId") == "3_TOWNC_300").row(0, named=True)
    # Brand 300 is not in purchases; catalog says PurchasePrice=3.00 for Brand 300.
    assert math.isclose(row["cost_unit"], 3.00, rel_tol=1e-6)
    assert row["cost_source"] == "catalog_brand"


def test_cost_basis_marks_missing_when_neither_source_has_data(
    sales, purchases, price_catalog,
):
    cost = compute_cost_basis(purchases, price_catalog, sales)
    row = cost.filter(pl.col("InventoryId") == "4_TOWND_500").row(0, named=True)
    # Brand 500 is in sales only (not in purchases, not in catalog).
    assert row["cost_unit"] is None
    assert row["cost_source"] == "missing"


def test_enriched_profit_subtracts_excise_tax_for_net_only(sales, purchases, price_catalog):
    flagged = flag_sales(sales)
    cost = compute_cost_basis(purchases, price_catalog, flagged)
    enriched = enrich_sales(flagged, cost).collect()

    # First row: Brand 100, Qty=2, Dollars=20.00, ExciseTax=1.00, cost_unit=100/15.
    row = enriched.filter(
        (pl.col("InventoryId") == "1_TOWNA_100") & (pl.col("SalesQuantity") == 2)
    ).row(0, named=True)

    expected_total_cost = (100 / 15) * 2
    assert math.isclose(row["revenue_gross"], 20.00, rel_tol=1e-6)
    assert math.isclose(row["revenue_net"], 19.00, rel_tol=1e-6)
    assert math.isclose(row["total_cost"], expected_total_cost, rel_tol=1e-6)
    assert math.isclose(row["profit_gross"], 20.00 - expected_total_cost, rel_tol=1e-6)
    assert math.isclose(row["profit_net"], 19.00 - expected_total_cost, rel_tol=1e-6)
    # Sanity: gross profit > net profit by exactly the excise tax.
    assert math.isclose(row["profit_gross"] - row["profit_net"], 1.00, rel_tol=1e-6)
