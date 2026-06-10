# AuditSaaS — Phased MVP Implementation Checklist

ISA-compliant audit management system for a small audit firm. This document is the
source of truth for agents developing the application. Work through phases in order;
do not start a phase until the previous phase's acceptance criteria pass.

The design approach deliberately mirrors the **Klair** platform
(`D:\Musa.Nduati\Trilogy\Klair`): a two-package repo (FastAPI API + React/TS/Vite
client), feature-based routers/services/models on the backend, strict lint/test
gates, and GitHub Actions CI/CD per component.

---

## Architecture Decisions (fixed — do not deviate)

Per client feedback, the original microservices proposal is **rejected** as too
complex and costly. The MVP is a **modular monolith API + static SPA**:

| Concern | Decision | Rationale |
|---|---|---|
| Backend | **Python 3.12, FastAPI (async)** + Pydantic models | Klair pattern; lightweight, fast to develop |
| Packaging | **uv** for Python, **pnpm** for frontend | Klair pattern |
| ORM / migrations | **SQLAlchemy 2.0 (async) + Alembic** | Postgres-first, explicit migrations |
| Frontend | **React 18 + TypeScript + Vite**, Tailwind CSS + Radix primitives, TanStack Table, Recharts | Klair pattern (minus MUI bloat) |
| Auth | **Clerk** (frontend components + backend token verification) | Klair pattern; free tier covers a small firm; MFA, sessions, invitations out of the box |
| Database | **Single RDS PostgreSQL 16, `db.t4g.micro`, single-AZ, 20 GB gp3** | Feedback item 06; smallest paid tier, scale up in place when needed |
| API hosting | **ECS Fargate — one service, one task (0.25 vCPU / 0.5 GB)** behind an **ALB** | User decision; serverless containers, no instance management |
| UI hosting | **S3 (private bucket) + CloudFront** with OAC | User decision; static SPA, pennies per month |
| File storage | **S3** (documents bucket, presigned URLs) | Evidence/document store |
| Images | **ECR** (api repo), deployed by GitHub Actions | Klair CI/CD pattern |
| PDF reports | **WeasyPrint** (HTML → PDF) in the API container | ISA report templates as HTML |
| TB import | **openpyxl / pandas** (XLSX + CSV) | Trial balance ingestion |
| Email | **AWS SES** | Notifications |
| Domain | **Purchase via Route 53 Domains** (e.g. `retrofitbusinesspact.com`, verified available @ $15/yr) — note Route 53 **cannot** register `.co.tz`; if the firm insists on `audit.retrofitbusinesspact.co.tz` (feedback item 07), register it with a tzNIC-accredited registrar and delegate NS to Route 53 | One registrar/DNS console; auto-renewal; works with ACM DNS validation |
| DNS / TLS | **Route 53 hosted zone** ($0.50/mo): `audit.<domain>` → CloudFront, `api.audit.<domain>` → ALB; **ACM** certs (us-east-1 for CloudFront, eu/af region for ALB), DNS-validated | Feedback item 07 |
| Backups | **RDS automated backups** (7-day PITR) + weekly snapshot export; S3 versioning on documents | Feedback item 10, near-zero effort |
| IaC | **Terraform**, one small stack in `/infra` | Reproducible provisioning; satisfies handover/deployment-guide requirement |
| CI/CD | **GitHub Actions**: separate api / client / infra workflows (Klair pattern); `main` = dev env conventions, tags = prod | Klair pattern |
| Monitoring | CloudWatch logs + alarms (CPU, 5xx, DB storage), ECS health checks | Native, no extra stack |

**Estimated running cost: ≈ $45/month** (Fargate ~$9, ALB ~$17, RDS t4g.micro ~$14,
S3/CloudFront/ECR/Route53 ~$5) **+ $15/yr domain registration**. Scale path: bigger Fargate task / RDS class — no
re-architecture.

### Explicit non-goals for MVP (do NOT build)
- ❌ Kubernetes, Kafka, RabbitMQ, microservices, Kong
- ❌ MongoDB, Redis, Elasticsearch, multi-database design
- ❌ Prometheus/Grafana/ELK/Jaeger, New Relic/Datadog
- ❌ Mobile/desktop apps, ML risk scoring, multi-AZ/multi-region HA

