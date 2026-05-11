"""Smoke test integral del pipeline Kisabella's LLC.

Test único que valida el sistema end-to-end. Si esto pasa, el deploy es seguro.

Self-contained: construye su propio dataset sintético en `tmp_path`, redirige
las rutas del módulo `config`, ejecuta el pipeline completo (Bronze -> Silver
-> Gold -> DuckDB), y verifica nueve invariantes críticos:

  1. El pipeline corre sin excepciones y produce el archivo DuckDB esperado.
  2. Las cinco tablas del Star Schema existen y no están vacías.
  3. Integridad referencial: ningún FK del fact apunta a un PK ausente en su dim.
  4. Aritmética de profit: profit_gross >= profit_net en toda fila activa.
  5. Las filas marcadas como anómalas se cuentan correctamente.
  6. Las queries `top10` y `summary_metrics` del dashboard devuelven datos.
  7. Las filas anómalas se excluyen del ranking visible al usuario.
  8. El filtro por tienda reduce el conjunto de resultados.
  9. El dashboard Streamlit renderiza sin lanzar excepciones.

Ejecutar:
    source .venv/bin/activate
    pytest tests/test_smoke.py -v
"""
import os
from datetime import date
from pathlib import Path

# La env var POLARS_NEW_STREAMING debe setearse antes del primer import de polars
# para activar el motor que soporta `sink_parquet` sobre nuestro pipeline.
os.environ.setdefault("POLARS_NEW_STREAMING", "1")

import duckdb  # noqa: E402
import polars as pl  # noqa: E402
import pytest  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from kisabella import config  # noqa: E402
from kisabella.dashboard.queries import summary_metrics, top10  # noqa: E402
from kisabella.pipeline import run  # noqa: E402


DASHBOARD_SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "src" / "kisabella" / "dashboard" / "app.py"
).as_posix()


