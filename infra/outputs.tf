output "zone_name_servers" {
  description = "Set these as the domain's NS records at the registrar (null until domain_name is set)"
  value       = local.use_custom_domain ? aws_route53_zone.main[0].name_servers : null
}

output "ui_url" {
  value = local.use_custom_domain ? "https://${local.ui_domain}" : "https://${aws_cloudfront_distribution.ui.domain_name}"
}

output "api_url" {
  description = "Base URL for the API (GitHub Actions variable VITE_API_URL); proxied through CloudFront until a domain exists"
  value       = local.use_custom_domain ? "https://${local.api_domain}" : "https://${aws_cloudfront_distribution.ui.domain_name}"
}

output "alb_dns_name" {
  description = "Direct ALB endpoint (plain HTTP while no domain/certificate exists)"
  value       = aws_lb.api.dns_name
}

output "cloudfront_distribution_id" {
  description = "GitHub Actions variable CLOUDFRONT_DISTRIBUTION_ID"
  value       = aws_cloudfront_distribution.ui.id
}

output "ui_bucket" {
  description = "GitHub Actions variable UI_BUCKET"
  value       = aws_s3_bucket.ui.bucket
}

output "documents_bucket" {
  value = aws_s3_bucket.documents.bucket
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "ecs_cluster" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service" {
  value = aws_ecs_service.api.name
}

output "github_deploy_role_arn" {
  description = "GitHub Actions variable AWS_DEPLOY_ROLE_ARN"
  value       = aws_iam_role.github_deploy.arn
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}
