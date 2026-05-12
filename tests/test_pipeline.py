"""TDD tests for the pipeline orchestrator (Bronze -> Silver -> Gold -> DuckDB)."""
import duckdb

from kisabella import config
from kisabella.pipeline import run


def test_pipeline_run_creates_duckdb_with_all_5_tables(synthetic_data_dir):
    run()

    assert config.WAREHOUSE_PATH.exists()

    with duckdb.connect(str(config.WAREHOUSE_PATH), read_only=True) as con:
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}

    assert tables == {"fact_sales", "dim_product", "dim_vendor", "dim_store", "dim_date"}
    assert all(c > 0 for c in counts.values()), counts


def test_pipeline_preserves_sales_row_count_in_fact(synthetic_data_dir, sales):
    run()
    with duckdb.connect(str(config.WAREHOUSE_PATH), read_only=True) as con:
        n_fact = con.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
    assert n_fact == sales.height


def test_pipeline_computes_revenue_for_known_brand(synthetic_data_dir):
    run()
    # Brand 100 has 2 sales rows (Dollars 20.00 + 10.00 = 30.00 gross).
    with duckdb.connect(str(config.WAREHOUSE_PATH), read_only=True) as con:
        revenue = con.execute(
            "SELECT SUM(revenue_gross) FROM fact_sales WHERE product_fk = 100"
        ).fetchone()[0]
    assert abs(revenue - 30.00) < 1e-6
