# Construir desde la raíz del repo (contexto = .), porque el backend
# importa directamente el código de rag_engine/ sin reimplementarlo.
FROM python:3.12-slim

WORKDIR /app

# Sin esto, stdout queda con buffer de bloque (no de línea) al no estar
# conectado a una TTY, y los print() de logging por request no aparecen en
# `docker logs` en tiempo real — se quedan atascados en el buffer.
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- CAPA 1: torch por separado (~200 MB en CPU) ---
# Capa independiente para que Docker la cachee aunque cambien las
# demás dependencias.
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.6.0+cpu

# --- CAPA 2: dependencias (rag_engine/requirements.txt + backend/requirements.txt) ---
COPY rag_engine/requirements.txt rag_engine/requirements.txt
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# --- CAPA 3: modelo de embeddings bakeado en la imagen ---
ENV SENTENCE_TRANSFORMERS_HOME=/app/models
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); \
print('Modelo de embeddings descargado correctamente.')"

# --- CAPA 4: código (cambia frecuentemente, va al final) ---
# rag_engine/data/ NO se copia: se monta como volumen en runtime
# (index FAISS + CSV de solo lectura, logs de lectura/escritura).
COPY backend/ backend/
COPY rag_engine/app rag_engine/app
COPY rag_engine/rag_langgraph rag_engine/rag_langgraph
COPY rag_engine/report_generator rag_engine/report_generator
COPY rag_engine/src rag_engine/src

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
