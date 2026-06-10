# AuditSaaS

ISA-compliant audit management system for a small audit firm. Modular monolith
FastAPI API + React SPA, hosted on AWS (S3/CloudFront for the UI, one ECS Fargate
task behind an ALB for the API, RDS PostgreSQL).

**Implementation plan:** see [checklist.md](checklist.md) — the source of truth for
phases, deliverables, and architecture decisions.

## Repo layout

| Path | What |
|---|---|
| `audit-api/` | FastAPI backend (Python 3.12, uv, SQLAlchemy + Alembic) |
| `audit-client/` | React 18 + TypeScript + Vite SPA (pnpm, Tailwind, Clerk) |
| `infra/` | Terraform stack (VPC, ECS/ALB, RDS, S3/CloudFront, ACM, SES, SSM) |
| `docs/` | Deployment guide, DB docs, user manual |

## Local development

Prereqs: Docker, uv, Node 22 + pnpm.

```bash
# 1. Postgres
docker compose up -d db

# 2. API (port 5000)
cd audit-api
uv sync
uv run uvicorn main:app --port 5000 --reload

# 3. Client (port 3001)
cd audit-client
pnpm install
pnpm dev
```

API docs at http://localhost:5000/docs once running.

## Quality gates (run before pushing)

```bash
# audit-api
uv run ruff format . && uv run ruff check . && uv run pytest

# audit-client
pnpm lint && pnpm tsc --noEmit && pnpm test run && pnpm build
```

CI enforces all of the above on every PR.
