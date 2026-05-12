"""Tiny synthetic DataFrames for characterization tests.

Hand-crafted to exercise specific behaviors: cost basis with both
sources, returns, anomalies, mid-year store openings.
"""
import os

# Must be set before any `import polars` so Polars picks the new streaming
# engine (required by sink_parquet over our join+with_columns chain).
os.environ.setdefault("POLARS_NEW_STREAMING", "1")

from datetime import date  # noqa: E402
from pathlib import Path  # noqa: E402
import polars as pl  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def sales() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "InventoryId":    ["1_TOWNA_100", "1_TOWNA_100", "2_TOWNB_200", "3_TOWNC_300", "1_TOWNA_400", "1_TOWNA_400", "4_TOWND_500"],
            "Store":          [1,             1,             2,             3,             1,             1,             4],
            "Brand":          [100,           100,           200,           300,           400,           400,           500],
            "Description":    ["Vodka A",     "Vodka A",     "Whisky B",    "Gin C",       "Rum D",       "Rum D",       "Free E"],
            "Size":           ["750mL"] * 7,
            "SalesQuantity": [2,             1,             5,             1,             -1,            2,             1],
            "SalesDollars":  [20.00,         10.00,         150.00,        5.00,          -10.00,        0.00,          5.00],
            "SalesPrice":    [10.00,         10.00,         30.00,         5.00,          10.00,         0.00,          5.00],
            "SalesDate":     [date(2016, 1, 15)] * 7,
            "Volume":        ["750"] * 7,
            "Classification": [1] * 7,
            "ExciseTax":     [1.00,          0.50,          7.50,          0.25,          -0.50,         0.00,          0.00],
            "VendorNo":      [10,            10,            20,            30,            40,            40,            50],
            "VendorName":    ["VEN A", "VEN A", "VEN B", "VEN C", "VEN D", "VEN D", "VEN E"],
        },
        schema_overrides={
            "Store": pl.Int32, "Brand": pl.Int32, "SalesQuantity": pl.Int32,
            "Classification": pl.Int8, "VendorNo": pl.Int32,
        },
    )


@pytest.fixture
def purchases() -> pl.DataFrame:
    # Brand 100 has two purchase lines (tests weighted avg).
    # Brand 300 is intentionally absent (sales falls back to catalog).
    # Brand 500 is intentionally absent everywhere (missing).
    return pl.DataFrame(
        {
            "InventoryId":    ["1_TOWNA_100", "1_TOWNA_100", "2_TOWNB_200", "1_TOWNA_400"],
            "Store":          [1, 1, 2, 1],
            "Brand":          [100, 100, 200, 400],
            "Description":    ["Vodka A", "Vodka A", "Whisky B", "Rum D"],
            "Size":           ["750mL"] * 4,
            "VendorNumber":   [10, 10, 20, 40],
            "VendorName":     ["VEN A", "VEN A", "VEN B", "VEN D"],
            "PONumber":       [1001, 1002, 1003, 1004],
            "PODate":         [date(2015, 12, 20)] * 4,
            "ReceivingDate":  [date(2016, 1, 1)] * 4,
            "InvoiceDate":    [date(2016, 1, 5)] * 4,
            "PayDate":        [date(2016, 2, 1)] * 4,
            "PurchasePrice":  [6.00, 8.00, 20.00, 7.00],
            "Quantity":       [10, 5, 3, 5],
            "Dollars":        [60.00, 40.00, 60.00, 35.00],
            "Classification": [1, 1, 1, 1],
        },
        schema_overrides={
            "Store": pl.Int32, "Brand": pl.Int32, "VendorNumber": pl.Int32,
            "PONumber": pl.Int64, "Quantity": pl.Int32, "Classification": pl.Int8,
        },
    )


@pytest.fixture
def price_catalog() -> pl.DataFrame:
    # Brand 300 here only — tests catalog fallback path.
    # Brand 500 intentionally absent — tests missing path.
    return pl.DataFrame(
        {
            "Brand":          [100, 200, 300, 400],
            "Description":    ["Vodka A", "Whisky B", "Gin C", "Rum D"],
            "Price":          [10.00, 30.00, 5.00, 10.00],
            "Size":           ["750mL"] * 4,
            "Volume":         ["750"] * 4,
            "Classification": [1, 1, 1, 1],
            "PurchasePrice":  [7.00, 22.00, 3.00, 7.50],
            "VendorNumber":   [10, 20, 30, 40],
            "VendorName":     ["VEN A", "VEN B", "VEN C", "VEN D"],
        },
        schema_overrides={
            "Brand": pl.Int32, "Classification": pl.Int8, "VendorNumber": pl.Int32,
        },
    )


