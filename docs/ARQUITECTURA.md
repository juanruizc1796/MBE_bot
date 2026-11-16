# Arquitectura — Asistente MBE

> Documentado con el método **Views & Beyond** (Clements et al., 2010), el mismo que usan Tummers et al. (2021) para arquitecturas de referencia en sistemas de información en salud. Cada vista responde una pregunta distinta sobre el mismo sistema.

| Vista | Pregunta |
|---|---|
| [1. Contexto](#vista-1-contexto) | ¿Con quién interactúa el sistema? |
| [2. Descomposición](#vista-2-descomposición) | ¿De qué está hecho? |
| [3. Capas](#vista-3-capas) | ¿Quién puede usar a quién? |
| [4. Despliegue](#vista-4-despliegue) | ¿Dónde corre cada parte? |

Además: [seguridad](#seguridad-y-autenticación), [API](#api-rest), [esquema de BD](#esquema-de-base-de-datos) y [mapa tesis ↔ código](#mapa-tesis--código).

---

## Por qué esta arquitectura

El sistema separa presentación, API y motor para que cada parte evolucione y se despliegue por separado, y para que el token de sesión nunca llegue a JavaScript en el navegador:

- **Backend:** FastAPI asíncrono, con Pydantic y streaming SSE.
- **Frontend:** Next.js 16 (App Router), con un patrón BFF: el navegador nunca habla directamente con FastAPI.
- **Proxy:** Caddy 2, la única entrada pública.
- **Motor:** `rag_engine/` agrupa el RAG y la analítica en Python puro, sin dependencias web. El backend lo importa vía `backend/bootstrap.py`.

### Stakeholders

| Stakeholder | Preocupación | Decisión que la atiende |
|---|---|---|
| Estudiante | Respuestas fundamentadas, sin alucinaciones | Prompt estricto de 4 casos con citas obligatorias |
| Docente | Ver qué preguntan y quién necesita apoyo | Reporte de 4 niveles y alertas |
| Administrador | Actualizar corpus y usuarios sin reconstruir imágenes | Volúmenes Docker para `data/` y `users.yaml` |
| Investigador (tesis) | Auditar calidad del retrieval | Log por consulta con chunks, scores y latencias |

---

## Vista 1: Contexto

```
                     ┌──────────────────────────────┐
  [Estudiante] ─────▶│                              │─────▶ [OpenRouter / Groq]
  pregunta / chat ◀──│         ASISTENTE MBE        │◀───── tokens en streaming
                     │                              │
  [Docente] ────────▶│  (chat RAG + reporte docente)│─────▶ [Groq]
  reporte ◀──────────│                              │◀───── nombres de temas (LLM)
                     │                              │
  [Administrador] ──▶│                              │
  corpus · usuarios  └──────────────────────────────┘
```

| Entidad | Relación |
|---|---|
| **Estudiante** | Pregunta en lenguaje natural y recibe respuestas citadas |
| **Docente** | Consulta el reporte (y también puede usar el chat) |
| **OpenRouter / Groq** | Ejecutan el LLM del chat (`openai/gpt-oss-20b`), según `LLM_PROVIDER` |
| **Groq** | Nombra los clusters de temas y elige las preguntas destacadas del reporte |
| **Administrador** | Gestiona `users.yaml`, el corpus y los backups de `mbe_logs.db` |

---

## Vista 2: Descomposición

```
ASISTENTE MBE
├── frontend/ (Next.js)
│   ├── Páginas: /login · /chat · /reporte/{pulso,temas,estudiantes,estudiantes/[usuario]}
│   ├── BFF: app/api/* (lee la cookie httpOnly y reenvía con Bearer a FastAPI)
│   └── proxy.ts (redirige a /login sin cookie) · use-idle-logout (cierre por inactividad)
├── backend/ (FastAPI)
│   ├── routers/   auth · chat · conversations · report
│   ├── services/  auth_service · rag_service · history_service · report_service
│   └── dependencies.py  get_current_user · require_role
└── rag_engine/
    ├── app/core.py            Carga de recursos, búsqueda FAISS, cliente LLM
    ├── app/logger.py          Persistencia de consultas en SQLite
    ├── rag_langgraph/         Grafo retrieve → generate, historial y prompt
    ├── src/                   Pipeline offline (PDF → chunks → embeddings → FAISS)
    └── report_generator/modules/  topic_store · alerts · deltas · roster · retrieval_quality · temporal_analysis · student_detail …
```

| Módulo | Responsabilidad |
|---|---|
| **Frontend / BFF** | UI y sesión. Guarda el JWT en una cookie `httpOnly` y nunca lo expone a JavaScript |
| **Routers** | Contrato HTTP, validación Pydantic y control de rol |
| **Services** | Lógica de negocio: credenciales, ejecución del RAG, historial y agregación del reporte |
| **Motor RAG** | Recuperación semántica y generación fundamentada. Detalle en [RAG.md](RAG.md) |
| **Analítica** | Temas incrementales, alertas y KPIs. Detalle en [REPORTE_DOCENTE.md](REPORTE_DOCENTE.md) |
| **Persistencia** | `mbe_logs.db` (consultas y temas) y `users.yaml` (usuarios y roles) |

---

## Vista 3: Capas

```
┌─────────────────────────────────────────────┐   ┌────────────────┐
│ PRESENTACIÓN   Next.js (páginas + componentes)│   │   SEGURIDAD    │
├─────────────────────────────────────────────┤   │  (transversal) │
│ BFF            Route handlers /api/*          │◀─▶│ cookie httpOnly│
├─────────────────────────────────────────────┤   │ JWT HS256      │
│ API            FastAPI routers + services     │◀─▶│ RBAC por rol   │
├─────────────────────────────────────────────┤   │ bcrypt         │
│ DOMINIO        rag_engine (RAG + analítica)   │   │ secretos .env  │
├─────────────────────────────────────────────┤   │                │
│ DATOS          FAISS · CSV · SQLite · YAML    │◀─▶│                │
└─────────────────────────────────────────────┘   └────────────────┘
```

Cada capa solo usa la inmediatamente inferior. La presentación nunca toca FastAPI directamente: siempre pasa por el BFF.

---

## Vista 4: Despliegue

```
HOST (VPS Hetzner, Linux)                         puertos públicos 80 / 443
┌───────────────────────────────────────────────────────────────────────────┐
│ caddy (caddy:2-alpine) ── reverse_proxy ──▶ frontend:3000                 │
│                                                                           │
│ frontend (mbe-frontend, Node standalone) ── red interna ──▶ backend:8000  │
│   NEXT_PUBLIC_API_URL=http://backend:8000                                 │
│                                                                           │
│ backend (mbe-backend, Python + uvicorn)  — sin puertos expuestos al host  │
│   SentenceTransformer + FAISS en memoria (se cargan en el lifespan)       │
│   Volúmenes:                                                              │
│     ./rag_engine/data        → ro  (corpus + índice)                      │
│     ./rag_engine/data/logs   → rw  (mbe_logs.db)                          │
│     ./rag_engine/users.yaml  → ro  (usuarios)                             │
│   env_file: .env                                                          │
└───────────────────────────────────────────────────────────────────────────┘
          │ HTTPS
          ▼
   OpenRouter / Groq (LLM)
```

- El backend **no** se publica. Si Caddy enrutara `/api` directamente al backend, se saltaría el BFF y se rompería la autenticación por cookie.
- El `Caddyfile` actual escucha en `:80`. Para HTTPS hay que poner el dominio en el `Caddyfile` y activar `COOKIE_SECURE=true` en el frontend (ver [OPERACION.md](OPERACION.md)).

---

## Seguridad y autenticación

1. **Usuarios:** `rag_engine/users.yaml`. Cada uno tiene `email`, `name`, `rol` (`Docente`/`Estudiante`) y un hash bcrypt.
2. **Login:** `POST /api/auth/login` verifica el bcrypt y emite un **JWT HS256** firmado con `JWT_SECRET_KEY` que expira a las **24 h**. El payload es `{sub, role, name, exp}`.
3. **BFF:** `frontend/app/api/auth/login/route.ts` guarda el JWT en una cookie `httpOnly`, `sameSite=lax`, con `secure` controlado por `COOKIE_SECURE`.
4. **RBAC:**
   - Frontend: `proxy.ts` exige la cookie y `/reporte/*` exige el rol `Docente`.
   - Backend: `Depends(get_current_user)` y `require_role("Docente")` responden `401`/`403`.
5. **Inactividad:** `use-idle-logout` cierra la sesión tras **30 min** sin actividad.

---

## API REST

Todas las rutas llevan el prefijo `/api`. El frontend las consume a través del BFF.

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/auth/login` | público | Valida credenciales y devuelve el JWT y el rol |
| GET | `/auth/me` | autenticado | Identidad del usuario actual |
| POST | `/chat` | autenticado | Pregunta + `conversation_id`. Responde con stream SSE de tokens |
| GET | `/conversations` | autenticado | Conversaciones del usuario, de la más reciente a la más antigua |
| GET | `/conversations/{id}` | autenticado | Mensajes de una conversación |
| POST | `/conversations` | autenticado | Crea una conversación nueva |
| GET | `/report/meta` | Docente | Rango de fechas disponible |
| GET | `/report/pulso?desde&hasta` | Docente | Nivel 1: KPIs con delta, sparkline, heatmap y alertas |
| GET | `/report/temas?desde&hasta` | Docente | Nivel 2: temas, preguntas destacadas y evolución semanal |
| POST | `/report/temas/generate?desde&hasta` | Docente | Corre el clustering incremental. Requiere `GROQ_API_KEY` (503 si falta, 422 si hay menos de 5 preguntas) |
| GET | `/report/estudiantes?desde&hasta` | Docente | Nivel 3: roster, histograma, silenciosos y cuentas nunca usadas |
| GET | `/report/estudiantes/{usuario}` | Docente | Nivel 4: detalle individual |

Con el backend corriendo en local, la documentación interactiva está en `http://localhost:8000/docs`.

---

## Esquema de base de datos

`rag_engine/data/logs/mbe_logs.db` (SQLite). El backend inicializa las tablas al arrancar.

**`consultas`**: una fila por pregunta (`rag_engine/app/logger.py`).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER PK | — |
| `timestamp` | DATETIME | UTC |
| `usuario` | TEXT | username (correo) |
| `session_id` | TEXT | id de la conversación |
| `pregunta` / `respuesta` | TEXT | — |
| `chunks_extraidos` | TEXT (JSON) | chunks recuperados con sus metadatos |
| `scores_similitud` | TEXT (JSON) | similitud coseno de cada chunk |
| `latencia_embedding` / `_retrieval` / `_llm` / `_total` | REAL | segundos por etapa |

**Temas** (`report_generator/modules/topic_store.py`):

| Tabla | Propósito | Columnas clave |
|---|---|---|
| `temas` | Un tema por fila | `rol`, `nombre`, `es_residual`, `centroide` (JSON 384D), `n_preguntas` |
| `tema_preguntas` | Asignación pregunta → tema | `pregunta_norm` (UNIQUE), `tema_id`, `embedding`, `primera_consulta_id` |
| `temas_scope_estado` | Cursor incremental por scope | `ultimo_consulta_id`, `ultima_corrida_en`, `destacadas_json` |

---

## Mapa tesis ↔ código

| Concepto | Dónde | Detalle |
|---|---|---|
| Corpus | `rag_engine/src/preprocess_corpus.py` | Guyatt 2015 + Dans 2017. Ventanas de ~100 palabras con 20 % de solapamiento, acotadas a la página |
| Representación vectorial | `rag_engine/src/indexing.py` | MiniLM-L12-v2, d = 384, normalización L2 |
| Búsqueda | `rag_engine/app/core.py` | FAISS `IndexFlatIP` (coseno exacto), top-k = 3 |
| Pipeline RAG | `rag_engine/rag_langgraph/app_langgraph.py` | LangGraph `retrieve → generate` con streaming |
| Seguimiento conversacional | `_query_retrieval()` | Combina la última pregunta del usuario con la actual |
| Mitigación de alucinaciones | prompt en `app_langgraph.py` | 4 casos, citas obligatorias y frase fija cuando no hay información |
| Inferencia | `rag_engine/app/core.py` | `gpt-oss-20b`, `temperature=0.2`, `reasoning_effort="low"` |
| Modelado de temas | `report_generator/modules/topic_store.py` | Centroides (umbral ≥ 0.55) + UMAP/HDBSCAN sobre el residual + nombres por LLM |
| Alertas pedagógicas | `report_generator/modules/alerts.py` | Tema en alza, retrieval débil, silenciosos, nunca usados, concentración |
| Observabilidad | `app/logger.py`, `backend/services/history_service.py` | Chunks, scores y latencias por etapa |
| Seguridad | `backend/services/auth_service.py`, `frontend/proxy.ts` | bcrypt, JWT 24 h en cookie httpOnly, RBAC |
| Evaluación | `evaluation/` | RAGAS (`Evaluacion_RAGAS/`) y encuestas de aceptación a docentes y estudiantes |

## Referencias

- Clements, P. et al. *Documenting Software Architectures: Views and Beyond*, 2nd ed. Addison-Wesley, 2010.
- Tummers, J. et al. *Designing a reference architecture for health information systems*. BMC Med Inform Decis Mak 21, 210 (2021).
