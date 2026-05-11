"""Gold: persiste fact + dims a un archivo DuckDB.

Cada valor en `tables` puede ser un DataFrame Polars (registrado vía Arrow)
o un Path a un archivo parquet (leído por el reader nativo de DuckDB, sin
costo de memoria Python — importante para el fact_sales de 12M+ filas).
"""
from pathlib import Path
import duckdb
import polars as pl


def load_to_duckdb(
    tables: dict[str, pl.DataFrame | Path],
    db_path: Path,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        for name, source in tables.items():
            if isinstance(source, Path):
                con.execute(
                    f"CREATE OR REPLACE TABLE {name} AS "
                    f"SELECT * FROM read_parquet(?)",
                    [str(source)],
                )
            else:
                con.register("_tmp", source.to_arrow())
                con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM _tmp")
                con.unregister("_tmp")