@pytest.fixture
def beg_inv() -> pl.DataFrame:
    # Stores 1, 2, 3. Store 4 (TOWND) intentionally absent — tests union with end_inv.
    return pl.DataFrame(
        {
            "InventoryId": ["1_TOWNA_100", "2_TOWNB_200", "3_TOWNC_300"],
            "Store":       [1, 2, 3],
            "City":        ["TOWNA", "TOWNB", "TOWNC"],
            "Brand":       [100, 200, 300],
            "Description": ["Vodka A", "Whisky B", "Gin C"],
            "Size":        ["750mL"] * 3,
            "onHand":      [5, 2, 0],
            "Price":       [10.00, 30.00, 5.00],
            "startDate":   [date(2016, 1, 1)] * 3,
        },
        schema_overrides={"Store": pl.Int32, "Brand": pl.Int32, "onHand": pl.Int32},
    )


@pytest.fixture
def end_inv() -> pl.DataFrame:
    # Adds store 4 (TOWND) — opened mid-year.
    return pl.DataFrame(
        {
            "InventoryId": ["1_TOWNA_100", "2_TOWNB_200", "3_TOWNC_300", "4_TOWND_500"],
            "Store":       [1, 2, 3, 4],
            "City":        ["TOWNA", "TOWNB", "TOWNC", "TOWND"],
            "Brand":       [100, 200, 300, 500],
            "Description": ["Vodka A", "Whisky B", "Gin C", "Free E"],
            "Size":        ["750mL"] * 4,
            "onHand":      [3, 1, 0, 0],
            "Price":       [10.00, 30.00, 5.00, 5.00],
            "endDate":     [date(2016, 12, 31)] * 4,
        },
        schema_overrides={"Store": pl.Int32, "Brand": pl.Int32, "onHand": pl.Int32},
    )


@pytest.fixture
def invoices() -> pl.DataFrame:
    # Minimal: one invoice header, mirrors a row from purchases.
    return pl.DataFrame(
        {
            "VendorNumber": [10],
            "VendorName":   ["VEN A"],
            "InvoiceDate":  [date(2016, 1, 5)],
            "PONumber":     [1001],
            "PODate":       [date(2015, 12, 20)],
            "PayDate":      [date(2016, 2, 1)],
            "Quantity":     [10],
            "Dollars":      [60.00],
            "Freight":      [3.00],
            "Approval":     ["None"],
        },
        schema_overrides={
            "VendorNumber": pl.Int32, "PONumber": pl.Int64, "Quantity": pl.Int32,
        },
    )


@pytest.fixture
def synthetic_data_dir(
    tmp_path,
    monkeypatch,
    sales, purchases, price_catalog, beg_inv, end_inv, invoices,
) -> Path:
    """Write the synthetic DataFrames as CSVs to tmp_path/Data; redirect config paths.

    Returns the data dir; pipeline.run() reads from config (now pointing at tmp_path).
    """
    from kisabella import config

    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    sales.write_csv(data_dir / config.CSV_SALES)
    purchases.write_csv(data_dir / config.CSV_PURCHASES)
    price_catalog.write_csv(data_dir / config.CSV_PRICE_CATALOG)
    beg_inv.write_csv(data_dir / config.CSV_BEG_INV)
    end_inv.write_csv(data_dir / config.CSV_END_INV)
    invoices.write_csv(data_dir / config.CSV_INVOICES)

    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "PARQUET_DIR", tmp_path / "parquet_cache")
    monkeypatch.setattr(config, "WAREHOUSE_DIR", tmp_path / "warehouse")
    monkeypatch.setattr(config, "WAREHOUSE_PATH", tmp_path / "warehouse" / "gold.duckdb")
    return data_dir


