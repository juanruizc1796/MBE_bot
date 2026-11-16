# Motor RAG — corpus, recuperación y generación

Código en `rag_engine/`. El backend lo reutiliza tal cual (`backend/services/rag_service.py`).

```
OFFLINE (solo cuando cambia el corpus)
  data/raw/*.pdf ──preprocess_corpus.py──▶ processed/articulos_total.csv ──indexing.py──▶ models/embeddings_total.npy + faiss_index_total.bin

ONLINE (cada pregunta)
  pregunta + historial ─▶ _query_retrieval ─▶ retrieve (MiniLM + FAISS top-3) ─▶ generate (prompt MBE + LLM stream) ─▶ SSE ─▶ log SQLite
```

---

## 1. Corpus

| Obra | Archivo en `data/raw/` |
|---|---|
| Guyatt G. et al. *Users' Guides to the Medical Literature*, 3rd ed. McGraw-Hill, 2015 | `Users Guides to the medical literature_….pdf` |
| Dans A. L. et al. *Painless Evidence-Based Medicine*, 2nd ed. Wiley-Blackwell, 2017 | `Painless Evidence-Based Medicine.pdf` |

Los PDFs, el CSV procesado y el índice FAISS están versionados en el repo. No hay que regenerarlos para desplegar.

## 2. Preprocesamiento — `src/preprocess_corpus.py`

- **Extracción** con `pdfplumber`. Cada página se libera (`p.close()`) para evitar quedarse sin memoria con PDFs de más de 1000 páginas.
- **Normalización** de `\r`, espacios, tabulaciones y saltos de línea repetidos.
- **Límite de páginas:** `PAGINA_LIMITE = {"Painless Evidence-Based Medicine.pdf": 167}`. El PDF de Dans trae una copia del libro de Guyatt a partir de la página 168. Sin este límite, esos fragmentos se citarían como si fueran de Dans.
- **Chunking por ventana deslizante, siempre dentro de una página.** Así cada chunk conserva su número de página real para citarlo.
  - `CHUNK_SIZE = 100` (palabras aprox.) · `CHUNK_OVERLAP = 0.2` · `MIN_CHARS = 50`
- **Salida:** `data/processed/articulos_total.csv` con las columnas `chunk_id, texto, tipo, pagina, fuente_pdf, referencia`.

## 3. Embeddings e índice — `src/indexing.py`

- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones, multilingüe), con vectores normalizados L2.
- Índice: FAISS `IndexFlatIP`. Como los vectores están normalizados, el producto interno es igual a la similitud coseno, y la búsqueda es exacta.
- Salida: `data/processed/models/embeddings_total.npy` y `faiss_index_total.bin`.

### Regenerar el índice

```bash
cd rag_engine
python src/preprocess_corpus.py
python src/indexing.py
docker compose restart backend   # el backend carga el índice al arrancar
```

---

## 4. Pipeline online — `rag_langgraph/app_langgraph.py`

Es un `StateGraph` de LangGraph con dos nodos: `retrieve → generate`. El estado es `{query, context, response}`.

**Seguimiento conversacional**
- `_query_retrieval()`: la búsqueda en FAISS usa *la última pregunta del usuario + la pregunta actual*. Esto resuelve preguntas con pronombres o elipsis («¿y sus componentes?»). Se descartó concatenar también la respuesta previa porque un párrafo largo diluye el embedding.
- `_preparar_historial()`: el prompt recibe los últimos **3 intercambios** (6 mensajes).

**`retrieve`:** codifica la query, busca el **top-3** en FAISS y arma el bloque `CONTEXTO`, con la referencia `(Autor, Libro, Año — pág. X)` de cada chunk.

**`generate`:** junta historial, reglas y contexto y llama al LLM en streaming.

`responder_stream_logged()` es la variante que usa el backend:
- El **primer `yield`** devuelve metadatos: chunks, scores, `lat_embedding`, `lat_retrieval` y `trace_id`.
- Los siguientes devuelven tokens.
- Al terminar, `history_service` guarda la fila en `consultas`.

## 5. Prompt: árbol de 4 casos

| Caso | Condición | Comportamiento |
|---|---|---|
| 1 | Saludo o cortesía | Responde cordialmente y ofrece ayuda en MBE |
| 2 | Pregunta fuera de MBE | 1–2 frases indicando el alcance y los temas que sí cubre |
| 3 | Pregunta de MBE y el contexto sirve | Responde **solo** con el contexto y cita `(Autor, Libro, Año — pág. X)` |
| 4 | Pregunta de MBE sin información en el contexto | Responde literalmente: *«No hay suficiente información en los textos proporcionados para responder la pregunta.»* |

El prompt prohíbe exponer el razonamiento interno (por ejemplo, «Esto corresponde al caso 3…»).

## 6. Proveedor LLM — `app/core.py`

| `LLM_PROVIDER` | Cliente | Modelo |
|---|---|---|
| `openrouter` (por defecto) | SDK de OpenAI → `https://openrouter.ai/api/v1` | `openai/gpt-oss-20b` |
| `groq` (respaldo) | SDK de Groq | `openai/gpt-oss-20b` |

Parámetros: `temperature=0.2`, `max_tokens=2048`, `reasoning_effort="low"` y `extra_body={"include_reasoning": False}`.

`reasoning_effort` va en `low` porque en `medium` los tokens de razonamiento consumían el presupuesto de `max_tokens` y la respuesta salía truncada. `include_reasoning: False` evita que el razonamiento se filtre en el stream.

Cambiar de proveedor: ver [OPERACION.md](OPERACION.md#cambiar-de-proveedor-llm).

---

## 7. Evaluación

| Carpeta | Contenido |
|---|---|
| `evaluation/Evaluacion_RAGAS/RAGAS_MBEbot.ipynb` | Métricas RAGAS sobre las respuestas del sistema |
| `evaluation/Analisis_Estadistico_Encuestas/{docentes,estudiantes}/` | Encuestas de aceptación (seudonimizadas) y su análisis estadístico |

## 8. Otros archivos de `rag_engine/`

| Archivo | Estado |
|---|---|
| `langgraph.json` | Config para LangGraph Studio (`graph` en `app_langgraph.py`) |
| `src/rag_simple.py` | Script independiente de prueba con un LLM local (Ollama). El backend no lo usa |
| `test.py` | Prueba manual de `responder()` |
| `report_generator/generate_report.py` | CLI que exporta el reporte como HTML estático. El reporte web solo usa `modules/` |
