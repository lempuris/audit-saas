# Paused stack — restore procedure

The AuditSaaS stack was put on hold on **2026-09-01** to cut AWS spend while the
project is parked. Spend went from **~$62/month to ~$3/month**.

Terraform state was deliberately **not** modified: it still describes the full
running stack. The paused resources show up as drift, and `terraform apply`
recreates them. That is the intended restore path — do not `terraform destroy`,
and do not refresh state expecting a clean plan while paused.

## What was done

| Resource | Action | Saved/mo |
|---|---|---|
| ECS service `api` | desired count → 0 (see caveat below) | $8.96 Fargate + $3.65 IPv4 |
| ALB `auditsaas-api` + `:80` listener | **deleted** | $18.30 + $7.30 (2 × IPv4) |
| RDS `auditsaas-db` | snapshot → deletion protection off → **deleted** | $15.00 |
| Manual snapshot `auditsaas-db-pause-20260901` | **created and retained** | −$1.90 (new cost) |

### Caveat: the tfvars guard is local-only

`terraform.tfvars` is gitignored, so the `api_desired_count = 0` line added
during the pause exists **only on the machine the pause was run from** — it is
not in this repo and a fresh clone will not have it. The authoritative record of
the paused state is this file.

Practically that means: the real protection is *not running `terraform apply`
while paused*. A plan from a fresh clone will want to recreate the ALB and the
RDS instance and set the desired count back to 1 — which is the restore path,
not something to trigger by accident. If you need the guard on another machine,
re-add `api_desired_count = 0` to your local `terraform.tfvars`.

## What was deliberately kept

- **`auditsaas-db-pause-20260901`** — the only copy of the database. 20 GB,
  postgres 16.13, unencrypted. **Do not delete this.** Automated snapshots were
  removed with the instance; this manual one is not subject to the 7-day window.
- **Target group `auditsaas-api`** — free, and the ECS service definition still
  references it. Keeping it means the service stays valid at zero tasks.
- **ECS cluster, task definition, CloudWatch log group** — all free at rest.
- **S3** `auditsaas-ui`, `auditsaas-documents`, `auditsaas-tfstate` (~0.6 MB total).
- **ECR** `auditsaas-api`, 10 images (~1.7 GB, $0.17/mo) — kept for rollback.
- **CloudFront** `E3I9LJC6V4D73Q` — left enabled. Costs nothing at zero traffic,
  and keeping it preserves the `d2j...cloudfront.net` domain, so the Clerk
  allowed-origins and CORS configuration stay valid across the pause. The SPA
  still loads; `/api/*` calls fail until the ALB is back.
- **SSM parameters** — all four, including the Clerk secrets.

## Restoring

1. Remove the `api_desired_count = 0` block from `terraform.tfvars` if your
   local copy has it (it is gitignored — a fresh clone will not).

2. Point the DB at the snapshot for **one apply only** — add to
   `aws_db_instance.main` in `rds.tf`:

   ```hcl
   snapshot_identifier = "auditsaas-db-pause-20260901"
   ```

3. `terraform plan` and read it carefully. Expect the ALB, its listener, the
   RDS instance, and the ECS service desired count to come back, plus an
   in-place update to the CloudFront API origin and the `database_url` SSM
   parameter (both track the new ALB/RDS DNS names automatically).

4. `terraform apply`. RDS restore takes ~10–15 minutes.

5. Remove the `snapshot_identifier` line once the DB is up. Leaving it in is
   harmless for subsequent applies — Terraform ignores it on an existing
   instance — but it will silently re-restore from the snapshot if the instance
   is ever replaced, which would discard newer data.

6. Redeploy the API so the task definition points at a current image, or just
   merge to `master` and let CI do it.

### Why the database password still works

`ssm.tf` builds `database_url` from `random_password.db`, which lives in
Terraform **state**, not in the database. State was left untouched, so that
value is unchanged; a snapshot restore preserves the master password the
snapshot was taken with. The two still match. This is the reason the pause was
done via the CLI rather than `terraform destroy` — destroying would drop
`random_password.db` from state, regenerate it on the next apply, and leave the
SSM connection string pointing at a password the restored database never had.

### Verifying afterwards

```bash
export AWS_REGION=eu-west-1
aws ecs describe-services --cluster auditsaas --services api \
  --query 'services[0].{Desired:desiredCount,Running:runningCount}'
curl -sS https://d2j123m79f41ic.cloudfront.net/api/health
```

## Notes

- **Do not merge to `master` while paused.** CI forces an ECS deployment on
  merge; with the service at zero it will not start a task, but the deploy step
  may fail on the missing target health check. Nothing breaks, but the build
  goes red for no reason.
- Unrelated to this project, the account also carries a stray
  `church-db-snapshot` in `us-east-1` ($0.31/mo) and two CloudFront
  distributions from older work. Left alone.