def _build_test_warehouse(db_path: Path) -> Path:
    """Build the canonical test star schema at db_path. Returns db_path.

    fact_sales (8 rows): 6 normal + 1 anomalous (row 7) + 1 cost-missing (row 8).
    Active totals (rows 1-6 only):
      product 100: profit_net = 45+45 = 90   margin = 47.37%
      product 200: profit_net = 15           margin = 15.79%
      product 300: profit_net = 65           margin = 68.42%
      product 400: profit_net = 5+0.5 = 5.5  margin =  5.26%
      vendor  10 (100, 200): profit_net = 105
      vendor  20 (300, 400): profit_net = 70.5
    """
    import duckdb  # noqa: F401  (warehouse_with_data uses it after this returns)
    from kisabella.gold.load import load_to_duckdb

    dim_product = pl.DataFrame(
        {
            "brand":          [100, 200, 300, 400],
            "description":    ["P1", "P2", "P3", "P4"],
            "size":           ["750mL"] * 4,
            "volume":         ["750"] * 4,
            "classification": [1] * 4,
        },
        schema_overrides={"brand": pl.Int32, "classification": pl.Int8},
    )
    dim_vendor = pl.DataFrame(
        {"vendor_no": [10, 20], "vendor_name": ["V1", "V2"]},
        schema_overrides={"vendor_no": pl.Int32},
    )
    dim_store = pl.DataFrame(
        {"store_id": [1, 2], "city": ["A", "B"]},
        schema_overrides={"store_id": pl.Int32},
    )
    dim_date = pl.DataFrame(
        {
            "date_id": [0, 1, 2],
            "date":    [date(2016, 1, 1), date(2016, 1, 2), date(2016, 1, 3)],
            "year":    [2016] * 3,
            "month":   [1] * 3,
            "quarter": [1] * 3,
        },
        schema_overrides={"date_id": pl.Int64, "year": pl.Int32, "month": pl.Int8, "quarter": pl.Int8},
    )

    # Row 7 is anomalous, row 8 has missing cost. Both reference real brands and
    # carry material profit so the WHERE-clause exclusion is observable in totals.
    fact_sales = pl.DataFrame(
        {
            "inventory_fk": ["1_A_100","1_A_200","2_B_300","2_B_400","1_A_400","1_A_100","1_A_100","2_B_300"],
            "product_fk":   [100,      200,      300,      400,      400,      100,      100,      300],
            "vendor_fk":    [10,       10,       20,       20,       20,       10,       10,       20],
            "store_fk":     [1,        1,        2,        2,        1,        1,        1,        2],
            "date_fk":      [0,        0,        1,        1,        2,        2,        0,        1],
            "sales_quantity":[10,      5,        1,        1,        1,        10,       1,        2],
            "revenue_gross":[100.0,    100.0,    100.0,    100.0,    10.0,     100.0,    1000.0,   200.0],
            "revenue_net":  [95.0,     95.0,     95.0,     95.0,     9.5,      95.0,     950.0,    190.0],
            "excise_tax":   [5.0,      5.0,      5.0,      5.0,      0.5,      5.0,      50.0,     10.0],
            "total_cost":   [50.0,     80.0,     30.0,     90.0,     9.0,      50.0,     450.0,    90.0],
            "profit_gross": [50.0,     20.0,     70.0,     10.0,     1.0,      50.0,     550.0,    110.0],
            "profit_net":   [45.0,     15.0,     65.0,     5.0,      0.5,      45.0,     500.0,    100.0],
            "is_return":              [False]*8,
            "is_anomalous_zero_price":[False,False,False,False,False,False,True, False],
            "is_cost_missing":        [False,False,False,False,False,False,False,True],
            "cost_source":   ["purchases_avg"]*7 + ["missing"],
        },
        schema_overrides={
            "product_fk": pl.Int32, "vendor_fk": pl.Int32,
            "store_fk": pl.Int32, "date_fk": pl.Int64,
            "sales_quantity": pl.Int32,
        },
    )

    load_to_duckdb(
        {
            "fact_sales": fact_sales,
            "dim_product": dim_product,
            "dim_vendor": dim_vendor,
            "dim_store": dim_store,
            "dim_date": dim_date,
        },
        db_path,
    )
    return db_path


@pytest.fixture
def warehouse_with_data(tmp_path):
    import duckdb
    db_path = _build_test_warehouse(tmp_path / "test.duckdb")
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        yield con
    finally:
        con.close()


@pytest.fixture
def warehouse_at_config_path(tmp_path, monkeypatch):
    """Build the test warehouse and redirect config.WAREHOUSE_PATH to it.

    For dashboard/AppTest scenarios where the app reads `config.WAREHOUSE_PATH`
    on import.
    """
    db_path = _build_test_warehouse(tmp_path / "warehouse.duckdb")
    from kisabella import config
    monkeypatch.setattr(config, "WAREHOUSE_PATH", db_path)
    return db_path
