import os
from dotenv import load_dotenv
load_dotenv()
from typing import Generator
# Algo
import faiss
import numpy as np
import pandas as pd
from groq import Groq
from openai import OpenAI
from sentence_transformers import SentenceTransformer

ARTICLES_PATH = "data/processed/articulos_total.csv"
EMBEDDINGS_PATH = "data/processed/models/embeddings_total.npy"
FAISS_PATH = "data/processed/models/faiss_index_total.bin"

EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
GROQ_MODEL = "openai/gpt-oss-20b"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _build_llm_client():
    """Plan A/Plan B: LLM_PROVIDER en .env elige el proveedor sin tocar el resto
    del pipeline (mismo modelo openai/gpt-oss-20b, misma interfaz chat.completions).
    Rollback en caliente: LLM_PROVIDER=groq en .env + reiniciar contenedores."""
    provider = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY no encontrada en variables de entorno.")
        return Groq(api_key=api_key)

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY no encontrada en variables de entorno.")
        return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)

    raise ValueError(
        f"LLM_PROVIDER='{provider}' invalido. Usar 'openrouter' o 'groq'."
    )

# gpt-oss: Groq recomienda NO usar mensaje "system" con estos modelos (lo tratan
# como "developer", de menor prioridad que un "system" oculto que el propio modelo
# inyecta) y meter todas las instrucciones en el mensaje "user". Por eso ya no hay
# un _SYSTEM_PROMPT separado: las reglas viven todas en el prompt que arma
# app_langgraph.py y se envian como un unico mensaje "user".


def load_resources():
    df = pd.read_csv(ARTICLES_PATH)
    embeddings = np.load(EMBEDDINGS_PATH)
    index = faiss.read_index(FAISS_PATH)
    encoder = SentenceTransformer(EMBED_MODEL_NAME)

    groq_client = _build_llm_client()

    return df, embeddings, index, encoder, groq_client


def buscar_articulos(query, top_k=3, *, encoder, index, df):
    """Recupera los top_k articulos mas relevantes para la query."""
    q_emb = encoder.encode([query], normalize_embeddings=True)
    scores, idxs = index.search(np.array(q_emb).astype("float32"), top_k)
    resultados = df.iloc[idxs[0]].copy()
    resultados["score"] = scores[0]
    return resultados


def call_ollama(prompt: str, *, ollama_client) -> str:
    """Llamada sincronica via Groq u OpenRouter (segun LLM_PROVIDER) — interfaz
    compatible con rama main.

    reasoning_effort="low": esto es QA extractivo sobre 3 chunks, no requiere
    razonamiento multi-paso, y con gpt-oss los tokens de razonamiento salen del
    mismo presupuesto que max_tokens — en "medium" (default) se comian el budget
    y la respuesta final quedaba truncada o el modelo devolvia el fallback corto
    en vez de la respuesta completa.

    include_reasoning va en extra_body (y no como kwarg top-level) porque el
    SDK de openai (usado para OpenRouter) no lo tiene tipado en create() y
    lanzaria TypeError; extra_body si existe en ambos SDKs (groq y openai) y
    termina en el mismo JSON."""
    completion = ollama_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2048,
        reasoning_effort="low",
        extra_body={"include_reasoning": False},
    )
    return completion.choices[0].message.content


def call_ollama_stream(prompt: str, *, ollama_client) -> Generator[str, None, None]:
    """Streaming via Groq u OpenRouter (segun LLM_PROVIDER) — interfaz compatible
    con rama main. Ver docstring de call_ollama sobre extra_body."""
    stream = ollama_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2048,
        reasoning_effort="low",
        extra_body={"include_reasoning": False},
        stream=True,
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield token
