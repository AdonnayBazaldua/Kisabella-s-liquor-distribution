# Kisabella's LLC — Liquor Distribution Analytics

Pipeline ETL end-to-end que ingesta más de 1.7 GB de transacciones para el año 2016 de una cadena de licores y expone un dashboard analítico con los **Top 10 productos y marcas más rentables** por Profit ($) y Margin (%).


## Cómo correrlo

### Opción 1 — Docker 

Necesita el dataset descomprimido en `./Data/` (ver sección **Datos**).

```bash
docker compose up --build
```

Espera ~5 min la primera vez (build de imagen + pipeline sobre 12.8M filas). Después abre <http://localhost:8501>.

### Opción 2 — Desarrollo local

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python -m kisabella.pipeline                          # ETL completo (~90s)
streamlit run src/kisabella/dashboard/app.py          # dashboard local
```

### Tests

```bash
pytest tests/test_smoke.py -v
```

Smoke integral: arma dataset sintético, corre el pipeline completo, valida integridad referencial, aritmética de profit, exclusión de anomalías y renderizado del dashboard. ~3 segundos.

## Arquitectura

Medallion (Bronze → Silver → Gold) sobre **Polars + DuckDB + Streamlit**, empaquetado en un único contenedor Docker.

```
Data/*.csv 
       │
       ▼
Bronze   scan_csv → sink_parquet  (streaming, memoria acotada)
       │
       ▼
Silver   flag → cost basis → enriched  (lazy chain → sink_parquet)
       │
       ▼
Gold     fact_sales + 4 dims (product, vendor, store, date) → DuckDB
       │
       ▼
Streamlit dashboard  (filtros + 4 rankings Top 10 + KPIs auditables)
```

- **Bronze**: schema explícito; lectura streaming con `scan_csv` + `sink_parquet` (el sales.csv de 1.6 GB nunca se carga completo en RAM).
- **Silver**: marca devoluciones (`SalesQuantity < 0`) y anomalías (`SalesPrice = 0 AND Qty > 0`); calcula cost basis como avg ponderado de PurchasePrice por InventoryId; computa revenue y profit gross+net (excluyendo `ExciseTax`).
- **Gold**: Star Schema en `gold.duckdb`. fact_sales materializado con DuckDB `read_parquet` directo (sin pasar por memoria Python).
- **Dashboard**: filtros multiselect de tienda y rango de fechas; 4 tablas Top 10 (Producto/Marca × Profit/Margin) con barras horizontales; KPIs sidebar (revenue, profit, devoluciones, anomalías excluidas, cost-missing).

## Stack y por qué?

Se propuso en un inciio el uso de Apache Spark + PostgreSQL pero tras una revista  alos datos se decidió cambiar a **Polars + DuckDB** porque:

- 1.7 GB en en un archivo no justifica el overhead de JVM ni el cluster manager de Spark que ademas e smás demantante computacionalmente; el pipeline corre 5–10× más rápido sin él.
- DuckDB es columnar y embebido — sirve los 4 queries analíticos del dashboard con latencia <100 ms sin necesidad de un servicio Postgres separado.
- Imagen Docker resultante: 1 GB (vs ~1.5–2 GB con JVM + Postgres).

## Términos clave

- **Producto** ≡ `Brand` (entero que identifica el SKU; el dataset tiene 12,261 brands únicos, cada uno con `(Description, Size, Volume)` única)
- **Marca** ≡ `VendorName` (proveedor/distribuidor)
- **Profit canónico** = `profit_net` = `(SalesDollars − ExciseTax) − cost_unit × SalesQuantity`
- **Margin agregado** = `SUM(profit_net) / SUM(revenue_net) × 100` (ponderado por revenue, **no** AVG por fila)
- **Devolución**: `SalesQuantity < 0` (incluida; el dataset 2016 entregado tiene 0 devoluciones empíricamente)
- **Anomalía**: `SalesPrice = 0 AND SalesQuantity > 0` (excluida del ranking, contada en KPI)

## Estructura del repositorio

```
src/kisabella/
├── config.py                       # rutas + schemas Polars
├── bronze/ingest.py                # CSV → Parquet (streaming)
├── silver/{clean,enrich}.py        # flagging + cost basis + profit
├── gold/{dimensions,fact,load}.py  # star schema → DuckDB
├── pipeline.py                     # orchestrator
└── dashboard/{queries,app}.py      # queries DuckDB + Streamlit UI

tests/test_smoke.py                 # smoke test integral
.streamlit/config.toml              # tema dashboard (data-dense, blue+amber)
docker-compose.yml + Dockerfile     # deploy en un único contenedor
pyproject.toml                      # dependencies
```

## Métricas de salida (sobre el dataset completo)

```
fact_sales      : 12,825,363 filas
dim_product     :     12,261 productos
dim_vendor      :        127 proveedores
dim_store       :         80 tiendas
dim_date        :        366 días (2016 bisiesto)

revenue_gross   : $452,062,952
revenue_net     : $433,088,711
profit_net      : $119,703,411
margin_net      :       27.64%
top product     : Jack Daniels No 7 Black ($1.1M profit)
top vendor      : Diageo North America Inc ($14.9M profit)
```

## Datos

El directorio `Data/` (1.7 GB de CSVs originales) **no está incluido** en el repositorio porque excede los límites estándar de GitHub. Para ejecutar el pipeline necesitas colocar los siguientes archivos en `./Data/`:

```
Data/
├── SalesFINAL12312016.csv          # 1.6 GB — ventas (12.8M filas)
├── PurchasesFINAL12312016.csv      # 384 MB — compras (2.4M filas)
├── 2017PurchasePricesDec.csv       # 1.2 MB — catálogo de precios
├── BegInvFINAL12312016.csv         # 19 MB  — inventario inicial
├── EndInvFINAL12312016.csv         # 21 MB  — inventario final
└── InvoicePurchases12312016.csv    # 578 KB — facturas
```

El dataset original es público y puede descargarse desde https://www.pwc.com/us/en/careers/university-relations/data-and-analytics-case-studies-files.html 

## Licencia

MIT — ver `LICENSE`.