@pytest.fixture
def kisabella_warehouse(tmp_path, monkeypatch):
    """Genera un dataset sintético mínimo y redirige `config` a `tmp_path`.

    Diseño de los datos:
      - sales (5 filas): cuatro brands (100, 200, 300, 400). La fila del
        brand 400 es anómala (`SalesPrice=0`) y debe quedar excluida del
        ranking visible.
      - purchases: cubre los brands 100, 200, 400. El brand 300 NO está,
        así que su costo se resuelve por fallback al catálogo.
      - price_catalog: cubre los cuatro brands.
      - beg_inv (3 tiendas) + end_inv (4 tiendas, agrega TOWND): la unión
        cubre todas las tiendas que aparecen en sales.
    """
    data_dir = tmp_path / "Data"
    data_dir.mkdir()

    pl.DataFrame(
        {
            "InventoryId":    ["1_TOWNA_100", "1_TOWNA_100", "2_TOWNB_200", "3_TOWNC_300", "1_TOWNA_400"],
            "Store":          [1, 1, 2, 3, 1],
            "Brand":          [100, 100, 200, 300, 400],
            "Description":    ["Vodka A", "Vodka A", "Whisky B", "Gin C", "Rum D"],
            "Size":           ["750mL"] * 5,
            "SalesQuantity":  [2, 1, 3, 1, 2],
            "SalesDollars":   [30.00, 15.00, 90.00, 5.00, 0.00],  # ultima fila: anomalia
            "SalesPrice":     [15.00, 15.00, 30.00, 5.00, 0.00],
            "SalesDate":      [date(2016, 1, 15), date(2016, 2, 10),
                               date(2016, 3, 20), date(2016, 5, 1),
                               date(2016, 6, 15)],
            "Volume":         ["750"] * 5,
            "Classification": [1, 1, 1, 2, 1],
            "ExciseTax":      [1.50, 0.75, 4.50, 0.25, 0.00],
            "VendorNo":       [10, 10, 10, 20, 30],
            "VendorName":     ["VEN A", "VEN A", "VEN A", "VEN B", "VEN C"],
        },
        schema_overrides={"Store": pl.Int32, "Brand": pl.Int32, "SalesQuantity": pl.Int32,
                          "Classification": pl.Int8, "VendorNo": pl.Int32},
    ).write_csv(data_dir / config.CSV_SALES)

    pl.DataFrame(
        {
            "InventoryId":    ["1_TOWNA_100", "2_TOWNB_200", "1_TOWNA_400"],
            "Store":          [1, 2, 1],
            "Brand":          [100, 200, 400],
            "Description":    ["Vodka A", "Whisky B", "Rum D"],
            "Size":           ["750mL"] * 3,
            "VendorNumber":   [10, 10, 30],
            "VendorName":     ["VEN A", "VEN A", "VEN C"],
            "PONumber":       [1001, 1002, 1003],
            "PODate":         [date(2015, 12, 21), date(2016, 2, 1), date(2016, 5, 1)],
            "ReceivingDate":  [date(2016, 1, 2), date(2016, 2, 15), date(2016, 5, 10)],
            "InvoiceDate":    [date(2016, 1, 4), date(2016, 2, 16), date(2016, 5, 15)],
            "PayDate":        [date(2016, 2, 16), date(2016, 3, 15), date(2016, 6, 15)],
            "PurchasePrice":  [9.00, 20.00, 4.00],
            "Quantity":       [10, 5, 5],
            "Dollars":        [90.00, 100.00, 20.00],
            "Classification": [1, 1, 1],
        },
        schema_overrides={"Store": pl.Int32, "Brand": pl.Int32, "VendorNumber": pl.Int32,
                          "PONumber": pl.Int64, "Quantity": pl.Int32, "Classification": pl.Int8},
    ).write_csv(data_dir / config.CSV_PURCHASES)

    pl.DataFrame(
        {
            "Brand":          [100, 200, 300, 400],
            "Description":    ["Vodka A", "Whisky B", "Gin C", "Rum D"],
            "Price":          [15.00, 30.00, 5.00, 5.00],
            "Size":           ["750mL"] * 4,
            "Volume":         ["750"] * 4,
            "Classification": [1, 1, 2, 1],
            "PurchasePrice":  [9.00, 20.00, 3.00, 4.00],
            "VendorNumber":   [10, 10, 20, 30],
            "VendorName":     ["VEN A", "VEN A", "VEN B", "VEN C"],
        },
        schema_overrides={"Brand": pl.Int32, "Classification": pl.Int8, "VendorNumber": pl.Int32},
    ).write_csv(data_dir / config.CSV_PRICE_CATALOG)

    pl.DataFrame(
        {
            "InventoryId": ["1_TOWNA_100", "2_TOWNB_200", "3_TOWNC_300"],
            "Store":       [1, 2, 3],
            "City":        ["TOWNA", "TOWNB", "TOWNC"],
            "Brand":       [100, 200, 300],
            "Description": ["Vodka A", "Whisky B", "Gin C"],
            "Size":        ["750mL"] * 3,
            "onHand":      [5, 2, 0],
            "Price":       [15.00, 30.00, 5.00],
            "startDate":   [date(2016, 1, 1)] * 3,
        },
        schema_overrides={"Store": pl.Int32, "Brand": pl.Int32, "onHand": pl.Int32},
    ).write_csv(data_dir / config.CSV_BEG_INV)

    pl.DataFrame(
        {
            "InventoryId": ["1_TOWNA_100", "2_TOWNB_200", "3_TOWNC_300", "1_TOWNA_400"],
            "Store":       [1, 2, 3, 1],
            "City":        ["TOWNA", "TOWNB", "TOWNC", "TOWNA"],
            "Brand":       [100, 200, 300, 400],
            "Description": ["Vodka A", "Whisky B", "Gin C", "Rum D"],
            "Size":        ["750mL"] * 4,
            "onHand":      [7, 4, 0, 0],
            "Price":       [15.00, 30.00, 5.00, 5.00],
            "endDate":     [date(2016, 12, 31)] * 4,
        },
        schema_overrides={"Store": pl.Int32, "Brand": pl.Int32, "onHand": pl.Int32},
    ).write_csv(data_dir / config.CSV_END_INV)

    pl.DataFrame(
        {
            "VendorNumber": [10],
            "VendorName":   ["VEN A"],
            "InvoiceDate":  [date(2016, 1, 4)],
            "PONumber":     [1001],
            "PODate":       [date(2015, 12, 21)],
            "PayDate":      [date(2016, 2, 16)],
            "Quantity":     [10],
            "Dollars":      [90.00],
            "Freight":      [3.00],
            "Approval":     ["None"],
        },
        schema_overrides={"VendorNumber": pl.Int32, "PONumber": pl.Int64, "Quantity": pl.Int32},
    ).write_csv(data_dir / config.CSV_INVOICES)

    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "PARQUET_DIR", tmp_path / "parquet_cache")
    monkeypatch.setattr(config, "WAREHOUSE_DIR", tmp_path / "warehouse")
    monkeypatch.setattr(config, "WAREHOUSE_PATH", tmp_path / "warehouse" / "gold.duckdb")
    return tmp_path


