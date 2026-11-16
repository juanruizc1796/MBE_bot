# Frontend — Asistente MBE

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4.

```bash
npm install
npm run dev     # http://localhost:3000 (necesita el backend en NEXT_PUBLIC_API_URL, por defecto http://localhost:8000)
npm run build && npm start
```

## Mapa

| Ruta | Qué es |
|---|---|
| `app/login`, `app/chat` | Login y chat del estudiante (`components/ChatShell.tsx`, `Sidebar.tsx`, …) |
| `app/reporte/*` | Reporte docente de 4 niveles (`components/report/*`) |
| `app/api/*` | BFF: lee el JWT de la cookie httpOnly y reenvía a FastAPI (`lib/fastapi.ts`) |
| `proxy.ts` | Redirige a `/login` si no hay sesión |
| `lib/auth-cookies.ts` | Nombre, duración y flag `secure` de la cookie, y timeout de inactividad (30 min) |
| `lib/report-*.ts` | Tipos, llamadas y formato del reporte |

Arquitectura y seguridad: [`../docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md). Despliegue: [`../docs/OPERACION.md`](../docs/OPERACION.md).

> Lee `AGENTS.md`: esta versión de Next.js trae cambios incompatibles con versiones anteriores.
