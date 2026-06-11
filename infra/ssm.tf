# Secrets injected into the ECS task. DATABASE_URL is fully managed here; the
# Clerk parameters are created as placeholders and set manually in the console
# or CLI (Terraform then leaves the values alone).

resource "aws_ssm_parameter" "database_url" {
  name  = "/${var.project}/database_url"
  type  = "SecureString"
  value = "postgresql+asyncpg://${var.db_username}:${random_password.db.result}@${aws_db_instance.main.address}:5432/${var.db_name}"
}

resource "aws_ssm_parameter" "clerk_secret_key" {
  name  = "/${var.project}/clerk_secret_key"
  type  = "SecureString"
  value = "CHANGE_ME"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "clerk_jwks_url" {
  name  = "/${var.project}/clerk_jwks_url"
  type  = "SecureString"
  value = "CHANGE_ME"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "clerk_webhook_secret" {
  name  = "/${var.project}/clerk_webhook_secret"
  type  = "SecureString"
  value = "CHANGE_ME"

  lifecycle {
    ignore_changes = [value]
  }
}