def test_kisabella_pipeline_smoke_end_to_end(kisabella_warehouse):
    """Smoke integral: ejecuta el pipeline y valida nueve invariantes críticos."""

    # === FASE 1: Pipeline corre sin excepciones ===
    run()
    assert config.WAREHOUSE_PATH.exists(), "el archivo DuckDB no fue creado"

    with duckdb.connect(str(config.WAREHOUSE_PATH), read_only=True) as con:
        # === FASE 2: Estructura del Star Schema ===
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        expected = {"fact_sales", "dim_product", "dim_vendor", "dim_store", "dim_date"}
        assert tables == expected, f"tablas obtenidas={tables}, esperadas={expected}"

        for tbl in tables:
            n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            assert n > 0, f"la tabla {tbl} esta vacia"

        # === FASE 3: Integridad referencial (FKs) ===
        # Toda fila del fact debe tener un PK correspondiente en su dim.
        for fk_col, dim_table, dim_key in [
            ("product_fk", "dim_product", "brand"),
            ("vendor_fk",  "dim_vendor",  "vendor_no"),
            ("store_fk",   "dim_store",   "store_id"),
            ("date_fk",    "dim_date",    "date_id"),
        ]:
            orphans = con.execute(
                f"SELECT COUNT(*) FROM fact_sales f "
                f"LEFT JOIN {dim_table} d ON f.{fk_col} = d.{dim_key} "
                f"WHERE d.{dim_key} IS NULL"
            ).fetchone()[0]
            assert orphans == 0, (
                f"{fk_col} tiene {orphans} valores huerfanos hacia {dim_table}.{dim_key}"
            )

        # === FASE 4: Aritmetica de profit (gross >= net) ===
        # revenue_gross = revenue_net + excise_tax (excise_tax >= 0); el costo
        # es el mismo en ambas formulas, por lo que profit_gross >= profit_net.
        violations = con.execute("""
            SELECT COUNT(*) FROM fact_sales
            WHERE NOT is_anomalous_zero_price
              AND NOT is_cost_missing
              AND profit_gross < profit_net - 1e-6
        """).fetchone()[0]
        assert violations == 0, f"{violations} filas violan profit_gross >= profit_net"

        # === FASE 5: Flags de anomalia ===
        n_anom = con.execute(
            "SELECT COUNT(*) FROM fact_sales WHERE is_anomalous_zero_price"
        ).fetchone()[0]
        assert n_anom == 1, f"esperaba 1 fila anomala, hay {n_anom}"

        # === FASE 6: Queries del dashboard devuelven datos ===
        top_p = top10(con, by="product", rank="profit")
        assert top_p.height >= 1, "top10 productos vacio"
        required_cols = {"group_key", "group_label", "profit_net", "revenue_net", "margin_net_pct"}
        assert required_cols.issubset(set(top_p.columns)), (
            f"columnas faltantes en top10: {required_cols - set(top_p.columns)}"
        )

        top_v = top10(con, by="vendor", rank="profit")
        assert top_v.height >= 1, "top10 vendors vacio"

        top_m = top10(con, by="product", rank="margin")
        assert top_m["margin_net_pct"].null_count() < top_m.height, (
            "todos los margenes son null en el ranking por margin"
        )

        # === FASE 7: Anomalias quedan fuera del ranking visible ===
        # Brand 400 es la fila anomala y no debe aparecer en el top10.
        assert 400 not in top_p["group_key"].to_list(), (
            "fila anomala (brand 400) aparece en el ranking"
        )

        # === FASE 8: Filtros narrowsean los resultados ===
        # Brand 200 solo se vendio en tienda 2; con store_filter=[1] no debe estar.
        top_filtered = top10(con, by="product", rank="profit", store_filter=[1])
        assert 200 not in top_filtered["group_key"].to_list(), (
            "filtro store=[1] no excluyo brand 200 (solo en tienda 2)"
        )

        # === FASE 9: Summary metrics ===
        m = summary_metrics(con)
        assert m["total_revenue_net"] > 0, "revenue_net total debe ser positivo"
        assert m["n_anomalies"] == 1, f"n_anomalies={m['n_anomalies']}, esperaba 1"

    # === FASE 10: Dashboard Streamlit renderiza sin excepciones ===
    at = AppTest.from_file(DASHBOARD_SCRIPT, default_timeout=15).run()
    assert not at.exception, f"dashboard lanzo excepcion: {at.exception}"
    assert len(at.tabs) >= 2, "dashboard debe tener al menos 2 tabs (productos, marcas)"
    assert len(at.sidebar.multiselect) >= 1, "sidebar sin filtro multiselect de tiendas"
    assert len(at.sidebar.date_input) >= 1, "sidebar sin filtro date_input"
