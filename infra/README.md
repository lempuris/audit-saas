# AuditSaaS infrastructure

Single Terraform stack: VPC, ECR, ECS Fargate (1 task) + ALB, RDS PostgreSQL
(`db.t4g.micro`, private subnets), S3 (UI + documents) + CloudFront with OAC,
ACM certificates, Route 53 hosted zone + records, SSM parameters, SES identity,
and a GitHub Actions OIDC deploy role.

## Bootstrap (one-time)

> **No domain yet?** The stack can be applied with `domain_name = ""`: it
> skips the hosted zone, DNS records, ACM certificates, CloudFront aliases,
> the ALB HTTPS listener, and SES. The SPA is served from the default
> CloudFront domain, which also proxies `/api/*` to the ALB so everything
> works over HTTPS. When the domain is registered, do step 1, set
> `domain_name` in `terraform.tfvars`, and re-apply — the temporary `/api/*`
> proxy is replaced by `api.audit.<domain>` automatically. Then update the
> `VITE_API_URL` GitHub variable and redeploy the client.

1. **Register the domain.** Either:
   - `.com` via Route 53 Domains (~$15/yr):
     `aws route53domains register-domain --cli-input-json file://domain.json --region us-east-1`
   - `.co.tz`: register with a tzNIC-accredited registrar, then after step 3
     set the registrar's NS records to the `zone_name_servers` output.
2. `cp terraform.tfvars.example terraform.tfvars` and fill in `domain_name`.
3. `terraform init && terraform apply`.
   - The ACM certificates wait on DNS validation; if the domain was registered
     outside Route 53, the apply will hang at certificate validation until you
     delegate NS records to the new hosted zone (step 1b). Verify with
     `dig NS <domain>`.
   - If the domain *was* registered via Route 53 Domains, registration
     auto-created a hosted zone. Either import it
     (`terraform import aws_route53_zone.main <ZONE_ID>`) or delete it and let
     this stack create its own — then update the registered domain's name
     servers to match (`aws route53domains update-domain-nameservers`).
4. Set real secret values (Terraform creates the parameters with placeholders
   and ignores later value changes):
   ```
   aws ssm put-parameter --name /auditsaas/clerk_secret_key --type SecureString --overwrite --value sk_...
   aws ssm put-parameter --name /auditsaas/clerk_jwks_url   --type SecureString --overwrite --value https://...
   ```
5. Push an image so the ECS service has something to run: a push to `master`
   touching `audit-api/**` does this via CI, or do it once by hand
   (`docker build`, `docker push <ecr_repository_url>:latest`, then
   `aws ecs update-service --force-new-deployment`).
6. Configure GitHub repository **variables** from the Terraform outputs:
   `AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`, `UI_BUCKET`,
   `CLOUDFRONT_DISTRIBUTION_ID`, and `VITE_API_URL` /
   `VITE_CLERK_PUBLISHABLE_KEY` for the client build.

## State

Phase 0 uses local state (`terraform.tfstate`, gitignored). Before anyone else
runs `apply`, migrate to an S3 backend: create a small state bucket, add a
`backend "s3"` block to `versions.tf`, and run `terraform init -migrate-state`.

## Costs (approximate)

Fargate ~$9, ALB ~$17, RDS t4g.micro ~$14, S3/CloudFront/ECR/Route 53 ~$5
≈ **$45/month**, plus $15/yr domain registration. No NAT gateway: the API task
runs in public subnets (security group only admits the ALB) specifically to
avoid the ~$32/mo NAT cost.
