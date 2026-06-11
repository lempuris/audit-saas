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

## 5. Before go-live

- Rotate `CLERK_SECRET_KEY` (it was shared during development) and create a
  **production** Clerk instance.
- Update SSM parameters `/auditsaas/clerk_secret_key`, `/auditsaas/clerk_jwks_url`,
  `/auditsaas/clerk_webhook_secret`, and the repo variable
  `VITE_CLERK_PUBLISHABLE_KEY`; redeploy API + client.
