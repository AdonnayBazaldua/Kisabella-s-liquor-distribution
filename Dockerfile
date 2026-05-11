FROM python:3.12-slim

WORKDIR /app

# Deps de runtime fijadas inline para cache rápido de capas; pyproject sigue
# siendo la fuente de verdad para desarrollo, esta lista replica su
# [project.dependencies].
RUN pip install --no-cache-dir \
    polars==1.18.0 \
    duckdb==1.1.3 \
    streamlit==1.41.1 \
    altair==5.5.0

COPY src/ ./src/
COPY .streamlit/ ./.streamlit/

ENV PYTHONPATH=/app/src \
    POLARS_NEW_STREAMING=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8501

# Corre el pipeline una vez y luego inicia Streamlit. El pipeline es idempotente;
# las tablas DuckDB son CREATE OR REPLACE así que re-ejecutar es seguro.
CMD ["bash", "-c", "python -m kisabella.pipeline && streamlit run src/kisabella/dashboard/app.py --server.port=8501 --server.address=0.0.0.0"]