### Repo structure (mirrors Klair)
```
/audit-api            FastAPI backend
  routers/            one <feature>_router.py per feature
  services/           one <feature>_service.py — all business logic lives here
  models/             Pydantic schemas (<feature>_models.py)
  database/           SQLAlchemy models, session, Alembic migrations
  middleware/         auth (Clerk verification), audit-trail, request logging
  config/             settings via pydantic-settings (env vars only)
  templates/          report HTML templates (WeasyPrint)
  utils/  tests/
/audit-client         React + TS + Vite SPA
  src/screens/  components/  hooks/  services/  contexts/  types/  utils/
/infra                Terraform stack (VPC, ECS, ALB, RDS, S3, CloudFront, ECR, SES, ACM)
/docs                 user manual, DB docs, deployment guide
```

### Conventions for agents (Klair practices)
- **Backend:** `uv` for deps; `uv run ruff format` + `ruff check` after every change;
  pytest with `unit` / `integration` / `smoke` markers (integration excluded by default).
- **Exceptions MUST propagate** to FastAPI error handlers. NEVER catch and return
  false/zero/empty data — clients must be able to distinguish empty results from errors.
- **Frontend:** ESLint strict (`--max-warnings 0`); pre-push: `pnpm lint`,
  `pnpm tsc --noEmit`, `pnpm build`; vitest for tests.
- Feature slice = router + service + models (+ screen/components/hooks on the client).
  No business logic in routers; routers validate, delegate, and shape responses.
- Every endpoint authenticated via Clerk middleware; RBAC roles
  (**Admin, Partner, Manager, Auditor**) enforced per route. Default deny.
- Every create/update/delete on business data writes an immutable audit-trail row
  (who, what, when, before/after) via middleware/service hook.
- SQLAlchemy models: UUID PKs, `created_at`/`updated_at` on all tables.
- Secrets via env vars only (ECS task secrets from SSM Parameter Store); never committed.
- CI must be green to merge; PRs created as drafts.

---

## Phase 0 — Foundation & Infrastructure

**Goal:** Skeleton SPA on CloudFront and API on Fargate, both live over HTTPS.

- [x] Initialize monorepo (`/audit-api`, `/audit-client`, `/infra`, `/docs`), README
- [x] Scaffold FastAPI app (uv, ruff, pytest markers, settings, `/api/health`),
      SQLAlchemy + Alembic wired to Postgres, Dockerfile (uvicorn workers)
- [x] Scaffold React + TS + Vite app (pnpm, Tailwind, ESLint strict, vitest);
      Clerk provider + sign-in screen; API client with auth token interceptor
- [x] Local dev: docker-compose for Postgres; `uv run` API on :5000, `pnpm dev` on :3001
- [x] Terraform stack in `/infra`: VPC (public/private subnets), ECR, ECS cluster +
      Fargate service (1 task) + ALB + target group health checks, RDS PostgreSQL
      `db.t4g.micro` (private subnet), S3 buckets (ui, documents) + CloudFront with OAC,
      ACM certs, SSM parameters for secrets, SES identity, IAM task roles (least privilege)
- [ ] **Register domain**: purchase via Route 53 Domains (`aws route53domains
      register-domain`, ~$15/yr for `.com`; account has no domains/zones yet) — or, if
      `.co.tz` is required, register with a tzNIC-accredited registrar and set its NS
      records to the Route 53 hosted zone
- [ ] Route 53 hosted zone created (Terraform) and delegation verified (`dig NS`)
- [ ] DNS records: `audit.<domain>` → CloudFront, `api.audit.<domain>` → ALB;
      ACM certificates issued via DNS validation in both required regions
- [x] GitHub Actions — `ci-cd-api.yml`: ruff + pytest + docker build → push ECR →
      update ECS service; `ci-cd-client.yml`: lint + tsc + vitest + build → S3 sync →
      CloudFront invalidation
