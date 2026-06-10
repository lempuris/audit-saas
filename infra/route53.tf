# Hosted zone for the apex domain. If the domain is registered via Route 53
# Domains, point the registration at this zone's name servers. If it is a
# .co.tz domain registered with a tzNIC registrar, set the registrar's NS
# records to this zone's name servers (see `zone_name_servers` output).
#
# All resources here are skipped while domain_name is empty (domain not yet
# registered); the stack serves from the default CloudFront/ALB hostnames.
resource "aws_route53_zone" "main" {
  count = local.use_custom_domain ? 1 : 0

  name = var.domain_name
}

resource "aws_route53_record" "ui" {
  count = local.use_custom_domain ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = local.ui_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.ui.domain_name
    zone_id                = aws_cloudfront_distribution.ui.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "ui_ipv6" {
  count = local.use_custom_domain ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = local.ui_domain
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.ui.domain_name
    zone_id                = aws_cloudfront_distribution.ui.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "api" {
  count = local.use_custom_domain ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = local.api_domain
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}
