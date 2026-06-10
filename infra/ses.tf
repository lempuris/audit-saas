# SES needs the domain for identity verification, so all of this waits until
# domain_name is set. No email goes out in the interim (nothing in Phase 0
# sends any).
resource "aws_ses_domain_identity" "main" {
  count = local.use_custom_domain ? 1 : 0

  domain = var.domain_name
}

resource "aws_route53_record" "ses_verification" {
  count = local.use_custom_domain ? 1 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = "_amazonses.${var.domain_name}"
  type    = "TXT"
  ttl     = 600
  records = [aws_ses_domain_identity.main[0].verification_token]
}

resource "aws_ses_domain_dkim" "main" {
  count = local.use_custom_domain ? 1 : 0

  domain = aws_ses_domain_identity.main[0].domain
}

resource "aws_route53_record" "ses_dkim" {
  count = local.use_custom_domain ? 3 : 0

  zone_id = aws_route53_zone.main[0].zone_id
  name    = "${aws_ses_domain_dkim.main[0].dkim_tokens[count.index]}._domainkey.${var.domain_name}"
  type    = "CNAME"
  ttl     = 600
  records = ["${aws_ses_domain_dkim.main[0].dkim_tokens[count.index]}.dkim.amazonses.com"]
}
