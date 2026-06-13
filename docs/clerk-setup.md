# Clerk configuration (dashboard checklist)

The app uses Clerk instance `engaged-sole-65.clerk.accounts.dev` (test mode —
rotate the secret key and switch to a production instance before go-live).
These dashboard steps are **required** for the backend to work correctly.

## 1. Session token must carry the role (required)

Without this, every user's role is `null` and all role-gated endpoints
return 403.

1. Dashboard → **Sessions** → **Customize session token**.
2. Add:
   ```json
   {"role": "{{user.public_metadata.role}}"}
   ```
3. Save. Users must sign out/in (or the session refresh) to pick it up.

Roles are assigned by setting `public_metadata.role` on the user to one of
`admin`, `partner`, `manager`, `auditor` — either in the dashboard or via
`PATCH /api/users/{id}/role` (Admin-only, keeps the local mirror in sync).

## 2. Webhook endpoint (required for user sync + login audit)

1. Dashboard → **Webhooks** → **Add endpoint**.
2. URL: `https://dn46rvtw2v7wc.cloudfront.net/api/webhooks/clerk`
   (after the custom domain lands: `https://api.audit.<domain>/api/webhooks/clerk`).
3. Subscribe to events: `user.created`, `user.updated`, `user.deleted`,
   `session.created`.
4. Copy the endpoint's **signing secret** (`whsec_…`) and store it:
   ```
   aws ssm put-parameter --name /auditsaas/clerk_webhook_secret \
     --type SecureString --overwrite --value whsec_...
   ```
5. Force a new ECS deployment so the task picks it up:
   ```
   aws ecs update-service --cluster auditsaas --service api --force-new-deployment
   ```
   If the running task definition does not yet inject `CLERK_WEBHOOK_SECRET`
   (check `aws ecs describe-task-definition --task-definition auditsaas-api
   --query "taskDefinition.containerDefinitions[0].secrets"`), run
   `terraform apply` in `/infra` instead — it registers the new task
   definition revision and rolls the service. Done 2026-06-11 (revision 2).

## 3. Enforce MFA (required — Phase 1 acceptance)

1. Dashboard → **User & authentication** → **Multi-factor**.
2. Enable **Authenticator application (TOTP)** (and optionally backup codes).
3. Set MFA to **Required** so every staff member must enrol at first sign-in.

Clerk then enforces enrolment during sign-in; no backend change is needed.

## 4. Invitations

`POST /api/users/invitations` uses Clerk's invitation API; invited users get
an email sign-up link and appear in the local `users` table via the
`user.created` webhook once they accept. Set the invite's role at invite time
(it is stored in `public_metadata.role`).

**Require a name at sign-up (otherwise the Users list shows "—").** By default
Clerk treats the name as optional, and the invitation sign-up flow goes straight
to setting a password — so invited users land with `first_name`/`last_name` null
and the webhook syncs a nameless row. In the Clerk dashboard go to
**User & Authentication → Personal information** and set **Name = Required** so
sign-up collects it. The UI degrades gracefully regardless — `UserRecord` exposes
a computed `display_name` that falls back to the email local-part, then the Clerk
id — but a real name is better.

To fix a user already created without a name, edit their name in the Clerk
dashboard; that fires `user.updated` and the webhook backfills the mirror.

**Manage users in-app — never delete them in the Clerk dashboard.** Invite,
role changes, and deactivate/reactivate all happen on the in-app **Users**
screen, which calls the Clerk Backend API for you; admins never need the Clerk
dashboard for day-to-day user management. To remove someone, use **Deactivate**
— it bans the Clerk user (blocking sign-in) and keeps the mirror in sync, and is
reversible via Reactivate. Do **not** use the Clerk dashboard's *Delete user*:
the `users` table is a soft-delete mirror (rows are kept so audit-trail entries
can resolve their author), so a dashboard deletion leaves a stale row, and any
in-app action on it then fails because the Clerk user is gone. The app handles
this defensively — a Clerk 404 reconciles the row to inactive and returns a
clear message — but the row cannot be restored once the Clerk user is deleted.
Inactive users are hidden on the Users screen behind a "Show inactive" toggle.

## 5. Before go-live

- Rotate `CLERK_SECRET_KEY` (it was shared during development) and create a
  **production** Clerk instance.
- Update SSM parameters `/auditsaas/clerk_secret_key`, `/auditsaas/clerk_jwks_url`,
  `/auditsaas/clerk_webhook_secret`, and the repo variable
  `VITE_CLERK_PUBLISHABLE_KEY`; redeploy API + client.