- [x] Alembic migration job runs on deploy (one-off ECS task or entrypoint step)

> **Phase 0 status (2026-06-10):** All code-side items are done and verified
> (ruff/pytest, lint/tsc/vitest/build, `terraform validate` all green). The three
> unchecked items are AWS account actions, in order:
>
> 1. **Register the domain** (a purchase — needs the firm's confirmation of
>    `.com` vs `.co.tz`). Commands and the `.co.tz` delegation caveat are in
>    `infra/README.md` step 1.
> 2. **`terraform apply`** — creates the hosted zone, DNS records, and ACM certs
>    in one shot. Follow `infra/README.md` steps 2–5: copy
>    `terraform.tfvars.example`, apply (the run waits at cert validation until
>    the registrar delegates NS to the new zone — verify with `dig NS`), set the
>    real Clerk values in SSM, and push a first image so ECS has something to run.
>    If the domain was registered via Route 53 Domains, import or replace the
>    auto-created zone (README step 3 note). Afterwards, migrate state to an S3
>    backend (README "State" section).
> 3. **Wire CI to AWS** — set GitHub repo variables from the Terraform outputs
>    (`AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`, `UI_BUCKET`,
>    `CLOUDFRONT_DISTRIBUTION_ID`, `VITE_API_URL`,
>    `VITE_CLERK_PUBLISHABLE_KEY`), then merge any PR touching `audit-api/` or
>    `audit-client/` to exercise the deploy jobs and check acceptance below.
>
> Design note: the Fargate task runs in **public subnets** (SG admits only the
> ALB) to avoid a ~$32/mo NAT gateway; RDS stays in private subnets. Default
> region is `eu-west-1` (`infra/variables.tf`) — `af-south-1` is closer to
> Tanzania but is an opt-in region not enabled on this AWS account.
>
> Domain registration is **not** a blocker for `terraform apply`: with
> `domain_name = ""` the stack skips Route 53/ACM/SES and serves the SPA from
> the default CloudFront domain (which proxies `/api/*` to the ALB). When the
> domain lands, set `domain_name` and re-apply.

**Acceptance:** `https://audit.retrofitbusinesspact.co.tz` serves the SPA;
`https://api.audit.retrofitbusinesspact.co.tz/api/health` returns 200 and confirms
DB connectivity; a merged PR auto-deploys both.

---

## Phase 1 — Users, Security & Clients

**Goal:** Staff log in securely; firm manages clients and engagements.

- [ ] Clerk integration end-to-end: backend token verification middleware, user sync
      webhook (`clerk_webhook_router`), **MFA enforced** via Clerk policy
- [ ] RBAC: Admin / Partner / Manager / Auditor roles (Clerk metadata → backend
      permission checks); permission matrix documented in `/docs`
- [ ] User management screens (Admin): invite via Clerk, deactivate, assign role
- [ ] **Audit trail feature**: middleware + service writing immutable log of all writes
      and logins; read-only viewer screen for Admin/Partner
- [ ] **Clients feature** (router/service/models + screens): CRUD, industry, contacts,
      risk rating
- [ ] **Engagements feature**: create engagement (client, type, fiscal year, status
      workflow), team assignment, independence/conflict confirmation checklist
- [ ] Client shell: navigation, role-aware menus, client list/detail,
      engagement list/detail screens

**Acceptance:** Auditor role cannot reach admin endpoints (tested); every write
appears in the audit trail; an engagement can be created end-to-end in the UI.

---

## Phase 2 — Audit Planning & Risk Assessment

**Goal:** Plan an audit per ISA: materiality, risk, programs, trial balance.

- [ ] **Trial balance import** (XLSX/CSV): column mapping UI, validation, account
      grouping into financial statement areas, prior-year comparison
- [ ] **Materiality feature**: benchmark selection (revenue/assets/profit), overall +
      performance materiality + clearly-trivial threshold; partner approval and locking
- [ ] **Risk assessment feature**: entity-level and assertion-level risks
      (inherent/control/combined), risks linked to planned responses/procedures
