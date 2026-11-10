terraform {
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare", version = "= 5.24.0" }
  }
}
variable "zone_id" { type = string }
variable "hostname" { type = string }
variable "ipv4" { type = string }
variable "proxied" { type = bool }
variable "manage_zone_settings" { type = bool }
variable "manage_cache_rules" { type = bool }
resource "cloudflare_dns_record" "odoo" {
  zone_id = var.zone_id
  name    = var.hostname
  type    = "A"
  content = var.ipv4
  proxied = var.proxied
  ttl     = 1
}
# Zone settings are shared by every hostname. Only one root may own them.
resource "cloudflare_zone_setting" "tls" {
  for_each   = var.manage_zone_settings ? { ssl = "strict", min_tls_version = "1.2" } : {}
  zone_id    = var.zone_id
  setting_id = each.key
  value      = each.value
}
# Cloudflare permits one zone entrypoint per phase: designate exactly one environment
# as owner, including all Odoo hosts in that zone, or use an existing bypass ruleset.
variable "cache_hostnames" { type = list(string) }
resource "cloudflare_ruleset" "cache" {
  count   = var.manage_cache_rules ? 1 : 0
  zone_id = var.zone_id
  name    = "Odoo cache bypass"
  kind    = "zone"
  phase   = "http_request_cache_settings"
  rules = [{
    action            = "set_cache_settings"
    expression        = "http.host in {${join(" ", [for host in var.cache_hostnames : jsonencode(host)])}}"
    description       = "Never cache ERP responses"
    enabled           = true
    action_parameters = { cache = false }
  }]
}
