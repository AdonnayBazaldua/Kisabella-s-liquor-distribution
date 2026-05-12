"""TDD tests for gold.load.load_to_duckdb."""
from pathlib import Path
import duckdb
import polars as pl

from kisabella.gold.load import load_to_duckdb


def test_load_writes_one_table_to_duckdb(tmp_path: Path):
    db = tmp_path / "test.duckdb"
    df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

    load_to_duckdb({"my_table": df}, db)

    con = duckdb.connect(str(db), read_only=True)
    try:
        result = con.execute("SELECT a, b FROM my_table ORDER BY a").pl()
    finally:
        con.close()
    assert result.to_dicts() == [
        {"a": 1, "b": "x"},
        {"a": 2, "b": "y"},
        {"a": 3, "b": "z"},
    ]


def test_re_running_load_replaces_existing_table(tmp_path: Path):
    db = tmp_path / "test.duckdb"
    first = pl.DataFrame({"id": [1]})
    second = pl.DataFrame({"id": [2, 3]})

    load_to_duckdb({"t": first}, db)
    load_to_duckdb({"t": second}, db)

    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute("SELECT id FROM t ORDER BY id").pl()["id"].to_list()
    finally:
        con.close()
    assert rows == [2, 3]


def test_load_writes_multiple_tables_in_one_call(tmp_path: Path):
    db = tmp_path / "test.duckdb"
    load_to_duckdb(
        {
            "alpha": pl.DataFrame({"x": [1, 2]}),
            "beta": pl.DataFrame({"y": ["a"]}),
            "gamma": pl.DataFrame({"z": [True, False, True]}),
        },
        db,
    )

    con = duckdb.connect(str(db), read_only=True)
    try:
        names = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        counts = {
            n: con.execute(f"SELECT COUNT(*) FROM {n}").fetchone()[0]
            for n in names
        }
    finally:
        con.close()
    assert names == {"alpha", "beta", "gamma"}
    assert counts == {"alpha": 2, "beta": 1, "gamma": 3}


def test_load_preserves_polars_dtypes_through_roundtrip(tmp_path: Path):
    db = tmp_path / "test.duckdb"
    df = pl.DataFrame(
        {
            "as_i32": pl.Series([1, 2], dtype=pl.Int32),
            "as_i64": pl.Series([10, 20], dtype=pl.Int64),
            "as_f64": pl.Series([1.5, 2.5], dtype=pl.Float64),
            "as_bool": [True, False],
            "as_str": ["x", "y"],
        }
    )

    load_to_duckdb({"t": df}, db)

    con = duckdb.connect(str(db), read_only=True)
    try:
        out = con.execute("SELECT * FROM t ORDER BY as_i32").pl()
    finally:
        con.close()
    assert out.schema["as_i32"] == pl.Int32
    assert out.schema["as_i64"] == pl.Int64
    assert out.schema["as_f64"] == pl.Float64
    assert out.schema["as_bool"] == pl.Boolean
    assert out.schema["as_str"] == pl.String


def test_load_accepts_parquet_path_for_streaming_ingest(tmp_path: Path):
    parquet = tmp_path / "src.parquet"
    pl.DataFrame({"k": [10, 20, 30], "v": ["a", "b", "c"]}).write_parquet(parquet)

    db = tmp_path / "test.duckdb"
    load_to_duckdb({"from_parquet": parquet}, db)

    con = duckdb.connect(str(db), read_only=True)
    try:
        out = con.execute("SELECT k, v FROM from_parquet ORDER BY k").pl()
    finally:
        con.close()
    assert out.to_dicts() == [
        {"k": 10, "v": "a"},
        {"k": 20, "v": "b"},
        {"k": 30, "v": "c"},
    ]
