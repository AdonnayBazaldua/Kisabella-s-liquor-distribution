"""Bronze: lee CSVs con schema explícito y los escribe a Parquet en streaming.

Limpia espacios en blanco en headers y en valores de columnas tipo String
(varios `VendorName` en los datos crudos tienen espacios al final). El uso
de `scan_csv` + `sink_parquet` mantiene el pico de memoria acotado: el CSV
de 1.6 GB de ventas nunca se materializa completo en RAM.
"""
import logging
from pathlib import Path
import polars as pl

from kisabella import config

log = logging.getLogger(__name__)

# (stem del archivo de salida, nombre del CSV origen, schema)
SOURCES: list[tuple[str, str, dict]] = [
    ("sales",         config.CSV_SALES,         config.SCHEMA_SALES),
    ("purchases",     config.CSV_PURCHASES,     config.SCHEMA_PURCHASES),
    ("price_catalog", config.CSV_PRICE_CATALOG, config.SCHEMA_PRICE_CATALOG),
    ("beg_inv",       config.CSV_BEG_INV,       config.SCHEMA_BEG_INV),
    ("end_inv",       config.CSV_END_INV,       config.SCHEMA_END_INV),
    ("invoices",      config.CSV_INVOICES,      config.SCHEMA_INVOICES),
]


def ingest_one(name: str, filename: str, schema: dict) -> Path:
    src = config.DATA_DIR / filename
    out = config.PARQUET_DIR / f"{name}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)

    plan = pl.scan_csv(
        src,
        schema_overrides=schema,
        try_parse_dates=True,
        null_values=["", "None", "NULL", "null"],
    )
    # Espacios en headers (los archivos crudos a veces los traen).
    actual = plan.collect_schema()
    rename = {c: c.strip() for c in actual.names() if c != c.strip()}
    if rename:
        plan = plan.rename(rename)
        actual = plan.collect_schema()
    string_cols = [c for c, dt in actual.items() if dt == pl.String]
    if string_cols:
        plan = plan.with_columns(pl.col(c).str.strip_chars() for c in string_cols)

    plan.sink_parquet(out, compression="snappy")
    n = pl.scan_parquet(out).select(pl.len()).collect().item()
    log.info("bronze %-13s %10d rows -> %s", name, n, out)
    return out


def ingest_all() -> dict[str, Path]:
    return {name: ingest_one(name, fn, sc) for name, fn, sc in SOURCES}
