"""Rutas del proyecto y schemas Polars para los 6 CSVs origen.

Única fuente de verdad — sin lógica.
"""
from pathlib import Path
import polars as pl

# Rutas (resueltas relativo a la raíz del repo por defecto)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "Data"
PARQUET_DIR = REPO_ROOT / "parquet_cache"
WAREHOUSE_DIR = REPO_ROOT / "warehouse"
WAREHOUSE_PATH = WAREHOUSE_DIR / "gold.duckdb"

# Nombres de los CSVs origen
CSV_SALES = "SalesFINAL12312016.csv"
CSV_PURCHASES = "PurchasesFINAL12312016.csv"
CSV_PRICE_CATALOG = "2017PurchasePricesDec.csv"
CSV_BEG_INV = "BegInvFINAL12312016.csv"
CSV_END_INV = "EndInvFINAL12312016.csv"
CSV_INVOICES = "InvoicePurchases12312016.csv"

# Schemas Polars — explícitos, sin inferSchema
SCHEMA_SALES = {
    "InventoryId": pl.String,
    "Store": pl.Int32,
    "Brand": pl.Int32,
    "Description": pl.String,
    "Size": pl.String,
    "SalesQuantity": pl.Int32,
    "SalesDollars": pl.Float64,
    "SalesPrice": pl.Float64,
    "SalesDate": pl.Date,
    "Volume": pl.String,
    "Classification": pl.Int8,
    "ExciseTax": pl.Float64,
    "VendorNo": pl.Int32,
    "VendorName": pl.String,
}

SCHEMA_PURCHASES = {
    "InventoryId": pl.String,
    "Store": pl.Int32,
    "Brand": pl.Int32,
    "Description": pl.String,
    "Size": pl.String,
    "VendorNumber": pl.Int32,
    "VendorName": pl.String,
    "PONumber": pl.Int64,
    "PODate": pl.Date,
    "ReceivingDate": pl.Date,
    "InvoiceDate": pl.Date,
    "PayDate": pl.Date,
    "PurchasePrice": pl.Float64,
    "Quantity": pl.Int32,
    "Dollars": pl.Float64,
    "Classification": pl.Int8,
}

SCHEMA_PRICE_CATALOG = {
    "Brand": pl.Int32,
    "Description": pl.String,
    "Price": pl.Float64,
    "Size": pl.String,
    "Volume": pl.String,
    "Classification": pl.Int8,
    "PurchasePrice": pl.Float64,
    "VendorNumber": pl.Int32,
    "VendorName": pl.String,
}

SCHEMA_BEG_INV = {
    "InventoryId": pl.String,
    "Store": pl.Int32,
    "City": pl.String,
    "Brand": pl.Int32,
    "Description": pl.String,
    "Size": pl.String,
    "onHand": pl.Int32,
    "Price": pl.Float64,
    "startDate": pl.Date,
}

SCHEMA_END_INV = {
    "InventoryId": pl.String,
    "Store": pl.Int32,
    "City": pl.String,
    "Brand": pl.Int32,
    "Description": pl.String,
    "Size": pl.String,
    "onHand": pl.Int32,
    "Price": pl.Float64,
    "endDate": pl.Date,
}

SCHEMA_INVOICES = {
    "VendorNumber": pl.Int32,
    "VendorName": pl.String,
    "InvoiceDate": pl.Date,
    "PONumber": pl.Int64,
    "PODate": pl.Date,
    "PayDate": pl.Date,
    "Quantity": pl.Int32,
    "Dollars": pl.Float64,
    "Freight": pl.Float64,
    "Approval": pl.String,
}
