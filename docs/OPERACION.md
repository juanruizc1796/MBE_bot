# Operación — desarrollo, despliegue y mantenimiento

## Variables de entorno

Van en `.env`, en la raíz del repo. Docker Compose se lo pasa al backend. La plantilla es `.env.example`.

| Variable | Servicio | Requerida | Descripción |
|---|---|---|---|
| `LLM_PROVIDER` | backend | sí | `openrouter` (por defecto) o `groq` |
| `OPENROUTER_API_KEY` | backend | si el proveedor es openrouter | — |
| `GROQ_API_KEY` | backend | si el proveedor es groq **o** si se quiere generar temas en el reporte | — |
| `JWT_SECRET_KEY` | backend | sí | Firma de los JWT (HS256) |
| `LANGSMITH_API_KEY` | backend | no | Trazas en LangSmith |
| `LOGS_DB_PATH` | backend | no | Por defecto `data/logs/mbe_logs.db` (relativa a `rag_engine/`) |
| `NEXT_PUBLIC_API_URL` | frontend | sí | URL interna del backend. En Compose: `http://backend:8000`. En local: `http://localhost:8000` |
| `COOKIE_SECURE` | frontend | no | `true` cuando se sirva por HTTPS |

---

## Desarrollo local

```bash
# Backend (desde la raíz del repo; main.py hace chdir a rag_engine/)
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
set -a && source .env && set +a
uvicorn backend.main:app --reload            # http://localhost:8000/docs

# Frontend (en otra terminal)
cd frontend
npm install
npm run dev                                  # http://localhost:3000
```

> `frontend/AGENTS.md`: Next.js 16 trae cambios incompatibles con versiones anteriores. Antes de tocar APIs del framework, revisa `node_modules/next/dist/docs/`.

---

## Despliegue (VPS Hetzner)

```bash
ssh usuario@hetzner
cd ~/RAG_langraph
git pull
docker compose up -d --build
docker compose logs -f backend
```

- Solo se reconstruye lo que cambió: `docker compose up -d --build backend` o `... frontend`.
- **HTTPS:** cambia `:80` por el dominio en el `Caddyfile` (Caddy obtiene el certificado solo), añade `COOKIE_SECURE=true` al servicio `frontend` y reinicia.

### Backup antes de desplegar cambios grandes

```bash
cp rag_engine/data/logs/mbe_logs.db rag_engine/data/logs/mbe_logs.db.bak_$(date +%Y%m%d_%H%M%S)
cp rag_engine/users.yaml rag_engine/users.yaml.bak_$(date +%Y%m%d_%H%M%S)
```

Lo ideal es copiar los backups fuera del VPS.

### Rollback

```bash
git log --oneline -5
git checkout <commit-estable>
docker compose up -d --build
```

---

## Cambiar de proveedor LLM

1. Edita `LLM_PROVIDER` en `.env` (`openrouter` o `groq`).
2. Ejecuta `docker compose up -d --build backend`.

---

## Gestión de usuarios

Los usuarios están en `rag_engine/users.yaml`, montado en solo lectura. Para aplicar cambios basta reiniciar el backend; no hace falta reconstruir.

```yaml
credentials:
  usernames:
    usuario@javeriana.edu.co:
      email: usuario@javeriana.edu.co
      name: Nombre Apellido
      rol: Estudiante        # o Docente
      password: $2b$12$...   # hash bcrypt
```

Generar un hash:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'la_clave', bcrypt.gensalt()).decode())"
```

Después: `docker compose restart backend`.

---

## Logs y observabilidad

- La BD vive en `rag_engine/data/logs/mbe_logs.db`, en el host. Se puede abrir con `sqlite3`, DBeaver o DB Browser.
- Las trazas por consulta (`trace_id`) salen en `docker compose logs backend`.

```sql
-- Consultas y latencia promedio por usuario
SELECT usuario, COUNT(*) AS n,
       ROUND(AVG(latencia_total), 2) AS lat_total_s,
       ROUND(AVG(latencia_llm), 2)   AS lat_llm_s
FROM consultas GROUP BY usuario ORDER BY n DESC;
```

---

## Problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| «Generar temas» devuelve 503 | Falta `GROQ_API_KEY` (los temas usan Groq aunque el chat use OpenRouter) |
| «Generar temas» devuelve 422 | Hay menos de 5 preguntas nuevas en el período |
| El login funciona pero vuelve a `/login` | `COOKIE_SECURE=true` sirviendo por HTTP |
| La respuesta del LLM se corta | Revisa `max_tokens` y `reasoning_effort` en `rag_engine/app/core.py` |
| El backend tarda en arrancar | Es normal: carga SentenceTransformer y FAISS en el `lifespan` |
