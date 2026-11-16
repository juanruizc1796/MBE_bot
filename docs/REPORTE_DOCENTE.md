# Reporte docente

Panel exclusivo para el rol **Docente** (`/reporte/*`). Si un estudiante intenta entrar, ve «sin permisos».

- Frontend: `frontend/app/reporte/` y `frontend/components/report/`
- Backend: `backend/routers/report.py` → `backend/services/report_service.py` → `rag_engine/report_generator/modules/`
- Umbrales: `rag_engine/report_generator/config.py`

---

## Estructura

Tiene 4 niveles de zoom. Los niveles 1 a 3 son pestañas. El 4 es una vista de detalle que solo se abre desde la tabla de estudiantes o desde una alerta.

La **barra lateral**, común a todos los niveles, tiene el selector de período (Desde/Hasta, acotado a `/report/meta`) y la identidad del docente con el botón de cerrar sesión.

> **Alcance de los datos:** el reporte solo cuenta preguntas de usuarios con rol `Estudiante`. Además, `report_service.py` filtra el roster por `PREFIJO_USUARIO_REPORTE` para excluir cuentas de prueba mientras conviven con las reales. Ese filtro es temporal y está escrito directamente en el código.

> **Período vs. histórico:** los KPIs, temas y conteos usan el período seleccionado. Las señales «nunca usado», «silencioso» y «última actividad», y todo el Nivel 4, se calculan sobre el **histórico completo**.

### Nivel 1 — Pulso (`/reporte/pulso`)

Responde «¿cómo va la semana?».
- **6 KPIs**, cada uno con su variación % frente al período anterior de igual duración: total de estudiantes (roster), estudiantes activos, chats, preguntas, preguntas por estudiante y tiempo promedio por sesión.
- Actividad de las últimas 4 semanas (sparkline semanal), distribución por día y mapa de calor día × hora.
- **Hasta 3 alertas** priorizadas, con enlace a Temas o a Estudiantes. Si no hay alertas, lo dice explícitamente.

### Nivel 2 — Temas (`/reporte/temas`)

Muestra qué está preguntando el curso.
- Estados de la vista: *sin generar* → *generando* → *resultado*. El análisis se lanza a mano (botón) porque tarda.
- Resultado: temas con conteo y %, preguntas de ejemplo por tema, hasta 3 **preguntas destacadas** y la evolución semanal por tema.
- Requiere al menos 5 preguntas nuevas y `GROQ_API_KEY`.

### Nivel 3 — Estudiantes (`/reporte/estudiantes`)

Compara el uso entre estudiantes.
- Histograma de esfuerzo por número de preguntas: 0 · 1–5 · 6–20 · >20.
- Silenciosos (≥ 14 días sin actividad) y cuentas nunca usadas.
- Roster con preguntas, sesiones y últimos temas. Va ordenado de **menor a mayor uso**, para que aparezca primero quien menos usa la herramienta.

### Nivel 4 — Estudiante individual (`/reporte/estudiantes/[usuario]`)

Muestra lo mínimo necesario para una tutoría y se marca en pantalla como vista restringida.
- Totales históricos y última actividad.
- Últimas 3 a 5 preguntas.
- Línea de tiempo diaria.
- Perfil temático: temas tocados frente a temas no tocados.

---

## Algoritmos

### Modelado de temas incremental — `modules/topic_store.py`

Si se hace clustering desde cero en cada carga, los temas cambian de nombre e id. Por eso los temas se **persisten** en SQLite (tablas `temas`, `tema_preguntas` y `temas_scope_estado`; ver [ARQUITECTURA.md](ARQUITECTURA.md#esquema-de-base-de-datos)) y cada corrida solo procesa las preguntas nuevas desde el cursor `ultimo_consulta_id`.

```
preguntas nuevas (≥ TEMAS_MIN_PREGUNTAS_NUEVAS = 5)
  → embedding MiniLM
  → similitud con el centroide de cada tema existente
       ≥ 0.55 (TEMAS_SIMILITUD_UMBRAL) → se asigna al tema y se actualiza el centroide (promedio ponderado)
       <  0.55                         → va al tema residual «Preguntas variadas»
  → si el residual acumula preguntas nuevas suficientes y hay menos de MAX_TEMAS (10) temas:
       UMAP (10 dims) → HDBSCAN (min_cluster_size=3, min_samples=2; KMeans como respaldo)
       → si se pasa del cupo, se fusionan los centroides más cercanos
       → el LLM (Groq) nombra cada cluster (máx. 4 palabras, sin usar «Medicina Basada en la Evidencia»)
       → se guardan los temas nuevos y se reasignan las preguntas del residual
```

En la misma llamada al LLM se eligen hasta 3 **preguntas destacadas** (`MAX_PREGUNTAS_DESTACADAS`), bien formuladas, para usarlas en clase.

### Alertas — `modules/alerts.py`

| Alerta | Regla | Fuente |
|---|---|---|
| Tema en alza | Un tema crece ≥ 30 % entre las dos últimas semanas | `evolucion_semanal_por_tema` |
| Retrieval débil | Tema con ≥ 3 preguntas (`RETRIEVAL_DEBIL_MIN_PREGUNTAS`) y similitud máxima media ≤ 0.40 (`RETRIEVAL_DEBIL_UMBRAL_SCORE`) | `retrieval_quality.py` |
| Silenciosos | ≥ 14 días sin actividad (`SILENCIO_DIAS`) | `roster.py` |
| Nunca usados | Están en el roster pero no tienen ninguna consulta | `roster.py` |
| Concentración | ≥ 40 % de las preguntas en solo 2 días de la semana | `temporal_analysis.py` |

Se muestran como máximo 3, ordenadas por prioridad. Las alertas de contenido (tema en alza y retrieval débil) solo aparecen si ya se generaron temas.

### KPIs con delta — `modules/deltas.py`

Cada KPI se calcula sobre `[desde, hasta]` y se compara con el período anterior de igual duración:

Δ% = (actual − anterior) / anterior × 100

Las sesiones se reconstruyen cortando la actividad cuando hay ≥ 30 min de inactividad (`SESION_GAP_INACTIVIDAD_MIN`).

### Roles — `modules/roles.py`

El rol se lee del campo `rol` de `users.yaml`, y el archivo se vuelve a leer solo cuando cambia su fecha de modificación. Para usernames antiguos del histórico (de antes del login por correo) se usa como respaldo el prefijo `Docente…` / `Estudiante…`.