- [ ] **Audit programs feature**: seedable ISA-referenced procedure templates per FS
      area; tailor per engagement; assign procedures with status and due dates
- [ ] **Lead schedules** auto-generated per FS area from the imported trial balance
- [ ] Planning dashboard: engagement progress, my assigned procedures

**Acceptance:** A demo engagement has an imported TB, locked materiality, documented
risks linked to programs, and lead schedules with correct totals.

---

## Phase 3 — Fieldwork & Documentation

**Goal:** Execute the audit: working papers, evidence, sampling, review notes.

- [ ] **Working papers feature**: indexed per FS area (A-1, B-2.1, …),
      procedure/result/conclusion structure, preparer + date stamped, version history
- [ ] **Documents feature**: upload evidence to S3 via presigned URLs, versioning,
      link documents to working papers, access logged in audit trail
- [ ] **Cross-referencing**: link working papers ↔ TB lines ↔ documents; clickable refs
- [ ] **Tick marks**: configurable tick-mark library applied to schedule lines, with legend
- [ ] **Sampling feature**: random, systematic, and monetary-unit sampling; sample size
      from population/materiality/risk inputs; selection basis stored
- [ ] **Review notes feature**: raise on any working paper, assign, respond, clear;
      open-notes dashboard

**Acceptance:** A working paper can be prepared with evidence attached,
cross-referenced to the TB, tick-marked, sampled, and has a raised-and-cleared
review note.

---

## Phase 4 — Review, Completion & Reporting

**Goal:** Close the audit: sign-offs, completion checklist, ISA-compliant report.

- [ ] **Sign-off workflow**: prepared → reviewed (Manager) → approved (Partner) per
      working paper and per FS area; sign-offs immutable with timestamp
- [ ] **Completion checklist**: ISA-mapped (subsequent events, going concern,
      management representations, …); engagement cannot close with open items or
      uncleared review notes
- [ ] **Report templates**: ISA 700/705/706 opinion templates (unmodified, qualified,
      adverse, disclaimer) with firm letterhead, editable sections
- [ ] **PDF generation** (WeasyPrint) of audit report and management letter
- [ ] Engagement archive: lock all content at completion (read-only), retention metadata
- [ ] Firm dashboard: engagements by status, review queue, overdue procedures

**Acceptance:** Demo engagement completes the full lifecycle — sign-offs at all
levels, checklist done, final PDF generated, file archived and immutable.

---

## Phase 5 — Hardening, Operations & Handover

**Goal:** Production-ready and owned by the client (feedback items 10–11).

- [ ] Backups verified: RDS PITR enabled (7 days), weekly snapshot export, S3
      versioning + lifecycle on documents; **restore drill performed and documented**
- [ ] Security pass: HTTPS-only + HSTS via CloudFront/ALB, WAF rate limiting on auth
      routes (or ALB rule), security headers, dependency audit (`pip-audit`,
      `pnpm audit`), S3 buckets private with OAC only, IAM least-privilege review
- [ ] Monitoring: CloudWatch alarms (ECS CPU/memory, ALB 5xx, RDS storage/CPU),
      log retention set, external uptime check, error notifications to email
- [ ] Load sanity check with realistic data volumes (≥ 25 concurrent users on one task;
      document the scale-up runbook: task size → task count → RDS class)
- [ ] **Deployment guide** (`/docs`): Terraform apply from scratch + CI/CD runbook
- [ ] **Database documentation**: schema/ERD + data dictionary
- [ ] **User manual**: per-role guide with screenshots
- [ ] **Ownership handover**: repository access, AWS account/credentials, Clerk org
      ownership transferred; source code ownership confirmed in writing
- [ ] UAT with the audit firm on a real (sandbox) engagement; sign-off

**Acceptance:** Restore drill succeeds; all documentation delivered; client has full
repo, AWS, and Clerk access; UAT signed off.

---

## Post-MVP (only when the firm grows — not now)

Second Fargate task + autoscaling → larger RDS class / Multi-AZ → ElastiCache →
full-text search → analytics dashboards → client portal → mobile evidence capture.
All incremental — none requires a rewrite.
