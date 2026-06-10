# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ISA-compliant audit management system for a small audit firm: a modular-monolith
FastAPI API + React SPA on AWS (S3/CloudFront for the UI, one ECS Fargate task
behind an ALB, RDS PostgreSQL).

**`checklist.md` is the source of truth** — phases, fixed architecture decisions,
agent conventions, and explicit non-goals (no microservices, no Kubernetes/Kafka,
no Redis/Mongo, no Prometheus stack). Read it before starting any feature work,
and do not start a phase before the previous phase's acceptance criteria pass.

## Commands

### Backend (`audit-api/`, Python 3.12 + uv)

```bash
uv sync                                        # install deps
uv run uvicorn main:app --port 5000 --reload   # run locally (needs Postgres: docker compose up -d db)
uv run ruff format . && uv run ruff check .    # format + lint (run after every change)
uv run pytest                                  # unit tests (integration/smoke excluded by default)
uv run pytest -m integration                   # integration tests (require Postgres)
uv run pytest tests/test_health.py::test_name  # single test
uv run alembic revision --autogenerate -m "…"  # new migration
uv run alembic upgrade head                    # apply migrations
```

### Frontend (`audit-client/`, Node 22 + pnpm)

```bash
pnpm install
pnpm dev                  # dev server on :3001
pnpm lint                 # ESLint, --max-warnings 0
pnpm exec tsc --noEmit    # typecheck
pnpm test run             # vitest (run once; `pnpm test` watches)
pnpm vitest run src/services/api.test.ts   # single test file
pnpm build                # tsc -b + vite build
```

### Infra (`infra/`, Terraform)

```bash
terraform fmt -check -recursive && terraform validate   # what CI checks
terraform init    # once after cloning — state is in S3 (see infra/README.md)
```

CI (GitHub Actions, one workflow per component, path-filtered) enforces all of the
above on every PR and auto-deploys on merge to `master`: API → ECR → ECS forced
deployment (entrypoint.sh runs `alembic upgrade head` on start); client → S3 sync +
CloudFront invalidation. `terraform apply` is always manual. PRs are created as
drafts; CI must be green to merge.

## Architecture

Feature-slice pattern (mirrors the Klair platform). A backend feature =
`routers/<feature>_router.py` + `services/<feature>_service.py` +
`models/<feature>_models.py` (Pydantic schemas); the client side adds
`src/screens/` + `components/` + `hooks/`. See the health feature for the
reference implementation end-to-end (router → service → Pydantic model →
`src/services/api.ts` client → `useApi` hook → screen).

Key rules (full list in checklist.md "Conventions for agents"):

- **No business logic in routers** — routers validate, delegate to services, shape responses.
- **Exceptions MUST propagate** to FastAPI error handlers. Never catch and return
  false/zero/empty — clients must distinguish empty results from errors.
- DB access is async SQLAlchemy 2.0 via the `get_db` dependency
  (`database/session.py`); every table inherits `BaseModel`
  (`database/models.py`: UUID PK + timezone-aware `created_at`/`updated_at`).
  Schema changes go through Alembic migrations in `database/migrations/versions/`.
- Settings come only from env vars via `config/settings.py` (pydantic-settings,
  cached with `lru_cache`); copy `.env.example` to `.env` locally. Production
  secrets live in SSM Parameter Store, injected as ECS task secrets.
- Auth is Clerk: frontend `@clerk/clerk-react` provider + backend token
  verification middleware. Every endpoint authenticated; RBAC roles
  (Admin/Partner/Manager/Auditor) enforced per route, default deny.
- Every create/update/delete on business data must write an immutable
  audit-trail row (who, what, when, before/after).
- Frontend API calls go through the `ApiClient` class (`src/services/api.ts`),
  which injects the Clerk token; don't use raw `fetch` in components.

## Deployment state (as of 2026-06-10)

Phase 0 is deployed to `eu-west-1` in **domainless mode** (`domain_name = ""`):
the SPA is served from the default CloudFront domain, which proxies `/api/*` to
the ALB; Route 53/ACM/SES are skipped until the firm's `.com` vs `.co.tz` domain
decision lands. Terraform state is in S3 (bucket created by hand, outside the
stack). The Fargate task deliberately runs in public subnets (SG admits only the
ALB) to avoid NAT gateway cost — don't "fix" this. Bootstrap and domain-cutover
steps are in `infra/README.md`.
