variable "project" {
  description = "Name prefix for all resources"
  type        = string
  default     = "auditsaas"
}

variable "aws_region" {
  description = "Region for the ALB, ECS, and RDS (af-south-1 is closer to Tanzania but is opt-in and not enabled on this account)"
  type        = string
  default     = "eu-west-1"
}

variable "domain_name" {
  description = <<-EOT
    Apex domain, e.g. retrofitbusinesspact.com (registered via Route 53 Domains)
    or retrofitbusinesspact.co.tz (registered with a tzNIC registrar, NS records
    delegated to the hosted zone this stack creates).

    Leave empty ("") while the domain is still being registered: the stack then
    skips the hosted zone, DNS records, ACM certificates, CloudFront aliases,
    the ALB HTTPS listener, and the SES domain identity. The SPA is served from
    the default CloudFront domain, which proxies /api/* to the ALB so the app
    works over HTTPS without a domain. Set the domain later and re-apply.
  EOT
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repo allowed to deploy via OIDC, in owner/name form"
  type        = string
  default     = "lempuris/audit-saas"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS storage in GB (gp3)"
  type        = number
  default     = 20
}

variable "db_name" {
  type    = string
  default = "auditsaas"
}

variable "db_username" {
  type    = string
  default = "audit"
}

variable "api_cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "Fargate task memory in MiB"
  type        = number
  default     = 512
}

variable "api_desired_count" {
  type    = number
  default = 1
}

variable "container_port" {
  type    = number
  default = 5000
}

locals {
  use_custom_domain = var.domain_name != ""

  ui_domain  = "audit.${var.domain_name}"
  api_domain = "api.audit.${var.domain_name}"
}
