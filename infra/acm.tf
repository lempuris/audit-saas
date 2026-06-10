# Certificates are only issued once domain_name is set; until then the ALB
# serves plain HTTP (reached only via CloudFront) and CloudFront uses its
# default *.cloudfront.net certificate.

# Regional certificate for the ALB (api.audit.<domain>).
resource "aws_acm_certificate" "api" {
  count = local.use_custom_domain ? 1 : 0

  domain_name       = local.api_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "api_cert_validation" {
  for_each = {
    for dvo in flatten(aws_acm_certificate.api[*].domain_validation_options) : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = aws_route53_zone.main[0].zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "api" {
  count = local.use_custom_domain ? 1 : 0

  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [for r in aws_route53_record.api_cert_validation : r.fqdn]
}

# us-east-1 certificate for CloudFront (audit.<domain>).
resource "aws_acm_certificate" "ui" {
  count    = local.use_custom_domain ? 1 : 0
  provider = aws.us_east_1

  domain_name       = local.ui_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "ui_cert_validation" {
  for_each = {
    for dvo in flatten(aws_acm_certificate.ui[*].domain_validation_options) : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = aws_route53_zone.main[0].zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "ui" {
  count    = local.use_custom_domain ? 1 : 0
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.ui[0].arn
  validation_record_fqdns = [for r in aws_route53_record.ui_cert_validation : r.fqdn]
}
