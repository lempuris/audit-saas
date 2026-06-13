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
      register-domain`, ~$15/yr for `.com`; no domain/zone exists for this project) — or, if
      `.co.tz` is required, register with a tzNIC-accredited registrar and set its NS
      records to the Route 53 hosted zone
- [ ] Route 53 hosted zone created (Terraform) and delegation verified (`dig NS`)
- [ ] DNS records: `audit.<domain>` → CloudFront, `api.audit.<domain>` → ALB;
      ACM certificates issued via DNS validation in both required regions
- [x] GitHub Actions — `ci-cd-api.yml`: ruff + pytest + docker build → push ECR →
      update ECS service; `ci-cd-client.yml`: lint + tsc + vitest + build → S3 sync →
      CloudFront invalidation
- [x] Alembic migration job runs on deploy (one-off ECS task or entrypoint step)

> **Phase 0 status (2026-06-10, deployed):** The stack (44 resources) is
> applied in `eu-west-1` with `domain_name = ""` and verified end-to-end:
> the SPA and API are live at https://dn46rvtw2v7wc.cloudfront.net,
> `/api/health` returns 200 with database connectivity (via both the
> CloudFront `/api/*` proxy and the ALB directly), GitHub repo variables are
> set from the Terraform outputs, and merged PRs auto-deploy both components
> (proven by PRs #2 and #3). Workflow actions are on Node 24-compatible
> majors ahead of GitHub's 2026-06-16 cutover.
>
> The three unchecked items above are all blocked on the firm's `.com` vs
> `.co.tz` decision and do **not** block Phase 1:
>
> 1. **Register the domain** (`infra/README.md` step 1).
> 2. **Set `domain_name` in `terraform.tfvars` and re-apply** — creates the
>    hosted zone, DNS records, and ACM certs, and removes the temporary
>    CloudFront→ALB proxy. If registered outside Route 53, the apply waits at
>    cert validation until NS records are delegated (verify with `dig NS`).
> 3. **Update the `VITE_API_URL` repo variable** to
>    `https://api.audit.<domain>` and redeploy the client.
>
> Before Phase 1 starts:
> - ✅ Clerk values set (2026-06-10): SSM parameters
>   `/auditsaas/clerk_secret_key` and `/auditsaas/clerk_jwks_url` and repo
>   variable `VITE_CLERK_PUBLISHABLE_KEY` hold real values for Clerk instance
>   `engaged-sole-65.clerk.accounts.dev` (test mode); the API task was
>   redeployed and the client rebuilt so both run with them. Rotate the
>   secret key in the Clerk dashboard before go-live.
> - ✅ Terraform state migrated to S3 (2026-06-10):
>   `s3://auditsaas-tfstate-176835474511/auditsaas/terraform.tfstate`,
>   versioned + encrypted, S3-native lockfile (no DynamoDB). Run
>   `terraform init` once after cloning (README "State" section).
>
> **Nothing blocks Phase 1.**
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

- [x] Clerk backend token verification middleware (RS256 vs instance JWKS, default
      deny, `/api/me`) — merged to `master` 2026-06-11
- [x] Clerk user sync webhook (`clerk_webhook_router`): Svix-verified, syncs
      user.created/updated/deleted into the local `users` mirror — merged 2026-06-11 (PR #10)
- [x] **MFA enforced** via Clerk policy (dashboard config — steps in
      `docs/clerk-setup.md` §3; done 2026-06-11 together with the session-token
      role claim, §1)
- [x] RBAC backend permission checks: Admin / Partner / Manager / Auditor roles
      (Clerk metadata → `require_roles()` per route, default deny) — merged
      2026-06-11
- [x] RBAC permission matrix documented in `/docs` (`docs/rbac-permission-matrix.md`,
      PR #15)
- [x] User management screens (Admin): invite via Clerk, deactivate, assign role
      (API PR #12, screen PR #17)
- [x] **Audit trail feature**: immutable log of all writes (service hook with
      before/after snapshots) and logins (session.created webhook); read-only viewer
      for Admin/Partner (PRs #11, #18)
- [x] **Clients feature** (router/service/models + screens): CRUD, industry, contacts,
      risk rating; DELETE archives instead of removing (PRs #13, #19)
- [x] **Engagements feature**: create engagement (client, type, fiscal year, status
      workflow), team assignment, independence/conflict confirmation checklist —
      fieldwork blocked until all members confirm; completion requires Partner/Admin
      (PRs #14, #20)
- [x] Client shell: navigation, role-aware menus, client list/detail,
      engagement list/detail screens (PR #16)

> **Phase 1 status (2026-06-11, merged & deployed):** All Phase 1 code is in
> `master` — auth middleware + `/api/me` (PR #9), Clerk user-sync webhook +
> `users` table (PR #10), and the full feature chain merged in order on
> 2026-06-11: #11 audit trail → #12 users API → #13 clients → #14 engagements
> → #15 RBAC/Clerk docs → #16 client shell → #17 users screen → #18 audit
> viewer → #19 clients screens → #20 engagements screens → #21 checklist.
> `ci-cd-api` and `ci-cd-client` deploys are green; migrations 0001–0004
> (users, audit_trail, clients, engagements + team members) applied on deploy.
> Backend: pytest 67 passed, ruff clean. Frontend: vitest 31 passed,
> ESLint/tsc/build clean.
>
> **Clerk dashboard config done (2026-06-11)**, all of docs/clerk-setup.md
> §1–3: session-token role claim added and verified on the deployed app;
> webhook endpoint created (user.created/updated/deleted + session.created)
> with its signing secret in SSM (`/auditsaas/clerk_webhook_secret`); MFA
> (TOTP) set to required. Wiring the webhook secret required a manual
> `terraform apply` (task definition revision 2 now injects
> `CLERK_WEBHOOK_SECRET`; the parameter was imported into Terraform state) —
> the Phase 1 Terraform changes had been merged but never applied.
>
> Remaining for Phase 1 acceptance:
>
> 1. Assign roles to the firm's users via public_metadata / the Users screen
>    (one user assigned so far).
> 2. Verify acceptance end-to-end on the deployed app: auditor blocked from
>    admin endpoints, writes appear in the audit trail (including
>    session.created logins via the webhook), engagement created through
>    the UI.

**Acceptance:** Auditor role cannot reach admin endpoints (tested); every write
appears in the audit trail; an engagement can be created end-to-end in the UI.

---

## Phase 2 — Audit Planning & Risk Assessment

**Goal:** Plan an audit per ISA: materiality, risk, programs, trial balance.

- [x] **Trial balance import** (XLSX/CSV): column mapping UI, validation, account
      grouping into financial statement areas, prior-year comparison (API PR #24,
      screen PR #30)
- [x] **Materiality feature**: benchmark selection (revenue/assets/profit), overall +
      performance materiality + clearly-trivial threshold; partner approval and locking
      (API PR #26, screen PR #31)
- [x] **Risk assessment feature**: entity-level and assertion-level risks
      (inherent/control/combined), risks linked to planned responses/procedures
      (API PR #27, screen PR #31; risk↔procedure links in PR #28/#32)
- [x] **Audit programs feature**: seedable ISA-referenced procedure templates per FS
      area; tailor per engagement; assign procedures with status and due dates
      (API PR #28, screen PR #32)
- [x] **Lead schedules** auto-generated per FS area from the imported trial balance
      (API PR #29, screen PR #32)
- [x] Planning dashboard: engagement progress, my assigned procedures
      (API PR #29, screens PR #32)

> **Phase 2 status (2026-06-12, merged & deployed):** All six features are
> in `master`, merged in stack order on 2026-06-12: #24/#25 TB import API →
> #26 materiality API → #27 risks API → #28 audit programs API (incl. the
> 27-procedure ISA template library + seed endpoint) → #29 lead schedules +
> planning dashboard API → #30 TB screen (column-mapping wizard, FS-area
> regrouping, PY comparison) → #31 materiality + risk screens → #32 program
> / lead schedules / dashboard screens → #33 checklist. All `ci-cd-api` and
> `ci-cd-client` deploys green; the ECS task was verified (via ECR digest)
> to run the image containing the full backend, and its startup applied
> migrations 0006–0008 (materiality_assessments, risks, procedure_templates
> + engagement_procedures + risk_procedure_links). `/api/health` ok in
> production. Backend: pytest 138 passed, ruff clean. Frontend: vitest 56
> passed, ESLint/tsc/build clean.
>
> No manual seeding step is needed: the program screen's "Load standard
> ISA program" button seeds the firm template library (idempotent) and
> bulk-adds it to the engagement in one go.
>
> **Phase 2 acceptance — verified 2026-06-13.** The demo engagement was run
> end-to-end on the deployed app (script in `docs/phase2-acceptance-demo.md`,
> sample data in `docs/sample-trial-balance.csv`): TB imported via the
> column-mapping wizard with FS-area grouping refined; materiality assessment
> saved, approved and locked as Partner/Admin; risks documented and linked to
> the standard ISA program; lead-schedule totals reconciled to the imported TB.
>
> Fixed during acceptance (separate PRs): invited-user names not populating +
> audit-trail actor showing raw Clerk ids + deleted-in-Clerk users (PR #35),
> and the procedure-assignee free-text box replaced with a team-member
> dropdown (PR #36) — both merged and deployed.
>
> **Phase 2 is complete. Phase 3 may begin.**

**Acceptance:** ✅ A demo engagement has an imported TB, locked materiality, documented
risks linked to programs, and lead schedules with correct totals.

---

## Phase 3 — Fieldwork & Documentation

**Goal:** Execute the audit: working papers, evidence, sampling, review notes.

- [x] **Working papers feature**: indexed per FS area (A-1, B-2.1, …),
      procedure/result/conclusion structure, preparer + date stamped, version history
      (API PR #38, screen PR #39)
- [x] **Documents feature**: upload evidence to S3 via presigned URLs, versioning,
      link documents to working papers, access logged in audit trail
      (API + infra PR #40, screen PR #41)
- [x] **Cross-referencing**: link working papers ↔ TB lines ↔ documents; clickable refs
      (API PR #42, UI PR #43)
- [x] **Tick marks**: configurable tick-mark library applied to schedule lines, with legend
      (API PR #44, UI PR #45)
- [x] **Sampling feature**: random, systematic, and monetary-unit sampling; sample size
      from population/materiality/risk inputs; selection basis stored
      (API PR #46, screen PR #47)
- [x] **Review notes feature**: raise on any working paper, assign, respond, clear;
      open-notes dashboard (API PR #48, UI PR #49)

> **Phase 3 status (2026-06-13, merged & deployed):** All six features are in
> `master`, merged as a stacked PR set #38–#50 — each an API slice then a
> screen/UI slice (working papers #38/#51, documents #40/#41, cross-refs
> #42/#43, tick marks #44/#45, sampling #46/#47, review notes #48/#49, docs #50).
> Migrations 0009–0014 (working_papers +versions, documents, cross_references,
> tick_marks +applications, samples, review_notes) applied on deploy; single
> Alembic head 0014. Backend pytest 193 passed, frontend vitest 86 passed,
> ruff/ESLint/tsc/build clean.
>
> The documents infrastructure (task env `DOCUMENTS_BUCKET` +
> `AWS_DEFAULT_REGION`, IAM `s3:GetObjectVersion`, documents-bucket CORS) was
> applied via a manual `terraform apply` (task-def revision 3). Deploys are now
> serialized by a CI concurrency guard (PR #52) after back-to-back merges raced
> on the S3 sync. Post-merge UX fixes (PR #53): working-paper preparer/editor
> names resolved to people, a proper document-upload button, and readable
> sampling validation errors.
>
> **Phase 3 acceptance — verified 2026-06-13.** A demo engagement was run
> end-to-end on the deployed app per `docs/phase3-acceptance-demo.md`: a working
> paper prepared (objective/result/conclusion, versioned); an evidence document
> uploaded via presigned URL and downloaded (access logged in the audit trail);
> the working paper cross-referenced to a TB line and the document; a tick mark
> applied to a schedule line with its legend; random / systematic / monetary-unit
> samples drawn with their selection bases stored; and a review note raised,
> responded to and cleared (leaving the open-notes dashboard).
>
> **Phase 3 is complete. Phase 4 may begin.**

**Acceptance:** ✅ A working paper can be prepared with evidence attached,
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
