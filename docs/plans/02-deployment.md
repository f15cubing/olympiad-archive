# Plan: Deployment

Goal: get the archive running on the public internet — a static frontend talking to a
hosted FastAPI backend backed by managed Postgres — safely and repeatably.

## ⚠️ Blocker before ANY public deploy: no auth on writes

Every mutating endpoint is currently **unauthenticated**: `POST/DELETE /competitions`,
`POST/PUT/DELETE /problems`, `POST/DELETE /solutions`, `POST /tags`, and both
`/tagging` endpoints. Deployed as-is, anyone on the internet can delete the entire
archive or burn the Gemini quota. **This must be fixed before going public** (see
Phase 0.5). It is called out here because it changes the deploy shape.

## Current state vs. what production needs

| Area | Today | Needed |
|---|---|---|
| DB URL | Hardcoded `sqlite+aiosqlite:///./olympiad.db` (`database.py:5`), `echo=True` | Read `DATABASE_URL` from env; Postgres in prod; `echo=False` |
| DB driver | `asyncpg` already in requirements ✅ | Use it (`postgresql+asyncpg://...`) |
| Schema | `Base.metadata.create_all` at startup (`main.py:11`) | Alembic migrations (safe schema evolution) |
| CORS | Hardcoded `http://localhost:5173` (`main.py:19`) | Env-driven allowed origins |
| Frontend API URL | Hardcoded `http://localhost:8000` in **every** component + `taggingService.js:5` | Single client reading `VITE_API_BASE_URL` |
| Secrets | `GEMINI_API_KEY` via `.env` locally | Platform secret manager |
| Dependencies | `requirements.txt` is a UTF-16 `pip freeze` dump incl. `google-auth==2.49.0.dev0` (a dev pin) | UTF-8, runtime-only, no dev/pre-release pins |
| Container | none | Dockerfiles + compose |
| Health | `GET /` returns a message (usable as healthcheck) | Keep, or add `/health` |

## Phase 0 — Config & code prerequisites (no hosting yet)

These are small code changes that make the app deployable at all.

1. **Env-driven DB** (`database.py`):
   ```python
   import os
   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./olympiad.db")
   engine = create_async_engine(DATABASE_URL, echo=os.getenv("SQL_ECHO") == "1")
   ```
2. **Env-driven CORS** (`main.py`): read a comma-separated `CORS_ORIGINS`.
3. **Frontend API client**: create `frontend/src/services/api.js` exporting a single
   axios instance with `baseURL: import.meta.env.VITE_API_BASE_URL`. Replace all
   inline `http://localhost:8000` literals (YearList, ProblemList, CompetitionList,
   ProblemDetail, Search, taggingService) with it. Add `frontend/.env.example` with
   `VITE_API_BASE_URL=http://localhost:8000`. **This is a prerequisite** — the built
   frontend bakes in whatever URL it has at build time.
4. **Fix `requirements.txt`**: regenerate as UTF-8, split into runtime vs. dev, and
   replace the `.dev0` pins with stable releases. Verify a clean install on Python 3.13.
5. **Add `.env.example`** at repo root documenting `DATABASE_URL`, `CORS_ORIGINS`,
   `GEMINI_API_KEY`, `SQL_ECHO`.

## Phase 0.5 — Minimal auth for writes (gate before public)
- Simplest viable: an `ADMIN_TOKEN` env var; a FastAPI dependency that checks a
  `Authorization: Bearer` / `X-Admin-Token` header on all mutating routes; reads stay
  public. Frontend admin actions send the token (entered once, stored in memory/local).
- Alternative if multi-user is wanted later: proper auth (OAuth / JWT). Out of scope
  for a first launch — the token gate is enough to stop anonymous vandalism.

## Phase 1 — Migrations
- Introduce **Alembic**; generate the initial migration from the current models.
- Keep `create_all` for local/dev convenience but run migrations on deploy.
- Rationale: once there's real data in Postgres, `create_all` can't evolve columns.

## Phase 2 — Containerize
- **Backend `Dockerfile`**: `python:3.13-slim`, install runtime reqs,
  `uvicorn main:app --host 0.0.0.0 --port $PORT`. Run migrations on startup or via an
  entrypoint step.
- **Frontend**: `npm ci && npm run build` → serve the static `dist/` (nginx image, or
  better, a static host/CDN — see Phase 3).
- **`docker-compose.yml`** for local parity: `backend` + `postgres` + `frontend`, with
  a named volume for Postgres. Lets contributors run the whole stack with one command.

## Phase 3 — Hosting (recommended path)
The app splits cleanly into **static frontend + API + DB**:
- **Frontend** → Vercel / Netlify / Cloudflare Pages. Build with `VITE_API_BASE_URL`
  pointing at the API's public URL. Free tier is plenty.
- **Backend** → Render / Railway / Fly.io as a web service from the Dockerfile.
- **Database** → the platform's managed Postgres (Render Postgres, Railway PG, Fly
  Postgres, or Supabase/Neon). Set `DATABASE_URL` from the managed instance.
- **Secrets** → set `GEMINI_API_KEY`, `ADMIN_TOKEN`, `DATABASE_URL`, `CORS_ORIGINS`
  in the platform dashboard, never in git.

Concrete recommended combo (lowest ops): **Cloudflare Pages (frontend) + Render web
service (backend) + Neon/Render Postgres**. Alternative all-in-one: **Fly.io** for both
backend and Postgres.

## Phase 4 — CI/CD & ops
- Extend the CI workflow (see test-suite plan) to build images and deploy on merge to
  `main` (or trigger the platform's git integration). Run Alembic migrations as a
  release step.
- **Rate-limit the `/tagging` endpoints** in prod (they cost Gemini quota) — or disable
  them publicly and only tag via the CLI.
- **Observability**: structured logging (turn off `echo`), optional Sentry for errors,
  uptime check hitting `/`.
- **Backups**: enable managed-Postgres automated backups; snapshot before bulk loads.
- **HTTPS + domain**: platform-provided certs; custom domain optional.

## Suggested phasing / DoD
1. Phase 0 + 0.5 merged → app runs against Postgres locally via env vars, writes gated.
2. Alembic in place; compose brings up the full stack locally.
3. Staging deploy of all three tiers wired together; smoke test browse + search.
4. Production deploy with secrets, backups, and CD; `/tagging` protected or CLI-only.

**Done when:** a fresh visitor can browse/search the live site, the API is on managed
Postgres with migrations, writes require the admin token, secrets live in the platform,
and merges to `main` auto-deploy.
