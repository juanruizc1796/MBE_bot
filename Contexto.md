# Contexto General del Proyecto: Asistente MBE & Plataforma de Analítica Pedagógica
## Rama: `migration-nextjs-fastapi`

---

## 1. Resumen Ejecutivo y Marco de la Tesis

### 1.1. Contexto Académico
Este proyecto constituye el núcleo tecnológico y experimental de una **Tesis de Maestría en Inteligencia Artificial** de la **Pontificia Universidad Javeriana** (Bogotá, Colombia), desarrollada en articulación interdisciplinaria con la **Facultad de Medicina**.

### 1.2. Problema que Resuelve
La enseñanza de la **Medicina Basada en la Evidencia (MBE)** en educación médica superior enfrenta dos grandes retos:
1. **Para los estudiantes:** Necesidad de consultar literatura metodológica densa (diseño de estudios, jerarquía de la evidencia, medidas de asociación, riesgo relativo, odds ratio, sesgos, revisiones sistemáticas) obteniendo respuestas inmediatas, fidedignas y estrictamente fundamentadas en fuentes académicas oficiales, sin sufrir las *alucinaciones* o imprecisiones conceptuales típicas de los LLMs comerciales generalistas.
2. **Para los docentes:** Falta de visibilidad y herramientas de *Learning Analytics* / observabilidad para comprender en tiempo real qué dudas tienen los estudiantes, qué temas presentan mayor dificultad o *retrieval débil*, cómo se distribuye el esfuerzo del curso y qué alumnos requieren intervención pedagógica oportuna por inactividad o rezago.

### 1.3. Solución Implementada
El sistema integra una solución dual de extremo a extremo:
- **Asistente Clínico-Educativo RAG (Retrieval-Augmented Generation):** Motor conversacional orquestado con **LangGraph**, recuperación vectorial densa con **FAISS** y embeddings multilingües (**MiniLM-L12**), e inferencia en streaming con LLMs de última generación (**LLaMA 3.1 8B / GPT-OSS 20B**). El asistente cita estrictamente autor, libro y página exacta, rechaza consultas fuera de dominio y previene alucinaciones.
- **Plataforma Analítica y Dashboard Docente (4 Niveles de Observabilidad):** Sistema analítico integral que procesa los registros históricos de consultas mediante **modelado de temas no supervisado e incremental (UMAP + HDBSCAN + LLM Labeling)**, cálculo de KPIs con deltas porcentuales respecto a períodos previos, mapas de calor de actividad temporal y motores de alerta temprana de estudiantes silenciosos y temas críticos.

### 1.4. Justificación de la Migración (`migration-nextjs-fastapi`)
El prototipo inicial fue concebido como un monolito en **Streamlit**. Aunque ágil para pruebas de concepto, presentaba limitaciones estructurales:
- Re-ejecución completa del script ante cualquier interacción del usuario (*rerun state*).
- Dificultad para desacoplar interfaces de usuario modernas, responsivas y accesibles.
- Acoplamiento rígido entre la lógica de recuperación RAG y la capa de presentación.
- Imposibilidad de implementar patrones de seguridad avanzados basados en tokens JWT aislados en cookies `httpOnly`.

La rama **`migration-nextjs-fastapi`** transforma el sistema en una **arquitectura desacoplada de nivel de producción**:
- **Backend API:** FastAPI (asíncrono, tipado estricto con Pydantic, modular, streaming SSE).
- **Frontend App:** Next.js 16 (App Router, React 19, TypeScript, Tailwind CSS v4, Server/Client Components, BFF pattern).
- **Proxy Inverso:** Caddy 2 (enrutamiento seguro, terminación HTTP/HTTPS, red Docker interna).
- **Persistencia y Memoria:** SQLite optimizado para observabilidad y taxonomía temática incremental, FAISS para búsqueda vectorial en memoria.

---

## 2. Arquitectura Global del Sistema

