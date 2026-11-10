provider "hcloud" {}
provider "cloudflare" {}
provider "aws" {
  region                      = var.s3_region
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  skip_region_validation      = true
  endpoints { s3 = var.s3_endpoint }
}
module "compute" {
  source         = "../../modules/compute/hetzner"
  name           = var.name
  environment    = var.environment
  region         = var.region
  server_type    = var.server_type
  image          = var.image
  ssh_public_key = var.ssh_public_key
  ssh_cidrs      = var.ssh_cidrs
  web_cidrs      = var.web_cidrs
}
module "dns" {
  source               = "../../modules/dns/cloudflare"
  zone_id              = var.cloudflare_zone_id
  hostname             = var.hostname
  ipv4                 = module.compute.host.ipv4
  proxied              = var.cloudflare_proxied
  manage_zone_settings = var.manage_zone_settings
  manage_cache_rules   = var.manage_cache_rules
  cache_hostnames      = var.cache_hostnames
}
module "backup" {
  source = "../../modules/object-storage/hetzner"
  bucket = var.backup_bucket
}
output "host" { value = module.compute.host }
output "backup_bucket" { value = module.backup.bucket }
