# Asistente MBE — Medicina Basada en la Evidencia
### Pontificia Universidad Javeriana · Facultad de Medicina

Asistente conversacional **RAG** que responde preguntas de Medicina Basada en la Evidencia citando autor, libro y página del corpus del curso. También incluye un **reporte docente** de analítica de aprendizaje (KPIs, temas, alertas y seguimiento por estudiante).

> **Autores:** Juan Ruiz · Yibby González 
> **Profesores:** Juan Pajaro · Fabián Gil
>
> Proyecto de Tesis de Maestría en Inteligencia Artificial.

---

## Qué hace

| Para | Qué ofrece |
|---|---|
| **Estudiantes** (`/chat`) | Chat con streaming. Las respuestas salen solo del corpus (Guyatt 2015 y Dans 2017), con citas `(Autor, Libro, Año — pág. X)`. Rechaza preguntas fuera del dominio y guarda el historial de conversaciones. |
| **Docentes** (`/reporte`) | Cuatro niveles: Pulso del curso, Temas, Estudiantes y Estudiante individual. Incluye alertas pedagógicas automáticas. |

## Arquitectura en una línea

```
Navegador → Caddy (:80) → Next.js 16 (UI + BFF /api/*) → FastAPI (:8000, red interna) → rag_engine (LangGraph + FAISS + LLM) / SQLite
```

El LLM es `openai/gpt-oss-20b`, vía OpenRouter (proveedor por defecto) o Groq (respaldo). Los detalles están en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

## Puesta en marcha rápida (Docker)

```bash
# 1. Variables de entorno (ver docs/OPERACION.md para la lista completa)
cp .env.example .env   # o crear .env a mano: LLM_PROVIDER, OPENROUTER_API_KEY, GROQ_API_KEY, JWT_SECRET_KEY

# 2. El corpus procesado y el índice FAISS ya vienen en rag_engine/data/processed/.
#    Solo hay que regenerarlos si cambian los PDFs (ver docs/RAG.md).

# 3. Levantar todo
docker compose up -d --build
```

La app queda en `http://localhost`. Para desarrollo local sin Docker, ver [docs/OPERACION.md](docs/OPERACION.md#desarrollo-local).

## Estructura del repositorio

```
RAG_langraph/
├── backend/            API FastAPI: routers (auth, chat, conversations, report) y services
├── frontend/           Next.js 16 + React 19 + Tailwind v4: /login, /chat, /reporte/*, BFF en app/api/*
├── rag_engine/         Núcleo Python que reutiliza el backend
│   ├── app/            core.py (recursos, FAISS, cliente LLM) · logger.py (SQLite)
│   ├── rag_langgraph/  Grafo LangGraph retrieve → generate y prompt MBE
│   ├── src/            Pipeline offline: preprocess_corpus.py · indexing.py
│   ├── report_generator/ Analítica del reporte docente (temas, alertas, KPIs, roster)
│   ├── data/           raw/ (PDFs) · processed/ (CSV + índice) · logs/ (mbe_logs.db)
│   └── users.yaml      Usuarios, roles y hashes bcrypt
├── evaluation/         Evaluación RAGAS y análisis de encuestas de aceptación
├── mockups/            Mockups HTML de referencia visual (chat y reporte)
├── docs/               Documentación (ver abajo)
├── docker-compose.yml  backend + frontend + caddy
└── Caddyfile           Reverse proxy → frontend:3000
```

## Documentación

| Documento | Contenido |
|---|---|
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Vistas de arquitectura (Views & Beyond), seguridad, API, esquema de BD y mapa tesis ↔ código |
| [docs/RAG.md](docs/RAG.md) | Corpus, preprocesamiento, embeddings, pipeline LangGraph, prompt y proveedores LLM |
| [docs/REPORTE_DOCENTE.md](docs/REPORTE_DOCENTE.md) | Funcionalidad de los 4 niveles y algoritmos de analítica (temas, alertas, KPIs) |
| [docs/OPERACION.md](docs/OPERACION.md) | Desarrollo local, despliegue, variables de entorno, usuarios, logs, backups y rollback |
## Stack

FastAPI · Pydantic · PyJWT · bcrypt · LangGraph · sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) · FAISS CPU · OpenRouter / Groq · UMAP + HDBSCAN · SQLite · Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · Docker Compose · Caddy 2
