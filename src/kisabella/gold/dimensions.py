"""Gold: construye las cuatro dimensiones derivadas del Star Schema.

dim_product (PK brand)     : description, size, volume, classification
dim_vendor  (PK vendor_no) : vendor_name
dim_store   (PK store_id)  : city
dim_date    (PK date_id)   : date, year, month, quarter
"""
import logging
from datetime import date
import polars as pl

log = logging.getLogger(__name__)


def build_dim_product(price_catalog: pl.DataFrame) -> pl.DataFrame:
    dim = (
        price_catalog
        .select("Brand", "Description", "Size", "Volume", "Classification")
        .unique(subset=["Brand"])
        .rename({
            "Brand": "brand",
            "Description": "description",
            "Size": "size",
            "Volume": "volume",
            "Classification": "classification",
        })
        .sort("brand")
    )
    log.info("gold dim_product %d rows", dim.height)
    return dim


def build_dim_vendor(sales: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame:
    dim = (
        sales.lazy()
        .select(
            pl.col("VendorNo").alias("vendor_no"),
            pl.col("VendorName").alias("vendor_name"),
        )
        .filter(pl.col("vendor_no").is_not_null())
        .unique(subset=["vendor_no"])
        .sort("vendor_no")
        .collect()
    )
    log.info("gold dim_vendor  %d rows", dim.height)
    return dim


def build_dim_store(beg_inv: pl.DataFrame, end_inv: pl.DataFrame) -> pl.DataFrame:
    # Unión de inventario inicial y final: PEMBROKE (store 81) abrió a mediados
    # de 2016, así que solo aparece en end_inv. Una tienda cerrada sería el
    # caso simétrico.
    rename = {"Store": "store_id", "City": "city"}
    dim = (
        pl.concat([
            beg_inv.select(rename.keys()).rename(rename),
            end_inv.select(rename.keys()).rename(rename),
        ])
        .unique(subset=["store_id"])
        .sort("store_id")
    )
    log.info("gold dim_store   %d rows", dim.height)
    return dim


def build_dim_date(
    start: date = date(2016, 1, 1),
    end: date = date(2016, 12, 31),
) -> pl.DataFrame:
    dim = (
        pl.DataFrame({"date": pl.date_range(start, end, "1d", eager=True)})
        .with_columns(
            pl.int_range(pl.len()).alias("date_id"),
            pl.col("date").dt.year().alias("year"),
            pl.col("date").dt.month().alias("month"),
            pl.col("date").dt.quarter().alias("quarter"),
        )
        .select("date_id", "date", "year", "month", "quarter")
    )
    log.info("gold dim_date    %d rows  span=%s..%s", dim.height, start, end)
    return dim
