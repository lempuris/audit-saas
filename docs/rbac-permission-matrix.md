# RBAC Permission Matrix

Roles live in Clerk `public_metadata.role` and reach the API inside the session
token (see [clerk-setup.md](clerk-setup.md)). The backend enforces **default
deny**: every endpoint requires a valid Clerk session token, and role-gated
endpoints reject users whose role is missing or unrecognised. Role checks are
implemented with `require_roles()` (`audit-api/middleware/auth.py`); the gates
below are asserted by unit tests.

## Roles

| Role | Intended for |
|---|---|
| **Admin** | Practice administrator: user accounts, firm-wide settings |
| **Partner** | Engagement partners: final approvals, completion sign-off |
| **Manager** | Audit managers: run engagements day to day |
| **Auditor** | Field staff: execute assigned work |

## Endpoint matrix

✅ allowed · ❌ 403

| Endpoint | Admin | Partner | Manager | Auditor |
|---|---|---|---|---|
| `GET /api/me` | ✅ | ✅ | ✅ | ✅ (any authenticated user, role not required) |
| **Users** |
| `GET /api/users` | ✅ | ❌ | ❌ | ❌ |
| `POST /api/users/invitations` | ✅ | ❌ | ❌ | ❌ |
| `PATCH /api/users/{id}/role` | ✅ | ❌ | ❌ | ❌ |
| `POST /api/users/{id}/deactivate` / `reactivate` | ✅ | ❌ | ❌ | ❌ |
| **Audit trail** |
| `GET /api/audit-trail` | ✅ | ✅ | ❌ | ❌ |
| **Clients** |
| `GET /api/clients`, `GET /api/clients/{id}` | ✅ | ✅ | ✅ | ✅ |
| `POST /api/clients`, `PATCH /api/clients/{id}` | ✅ | ✅ | ✅ | ❌ |
| `DELETE /api/clients/{id}` (archive) | ✅ | ✅ | ❌ | ❌ |
| **Engagements** |
| `GET /api/engagements`, `GET /api/engagements/{id}` | ✅ | ✅ | ✅ | ✅ |
| `POST /api/engagements`, `PATCH /api/engagements/{id}` | ✅ | ✅ | ✅ | ❌ |
| `PATCH /api/engagements/{id}/status` | ✅ | ✅ | ✅¹ | ❌ |
| `POST /api/engagements/{id}/team`, `DELETE …/team/{user}` | ✅ | ✅ | ✅ | ❌ |
| `POST /api/engagements/{id}/team/confirm-independence` | ✅² | ✅² | ✅² | ✅² |
| **Unauthenticated** |
| `GET /api/health` (ALB health checks) | public |
| `POST /api/webhooks/clerk` (Svix-signature verified) | public |

¹ Managers may move engagements through the workflow, but the transition to
`completed` additionally requires Partner or Admin (enforced in
`engagements_service.change_status`).

² Any staff role, but only for an engagement the caller is a team member of —
each person confirms their own independence.

## Workflow rules (beyond per-endpoint gates)

- Engagement status must follow `draft → planning → fieldwork → review →
  completed`; `review → fieldwork` is allowed for rework. Anything else is 409.
- `planning → fieldwork` is blocked until the engagement has a team **and**
  every member has confirmed independence (the independence/conflict
  confirmation checklist).
- Clients are archived, never deleted; archiving requires Partner/Admin.
- Every create/update/delete and every login is written to the immutable
  audit trail; only Admin/Partner can read it.