### 2.1. Diagrama de Arquitectura por Capas

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLIENTE (Navegador Web)                          │
│        Estudiantes: Interfaz de Chat  ·  Docentes: Reporte Analítico        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / HTTPS (:80, :443)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    REVERSE PROXY & GATEWAY (Caddy 2 Alpine)                 │
│                 Enruta todo el tráfico hacia el contenedor Frontend         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP (:3000)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                     FRONTEND APPLICATION (Next.js 16 / React 19)            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Capa de Presentación (App Router)                                     │  │
│  │  · /login       : Autenticación institucional                         │  │
│  │  · /chat        : Conversación RAG en tiempo real (Streaming SSE)     │  │
│  │  · /reporte/*   : Dashboard docente (Pulso, Temas, Estudiantes, Ind.) │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │ Backend-For-Frontend (BFF Proxy & Route Handlers: /api/*)             │  │
│  │  · Lee JWT desde Cookie httpOnly (protección XSS total)               │  │
│  │  · Inyecta Header 'Authorization: Bearer <token>' hacia FastAPI       │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │ Red Docker Interna (:8000)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                       BACKEND API (FastAPI / Python 3.12)                   │
│  ┌─────────────────────────┐ ┌──────────────────────┐ ┌──────────────────┐  │
│  │  Routers REST & SSE     │ │  Middleware & Auth   │ │ Dependencies     │  │
│  │  · /api/auth/*          │ │  · Bcrypt verify     │ │ · get_current_user│ │
│  │  · /api/chat            │ │  · JWT HS256 Decode  │ │ · require_role   │  │
│  │  · /api/conversations   │ │  · RBAC (Rol Docente/│ │                  │  │
│  │  · /api/report/*        │ │    Estudiante)       │ │                  │  │
│  └────────────┬────────────┘ └──────────┬───────────┘ └────────┬─────────┘  │
│               │                         │                      │            │
│  ┌────────────▼─────────────────────────▼──────────────────────▼─────────┐  │
│  │ Capa de Servicios de Negocio                                          │  │
│  │  · auth_service   : Validación de credenciales y emisión de tokens    │  │
│  │  · history_service: Trazabilidad y registro de sesiones/preguntas     │  │
│  │  · rag_service    : Enlace al pipeline LangGraph y retrieval          │  │
│  │  · report_service : Agregación analítica, KPIs, deltas y alertas      │  │
│  └────────────┬─────────────────────────┬──────────────────────┬─────────┘  │
└───────────────┼─────────────────────────┼──────────────────────┼────────────┘
                │                         │                      │
┌───────────────▼───────────┐ ┌───────────▼──────────┐ ┌─────────▼────────────┐
│   MOTOR RAG (LangGraph)   │ │  ANALÍTICA & TEMAS   │ │  CAPA DE PERSISTENCIA│
│ · SentenceTransformer     │ │ · UMAP + HDBSCAN     │ │ · SQLite (Logs DB)   │
│   (MiniLM-L12 en memoria) │ │ · topic_store.py     │ │   - consultas        │
│ · FAISS Index (IndexFlatIP│ │   (Incremental)      │ │   - temas            │
│ · Prompt Grounding MBE    │ │ · Groq API (LLM      │ │   - tema_preguntas   │
│ · LLM Stream (Groq /      │ │   Topic Labeling)    │ │   - scope_estado     │
│   OpenRouter gpt-oss-20b) │ │                      │ │ · users.yaml (Roster)│
└───────────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

### 2.2. Flujo de Autenticación y Seguridad por Capas
1. **Almacenamiento de Credenciales:** El archivo institucional `streamlit_app/users.yaml` define usuarios, correos, nombres, roles (`Docente` o `Estudiante`) y contraseñas cifradas con **Bcrypt** (`$2b$12$...`).
2. **Inicio de Sesión (`POST /api/auth/login`):**
   - El cliente envía `username` (correo) y `password`.
   - FastAPI valida el hash Bcrypt contra `users.yaml`.
   - Emite un JSON Web Token (**JWT**) firmado con clave simétrica secreta (`JWT_SECRET_KEY`, algoritmo `HS256`) con expiración de **24 horas**.
   - El payload del token contiene: `{"sub": "<username>", "role": "<Docente|Estudiante>", "name": "<Nombre>", "exp": <timestamp>}`.
3. **Manejo Seguro en Frontend (BFF Pattern):**
   - El Route Handler de Next.js (`frontend/app/api/auth/login/route.ts`) intercepta la respuesta de FastAPI y almacena el JWT en una cookie con flags:
     - `httpOnly: true` (inaccesible desde JavaScript en el navegador, mitigando ataques XSS).
     - `sameSite: "lax"`.
     - `path: "/"`.
     - `secure: true` (en producción HTTPS).
4. **Control de Acceso Basado en Roles (RBAC):**
   - **En Frontend:** El middleware `frontend/proxy.ts` redirige al `/login` si no existe la cookie. Las páginas `/reporte/*` verifican además que el rol sea `Docente`; de lo contrario muestran una pantalla de *Acceso Denegado (Sin permisos)*.
   - **En Backend:** Inyección de dependencias `Depends(get_current_user)` y `Depends(require_role("Docente"))` que rechazan cualquier petición ilegítima con códigos `401 Unauthorized` o `403 Forbidden`.
   - **Logout por Inactividad:** Hook cliente `useIdleLogout` que monitoriza eventos de mouse/teclado y destruye la sesión tras inactividad prolongada.

---

## 3. Preprocesamiento del Corpus y Pipeline Offline

El sistema RAG no busca en texto plano ni en internet; se basa en un corpus curado, validado y preprocesado offline para garantizar máxima fidelidad médica.

```
                   PIPELINE OFFLINE (Ejecución Única)
┌──────────────────┐       ┌────────────────────────┐       ┌─────────────────────┐
│ PDFs Originales  │  ───▶ │ preprocess_corpus.py   │  ───▶ │ articulos_total.csv │
│ (data/raw/)      │       │ (pdfplumber + chunking)│       │ (Corpus en chunks)  │
└──────────────────┘       └────────────────────────┘       └──────────┬──────────┘
                                                                       │
                                                                       ▼
┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────┐
│ faiss_index_total.bin   │ ◀───  │ indexing.py             │ ◀───  │ embeddings_total.npy│
│ (Índice FAISS CPU IP)   │       │ (MiniLM-L12 Embeddings) │       │ (Matriz de vectores)│
└─────────────────────────┘       └─────────────────────────┘       └─────────────────────┘
```

### 3.1. Literatura Médica de Referencia (Corpus MBE)
El corpus está compuesto por dos obras fundamentales de la Medicina Basada en la Evidencia:
1. **Guyatt, G. et al. (2015):** *Users' Guides to the Medical Literature: A Manual for Evidence-Based Clinical Practice*, 3rd Edition. McGraw-Hill Education.
2. **Dans, A. L. et al. (2017):** *Painless Evidence-Based Medicine*, 2nd Edition. Wiley-Blackwell.

### 3.2. Extracción, Limpieza y Chunking (`src/preprocess_corpus.py`)
- **Extracción de Texto:** Utiliza `pdfplumber`. Para prevenir fugas de memoria (**OOM - Out of Memory**) en PDFs de más de 1.000 páginas, cada página extraída se libera explícitamente (`p.close()`).
- **Normalización Textual:** Limpieza de retornos de carro `\r`, unificación de espacios y tabulaciones, y colapso de saltos de línea redundantes.
- **Manejo de Errores de Origen en PDFs:** En el PDF de Dans, a partir de la página 168 existía una copia pegada del libro de Guyatt. El script limita el procesamiento a las primeras 167 páginas (`PAGINA_LIMITE = {"Painless Evidence-Based Medicine.pdf": 167}`) para evitar contaminación y doble citación errónea.
- **Estrategia de Chunking por Ventana Deslizante (Sliding Window):**
  - **Tamaño de Chunk (`CHUNK_SIZE`):** ~100 palabras / tokens aproximados (fragmentos altamente densos y específicos).
  - **Solapamiento (`CHUNK_OVERLAP`):** 20% de solapamiento entre ventanas contiguas para no perder continuidad semántica en los límites de corte.
  - **Filtro Mínimo (`MIN_CHARS`):** 50 caracteres mínimos por chunk para descartar cabeceras y números de página aislados.
  - **Atribución de Página:** El chunking está acotado estrictamente dentro de los límites de cada página física, garantizando que cada fila del dataset tenga el número de página exacto (`pagina`) para la posterior citación bibliográfica del LLM.
- **Salida Generada:** `data/processed/articulos_total.csv` con las columnas: `chunk_id`, `texto`, `tipo`, `pagina`, `fuente_pdf`, `referencia`.

### 3.3. Generación de Embeddings e Índice FAISS (`src/indexing.py`)
- **Modelo de Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
  - Dimensión del vector ($d$): **384**.
  - Modelo multilingüe optimizado para capturar semántica en español e inglés técnico.
  - Normalización $L_2$ aplicada a todos los vectores: $\|v\|_2 = 1$.
- **Índice Vectorial:** **FAISS (Facebook AI Similarity Search)** con topología `IndexFlatIP` (Inner Product).
  - Dado que los vectores están normalizados $L_2$, el producto interno es matemáticamente idéntico a la **Similitud Coseno**:
    $$\text{Similitud}(u, v) = \frac{u \cdot v}{\|u\|_2 \|v\|_2} = u \cdot v$$
- **Archivos Generados:**
  - `data/processed/models/embeddings_total.npy`: Matriz NumPy con todos los vectores densos calculados.
  - `data/processed/models/faiss_index_total.bin`: Índice binario FAISS optimizado para búsqueda exacta y ultra-rápida en CPU (< 1 ms por consulta).

---

## 4. Motor RAG en Tiempo Real y Pipeline LangGraph

El pipeline online se ejecuta en cada interacción de chat. Está orquestado a través de **LangGraph** y expuesto por el backend mediante streaming.

```
                                  PIPELINE ONLINE (Runtime)
┌──────────────┐
│  Pregunta    │
│  del Usuario │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Enriquecimiento Contextual (_query_retrieval)                            │
│    Concatena la última pregunta del usuario + pregunta actual               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Nodo "retrieve" (LangGraph)                                              │
│    a. SentenceTransformer: Codifica query enriquecida (vector 384D normal.) │
│    b. FAISS: Búsqueda top_k = 3 (Similitud Coseno / Inner Product)          │
│    c. Ensambla bloque CONTEXTO con citas: (Autor, Libro, Año — pág. X)      │
│    * Emite yield 1: Metadatos (chunks, scores de similitud, latencias)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Nodo "generate" (LangGraph)                                              │
│    a. Inyecta Historial reciente (últimos 3 intercambios / 6 mensajes)       │
│    b. Inyecta Prompt de Reglas Estrictas de MBE (4 casos determinísticos)   │
│    c. LLM Inferencia en Streaming (OpenRouter / Groq: gpt-oss-20b)          │
│    * Emite yields 2..N: Tokens de texto en tiempo real vía SSE              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. Observabilidad y Cierre (history_service)                                │
│    a. Frontend renderiza tokens en tiempo real con cursor de escritura      │
│    b. Al finalizar el stream, backend calcula latencias (LLM, Total)        │
│    c. Inserción asíncrona en SQLite: tabla consultas con trace_id           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1. Grafo de Estados (`app_langgraph.py`)
Se define mediante un grafo `StateGraph` tipado:
- `InputState`: `{"query": str}`
- `OutputState`: `{"response": str}`
- `GraphState`: `{"query": str, "context": str, "response": str}`
- Nodos: `retrieve` $\to$ `generate`.

### 4.2. Recuperación Contextual Avanzada y Manejo de Seguimiento
Uno de los principales problemas de los sistemas RAG conversacionales ocurre cuando el usuario hace preguntas de seguimiento con pronombres o elipsis (ej. *"¿Cuáles son sus 3 componentes?"* o *"Explícame el segundo"*):
- Si se busca en FAISS solo la frase *"¿Cuáles son sus 3 componentes?"*, el vector resultante no tiene información sobre la entidad previa y el retrieval recupera chunks irrelevantes.
- Si se concatena toda la respuesta previa del asistente a la búsqueda, los párrafos largos diluyen el embedding y desvían el vector hacia temas secundarios.
- **Solución implementada (`_query_retrieval`):** El sistema extrae la **última pregunta hecha por el usuario en el historial** y la concatena a la pregunta actual para calcular el embedding de búsqueda en FAISS. De este modo, el retrieval mantiene el contexto temático exacto sin dilución de ruido.
- **Ventana de Memoria (`_preparar_historial`):** Se mantiene una ventana deslizante de los últimos **3 intercambios completos (6 mensajes)** para inyectar en el prompt del LLM, balanceando contexto con economía de tokens.

### 4.3. Reglas de Inferencia y Prompt Grounding para MBE
El prompt instruye al LLM a comportarse como un experto en MBE y a seguir un árbol de decisión estricto de **4 casos mutuamente excluyentes**:
1. **Caso 1 (Cortesía):** Si el mensaje es solo un saludo o agradecimiento (*"hola"*, *"gracias"*), responde cordialmente y ofrece ayuda en temas de MBE.
2. **Caso 2 (Fuera de Dominio - Out of Scope):** Si la pregunta no corresponde a MBE (ej. recetas, política, programación general), indica amablemente en 1-2 frases que está fuera de su alcance y lista los temas que sí domina (diseño de estudios, jerarquía de evidencia, sesgos, preguntas PICO, revisiones sistemáticas).
3. **Caso 3 (Pregunta de MBE con Contexto Válido):** Sintetiza la respuesta utilizando **únicamente** los fragmentos recuperados en `CONTEXTO`. Al citar, utiliza obligatoriamente la referencia exacta entre paréntesis: `(Autor, Libro, Año — pág. X)`.
4. **Caso 4 (Pregunta de MBE sin Información en el Corpus):** Si la pregunta es médica pero el corpus no contiene la respuesta (o solo contiene índices/bibliografías), debe responder textualmente:
   > *"No hay suficiente información en los textos proporcionados para responder la pregunta."*

**Prohibición de Razonamiento Interno en la Salida:** El prompt prohíbe explícitamente incluir meta-comentarios como *"Basado en el caso 3..."* o *"Nota: según el contexto..."*, forzando una respuesta limpia orientada directamente al usuario.

### 4.4. Flexibilidad de Proveedores de LLM (`core.py`)
El sistema implementa una arquitectura desacoplada de proveedor mediante la variable `LLM_PROVIDER`:
- **OpenRouter (`LLM_PROVIDER=openrouter`):** Cliente compatible con OpenAI SDK apuntando a `https://openrouter.ai/api/v1`. Modelo: `openai/gpt-oss-20b`.
- **Groq (`LLM_PROVIDER=groq`):** Inferencia de ultra-baja latencia con Groq SDK.
- **Parámetros de Inferencia Optimizados:**
  - `temperature: 0.2` (máximo determinismo y reducción de variabilidad).
  - `max_tokens: 2048`.
  - `reasoning_effort: "low"` (evita que los tokens de pensamiento consuman el presupuesto de respuesta en tareas extractivas).
  - `extra_body: {"include_reasoning": False}` (evita filtración de tokens de razonamiento en streaming).

---

## 5. Backend FastAPI (`backend/`)

### 5.1. Estructura y Módulos
```
backend/
├── main.py                # Punto de entrada FastAPI, ciclo de vida (lifespan), montaje de routers
├── bootstrap.py           # Inserción limpia de streamlit_app en sys.path (reuso de módulos)
├── dependencies.py        # Inyección de dependencias de seguridad (JWT, validación de roles)
├── requirements.txt       # Dependencias exclusivas de backend (FastAPI, PyJWT, PyYAML, etc.)
├── Dockerfile             # Imagen Docker multi-capa con PyTorch CPU y SentenceTransformers
├── models/
│   └── schemas.py         # Modelos Pydantic para request/response de chat y conversaciones
├── routers/
│   ├── auth.py            # Endpoints de login y me (/api/auth/*)
│   ├── chat.py            # Endpoint de chat en streaming SSE (/api/chat)
│   ├── conversations.py   # Endpoints de historial de conversaciones (/api/conversations/*)
│   └── report.py          # Endpoints analíticos del reporte docente (/api/report/*)
└── services/
    ├── auth_service.py    # Lógica de bcrypt, emisión y verificación de JWT
    ├── history_service.py # Interfaz con logger.py y persistencia de interacciones
    ├── rag_service.py     # Wrapper de carga de recursos y ejecución del pipeline RAG
    └── report_service.py  # Agregación analítica de datos, deltas, alertas y filtrado
```

### 5.2. Ciclo de Vida del Backend (`lifespan`)
Al arrancar el contenedor (`main.py`):
1. Se inicializan las tablas de la base de datos SQLite (`consultas`, `temas`, `tema_preguntas`, `temas_scope_estado`).
2. Se cargan en memoria de forma persistente:
   - El dataset de chunks (`articulos_total.csv`).
   - El índice vectorial FAISS (`faiss_index_total.bin`).
   - El modelo de embeddings `SentenceTransformer` precargado localmente.
   - El cliente de inferencia LLM (Groq / OpenRouter).
3. Los recursos quedan disponibles en `app.state.resources`, evitando recargas costosas en cada petición HTTP.

### 5.3. Catálogo Detallado de Endpoints

| Método | Endpoint | Rol Requerido | Descripción |
|---|---|---|---|
| `POST` | `/api/auth/login` | Público | Autentica usuario/clave contra `users.yaml`, retorna JWT y rol. |
| `GET` | `/api/auth/me` | Autenticado | Retorna identidad del usuario activo (`user_id`, `role`, `name`). |
| `POST` | `/api/chat` | Autenticado | Recibe pregunta y `conversation_id`, ejecuta RAG y emite stream SSE de tokens. |
| `GET` | `/api/conversations` | Autenticado | Lista conversaciones del usuario autenticado (más reciente primero). |
| `GET` | `/api/conversations/{id}` | Autenticado | Detalle y mensajes de una conversación específica. |
| `POST` | `/api/conversations` | Autenticado | Crea un nuevo ID de conversación temporal. |
| `GET` | `/api/report/meta` | `Docente` | Rango de fechas mínimo y máximo presente en la base de datos. |
| `GET` | `/api/report/pulso` | `Docente` | Nivel 1: KPIs con deltas, sparkline 4 semanas, alertas y distribución temporal. |
| `GET` | `/api/report/temas` | `Docente` | Nivel 2: Estado de temas generados, preguntas destacadas y evolución semanal. |
| `POST` | `/api/report/temas/generate` | `Docente` | Dispara el clustering incremental de temas y preguntas destacadas. |
| `GET` | `/api/report/estudiantes` | `Docente` | Nivel 3: Roster de estudiantes, tabla de esfuerzo, histograma, silenciosos y nunca usados. |
| `GET` | `/api/report/estudiantes/{usuario}` | `Docente` | Nivel 4: Detalle individual, timeline, últimas preguntas y perfil temático. |

---

## 6. Módulo de Analítica y Modelado de Temas (`report_generator/modules/`)

Este módulo implementa algoritmos de procesamiento estadístico y machine learning no supervisado para transformar los logs de interacciones en conocimiento pedagógico accionable.

### 6.1. Modelado Temático Incremental y Persistente (`topic_store.py`)
En dashboards analíticos tradicionales, correr algoritmos de clustering (como LDA o K-Means clásico) en cada carga de página provoca inestabilidad: los temas cambian de nombre y los IDs se reasignan aleatoriamente. Para resolver esto, se diseñó un **sistema de clustering incremental con persistencia en SQLite**:

```
                       PROCESO DE CLUSTERING INCREMENTAL
┌────────────────────────────────────────┐
│ Preguntas Nuevas en consultas          │
│ (Pendientes de clasificar ≥ 5)         │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Generación de Embeddings (MiniLM-L12)  │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Comparación contra Centroides de Temas Existentes (Similitud Coseno)        │
│                                                                             │
│   ¿Similitud ≥ 0.55?                                                        │
│     ├── SÍ ──▶ Asignar a tema existente y recalcular centroide ponderado.   │
│     └── NO ──▶ Enviar al bucket residual ("Preguntas variadas").            │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Evaluación del Bucket Residual ("Preguntas variadas")                       │
│                                                                             │
│   ¿Residual acumula ≥ 5 preguntas nuevas Y temas actuales < MAX_TEMAS (10)? │
│     └── SÍ ──▶ SUB-CLUSTERING DEL RESIDUAL:                                 │
│                1. Reducción UMAP (10 dimensiones).                          │
│                2. Agrupamiento HDBSCAN (min_cluster_size=3) / Fallback KMeans│
│                3. Fusión de centroides más cercanos si excede el cupo.      │
│                4. Llamada al LLM: Nombra nuevos clusters (máx 4 palabras).  │
│                5. Persiste nuevos temas y reasigna preguntas del residual.  │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Nombrado Inteligente de Clusters:** Se envía un lote de preguntas representativas de cada grupo al LLM con la regla explícita de asignar títulos breves (máximo 4 palabras en español) y la prohibición estricta de usar el término general *"Medicina Basada en la Evidencia"*.
- **Preguntas Destacadas:** En la misma llamada, el LLM analiza la muestra de preguntas y selecciona hasta **3 preguntas formuladas con excelencia clínica** para que el docente las proyecte o discuta en clase como ejemplos positivos.

### 6.2. Motor de Detección de Alertas Pedagógicas (`alerts.py`)
El sistema evalúa continuamente 5 condiciones críticas y genera hasta 3 tarjetas de alerta priorizadas en la pantalla principal del docente:
1. **Tema en Alza:** Compara el volumen de preguntas de las dos últimas semanas mediante `evolucion_semanal_por_tema`. Si un tema incrementa su volumen en $\ge 30\%$, se emite una alerta indicando el repunte.
2. **Retrieval Débil (`retrieval_quality.py`):** Cruza las preguntas asignadas a cada tema con los puntajes de similitud máxima recuperados de FAISS (`scores_similitud`). Si un tema tiene $\ge 3$ preguntas y su similitud media es $\le 0.40$, alerta al docente sobre posibles vacíos en el corpus o confusiones terminológicas de los estudiantes.
3. **Estudiantes Silenciosos (`roster.py`):** Identifica alumnos registrados que tuvieron actividad previa pero acumulan **$\ge 14$ días de inactividad continua**.
4. **Cuentas Nunca Usadas (`roster.py`):** Cruza el roster con el histórico de logs para listar a los estudiantes que no han enviado su primera pregunta.
5. **Concentración Temporal (`temporal_analysis.py`):** Detecta si el $\ge 40\%$ del volumen de preguntas del período se concentra en solo 2 días de la semana (patrón típico de estudio de última hora previo a evaluaciones).

### 6.3. Cálculo de KPIs con Deltas Porcentuales (`deltas.py`)
Para cada indicador del Nivel 1 (Pulso), se calcula el valor del período seleccionado ($[T_{\text{desde}}, T_{\text{hasta}}]$) y se compara contra el período inmediatamente anterior de igual duración ($[T_{\text{desde}} - \Delta t, T_{\text{desde}}]$):
$$\Delta\% = \frac{\text{Valor}_{\text{actual}} - \text{Valor}_{\text{anterior}}}{\text{Valor}_{\text{anterior}}} \times 100$$
Indicadores calculados:
- Total de Preguntas formuladas.
- Estudiantes Activos en el período.
- Total de Sesiones / Chats iniciados.
- Promedio de Preguntas por Estudiante.
- Tiempo Promedio por Sesión (partiendo sesiones reales con corte de inactividad de 30 min).

---

## 7. Frontend Next.js 16 (`frontend/`)

### 7.1. Arquitectura y Stack Tecnológico
- **Framework:** Next.js 16 (App Router) con React 19.
- **Lenguaje:** TypeScript con tipado estricto en toda la aplicación.
- **Estilos:** Tailwind CSS v4 con variables semánticas personalizadas (`theme-javeriana`: azul institucional profundo `#1e3a5f`, verde teal `#0d9488`, grises de superficie cálidos).
- **Renderizado Markdown:** `react-markdown` + `remark-gfm` con estilos tipográficos para listas, tablas y bloques de código médico.

### 7.2. Estructura de Rutas y Páginas
```
frontend/app/
├── layout.tsx                     # Root layout, fuentes tipográficas, metadatos
├── page.tsx                       # Redirección inteligente a /chat o /login según sesión
├── globals.css                    # Tokens de diseño Tailwind CSS v4
├── login/
│   └── page.tsx                   # Formulario de login institucional Javeriana
├── chat/
│   └── page.tsx                   # Server component que carga historial inicial y renderiza ChatShell
├── reporte/
│   ├── layout.tsx                 # Layout docente con verificación de rol, sidebar y top bar
│   ├── page.tsx                   # Redirección por defecto a /reporte/pulso
│   ├── pulso/
│   │   └── page.tsx               # Nivel 1: Pulso del curso (KPIs, gráficos, alertas)
│   ├── temas/
│   │   └── page.tsx               # Nivel 2: Exploración temática y preguntas destacadas
│   └── estudiantes/
│       ├── page.tsx               # Nivel 3: Roster, histograma de esfuerzo, silenciosos
│       └── [usuario]/
│           └── page.tsx           # Nivel 4: Detalle individual de un estudiante
└── api/                           # Backend-For-Frontend (BFF) Proxies
    ├── auth/login/route.ts        # Almacena JWT en cookie httpOnly
    ├── auth/logout/route.ts       # Elimina cookie de sesión
    ├── chat/route.ts              # Proxy de streaming SSE hacia FastAPI
    ├── conversations/route.ts     # Proxy de listado y creación de chats
    ├── conversations/[id]/route.ts# Proxy de mensajes por conversación
    └── report/temas/generate/route.ts # Disparador de análisis temático
```

### 7.3. Componentes Clave del Asistente y del Reporte

```
                       MAPA DE COMPONENTES REACT
┌─────────────────────────────────────────────────────────────────────────────┐
│ ASISTENTE DE CHAT (/chat)                                                   │
│ ┌───────────────────────┐ ┌───────────────────────────────────────────────┐ │
│ │ Sidebar.tsx           │ │ ChatShell.tsx                                 │ │
│ │ · Historial de chats  │ │ ├── WelcomeScreen.tsx (Sugerencias iniciales) │ │
│ │ · Nueva conversación  │ │ ├── MessageBubble.tsx (Renderizado Markdown)  │ │
│ │ · Usuario y logout    │ │ └── ChatInput.tsx (Input + Botón Cancelar)    │ │
│ └───────────────────────┘ └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ REPORTE DOCENTE (/reporte/*)                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ ReportSidebar.tsx (Selector temporal "Desde-Hasta", Identidad docente)  │ │
│ │ ReportTopBar.tsx  (Navegación por pestañas: Pulso | Temas | Estudiantes)│ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ Nivel 1 - Pulso:       KpiGrid, AlertsSection, WeeklyChart, HeatmapCard │ │
│ │ Nivel 2 - Temas:       TemasView, TemasResultado, EvolutionChart        │ │
│ │ Nivel 3 - Estudiantes: EffortHistogram, SilenciososCard, RosterTable    │ │
│ │ Nivel 4 - Individual:  StudentBanner, StudentKpis, StudentQuestions,    │ │
│ │                        StudentTopicProfile, StudentSparkline            │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Observabilidad y Esquema de Base de Datos SQLite

La base de datos relacional `mbe_logs.db` (ubicada en `streamlit_app/data/logs/mbe_logs.db`) actúa como el registro central de verdad y auditoría del sistema.

### 8.1. Esquema Relacional Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 consultas                                   │
├──────────────────────┬──────────────────┬───────────────────────────────────┤
│ id                   │ INTEGER (PK AI)  │ Identificador único de consulta   │
│ timestamp            │ DATETIME         │ Fecha y hora UTC del registro     │
│ usuario              │ TEXT             │ Username / Correo del estudiante  │
│ session_id           │ TEXT             │ UUID de la conversación de chat   │
│ pregunta             │ TEXT             │ Texto de la pregunta realizada    │
│ chunks_extraidos     │ TEXT (JSON)      │ Chunks de texto y metadatos FAISS │
│ scores_similitud     │ TEXT (JSON)      │ Lista de puntajes de similitud cos│
│ respuesta            │ TEXT             │ Respuesta completa generada       │
│ latencia_embedding   │ REAL             │ Segundos en calcular embedding Q  │
│ latencia_retrieval   │ REAL             │ Segundos en búsqueda FAISS        │
│ latencia_llm         │ REAL             │ Segundos en inferencia LLM        │
│ latencia_total       │ REAL             │ Segundos totales de la petición   │
└──────────────────────┴──────────────────┴───────────────────────────────────┘
                                   │
                                   │ 1:N (por pregunta normalizada y rol)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               tema_preguntas                                │
├──────────────────────┬──────────────────┬───────────────────────────────────┤
│ id                   │ INTEGER (PK AI)  │ Identificador único               │
│ rol                  │ TEXT             │ Scope de rol ('estudiantes')      │
│ pregunta_norm        │ TEXT             │ Pregunta normalizada (UNIQUE)     │
│ tema_id              │ INTEGER (FK)     │ Referencia a tabla temas(id)      │
│ embedding            │ TEXT (JSON)      │ Vector denso 384D de la pregunta  │
│ primera_consulta_id  │ INTEGER          │ ID de la primera aparición en log │
│ creado_en            │ DATETIME         │ Timestamp de asignación           │
└──────────────────────┴──────────────────┴───────────────────────────────────┘
                                   │
                                   │ N:1
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   temas                                     │
├──────────────────────┬──────────────────┬───────────────────────────────────┤
│ id                   │ INTEGER (PK AI)  │ Identificador único del tema      │
│ rol                  │ TEXT             │ Scope de rol ('estudiantes')      │
│ nombre               │ TEXT             │ Título descriptivo asignado porLLM│
│ es_residual          │ INTEGER (0/1)    │ 1 si es 'Preguntas variadas'      │
│ centroide            │ TEXT (JSON)      │ Vector centroide promedio 384D    │
│ n_preguntas          │ INTEGER          │ Contador de preguntas asociadas   │
│ creado_en            │ DATETIME         │ Timestamp de creación             │
│ actualizado_en       │ DATETIME         │ Timestamp de última actualización │
└──────────────────────┴──────────────────┴───────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            temas_scope_estado                               │
├──────────────────────┬──────────────────┬───────────────────────────────────┤
│ rol                  │ TEXT (PK)        │ Scope ('estudiantes', 'docentes') │
│ ultimo_consulta_id   │ INTEGER          │ Cursor ID de la última corrida    │
│ ultima_corrida_en    │ DATETIME         │ Timestamp del último análisis     │
│ destacadas_json      │ TEXT (JSON)      │ Lista de preguntas destacadas     │
└──────────────────────┴──────────────────┴───────────────────────────────────┘
```

---

## 9. Infraestructura, Despliegue y Contenedores

La orquestación se realiza a través de **Docker Compose** con volúmenes persistentes y redes aisladas.

```
                                INFRAESTRUCTURA DOCKER
┌─────────────────────────────────────────────────────────────────────────────┐
│ HOST (Servidor Linux / Hetzner VPS)                                         │
│                                                                             │
│  Puertos Públicos: 80 (HTTP), 443 (HTTPS)                                   │
│                           │                                                 │
│                           ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Contenedor caddy (caddy:2-alpine)                                     │  │
│  │ Reverse proxy hacia frontend:3000                                     │  │
│  └────────────────────────┬──────────────────────────────────────────────┘  │
│                           │ Red interna Docker                              │
│                           ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Contenedor frontend (mbe-frontend:latest - Node 20 Standalone)        │  │
│  │ Puerto interno: 3000 | NEXT_PUBLIC_API_URL=http://backend:8000        │  │
│  └────────────────────────┬──────────────────────────────────────────────┘  │
│                           │ Red interna Docker                              │
│                           ▼                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Contenedor backend (mbe-backend:latest - Python 3.12 FastAPI)         │  │
│  │ Puerto interno: 8000 | SentenceTransformers + FAISS en memoria        │  │
│  │ Volúmenes montados desde el Host:                                     │  │
│  │   · ./streamlit_app/data (ro)       : Índice FAISS y CSV corpus       │  │
│  │   · ./streamlit_app/data/logs (rw)  : Base de datos SQLite mbe_logs.db│  │
│  │   · ./streamlit_app/users.yaml (ro) : Credenciales y Roster           │  │
│  │   · .env (secrets)                  : API Keys de Groq / OpenRouter   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.1. Configuración de Servicios (`docker-compose.yml`)
- **Aislamiento de Seguridad:** El contenedor de backend no expone ningún puerto al exterior del host; la comunicación ocurre exclusivamente a través de la red interna de Docker desde el BFF de Next.js.
- **Volúmenes de Persistencia:** Los logs (`mbe_logs.db`), el corpus preprocesado y el archivo de usuarios `users.yaml` residen en el sistema de archivos del host, permitiendo actualizaciones de usuarios o backups de datos sin necesidad de reconstruir las imágenes Docker.

---

## 10. Guía Rápida de Referencia para la Escritura de la Tesis

Para facilitar la redacción de los capítulos metodológico, de desarrollo y de resultados de la tesis, esta tabla sintetiza las correspondencias conceptuales y técnicas:

| Concepto en la Tesis | Módulo / Archivo en el Código | Detalle Técnico / Algorítmico |
|---|---|---|
| **Corpus Bibliográfico** | `streamlit_app/src/preprocess_corpus.py` | 2 libros clásicos MBE (Guyatt 2015, Dans 2017). Chunking por ventana (~100 tokens, 20% overlap, límite pág. 167 Dans). |
| **Representación Vectorial** | `streamlit_app/src/indexing.py` | Embeddings densos multilingües `MiniLM-L12-v2` ($d=384$), normalizados $L_2$. |
| **Indexación y Búsqueda** | `streamlit_app/app/core.py` | FAISS CPU con topología `IndexFlatIP` (Similitud Coseno exacta, top $k=3$). |
| **Pipeline RAG** | `streamlit_app/rag_langgraph/app_langgraph.py` | Grafo de estados LangGraph (`retrieve` $\to$ `generate`). Streaming y captura de metadatos. |
| **Seguimiento Conversacional** | `streamlit_app/rag_langgraph/app_langgraph.py` | Función `_query_retrieval()`: combina última pregunta de usuario con query actual para resolver elipsis. |
| **Mitigación de Alucinaciones** | `streamlit_app/rag_langgraph/app_langgraph.py` | Prompt estricto de 4 casos: citas obligatorias `(Autor, Libro, Año — pág. X)`, rechazo OOS y fallback exacto si no hay datos. |
| **Motor de Inferencia LLM** | `streamlit_app/app/core.py` | `openai/gpt-oss-20b` vía OpenRouter o Groq (`temperature=0.2`, `reasoning_effort="low"`). |
| **Modelado de Temas** | `streamlit_app/report_generator/modules/topic_store.py` | Clustering incremental: embeddings $\to$ similitud a centroides ($\ge 0.55$) $\to$ UMAP (10D) + HDBSCAN sobre residual $\to$ LLM labeling. |
| **Alertas Pedagógicas** | `streamlit_app/report_generator/modules/alerts.py` | Detección de tema en alza ($\ge 30\%$), retrieval débil (score $\le 0.40$), silenciosos ($\ge 14$ días) y concentración temporal ($\ge 40\%$). |
| **Observabilidad y Logs** | `streamlit_app/app/logger.py` & `backend/services/history_service.py` | Registro SQLite de cada consulta con `trace_id`, chunks recuperados, scores de similitud y latencias por etapa (embedding, retrieval, LLM, total). |
| **Autenticación y Seguridad** | `backend/services/auth_service.py` & `frontend/proxy.ts` | Bcrypt para verificación de credenciales, JWT (HS256, 24h) almacenado en cookies `httpOnly`, RBAC por rol. |
| **Arquitectura de Software** | `docker-compose.yml`, `Caddyfile`, `backend/`, `frontend/` | Patrón BFF con Next.js 16 + API REST asíncrona en FastAPI + Reverse proxy Caddy 2. |
