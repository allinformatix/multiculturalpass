mock_provider "hcloud" {
  mock_resource "hcloud_server" {
    defaults = {
      ipv4_address = "192.0.2.20"
    }
  }
}
mock_provider "cloudflare" {}
mock_provider "aws" {}
variables {
  name                 = "test-odoo-dev"
  environment          = "dev"
  hostname             = "odoo.dev.example.com"
  cloudflare_zone_id   = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  ssh_public_key       = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest"
  ssh_cidrs            = ["192.0.2.1/32"]
  web_cidrs            = ["173.245.48.0/20"]
  server_type          = "cpx12"
  region               = "fsn1"
  image                = "ubuntu-24.04"
  backup_bucket        = "test-odoo-dev-backups"
  cloudflare_proxied   = true
  manage_zone_settings = false
  manage_cache_rules   = false
  cache_hostnames      = []
  s3_endpoint          = "https://fsn1.your-objectstorage.com"
  s3_region            = "fsn1"
}
run "adapter_contract" {
  command = plan
  assert {
    condition     = output.host.environment == "dev" && output.host.name == "test-odoo-dev"
    error_message = "Compute output must preserve environment identity."
  }

}
run "environment_mismatch" {
  command = plan
  variables {
    environment = "prd"
  }
  expect_failures = [var.environment]
}
