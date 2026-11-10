terraform {
  required_providers {
    hcloud = { source = "hetznercloud/hcloud", version = "= 1.70.1" }
  }
}
variable "name" { type = string }
variable "environment" { type = string }
variable "region" { type = string }
variable "server_type" { type = string }
variable "image" { type = string }
variable "ssh_public_key" { type = string }
variable "ssh_cidrs" { type = list(string) }
variable "web_cidrs" { type = list(string) }
resource "hcloud_ssh_key" "deployment" {
  name       = var.name
  public_key = var.ssh_public_key
}
resource "hcloud_firewall" "origin" {
  name   = var.name
  labels = { environment = var.environment, managed_by = "terraform" }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = var.ssh_cidrs
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = var.web_cidrs
  }
  rule {
    direction  = "in"
    protocol   = "icmp"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}
resource "hcloud_server" "odoo" {
  name               = var.name
  server_type        = var.server_type
  image              = var.image
  location           = var.region
  ssh_keys           = [hcloud_ssh_key.deployment.id]
  firewall_ids       = [hcloud_firewall.origin.id]
  backups            = true
  delete_protection  = var.environment == "prd"
  rebuild_protection = var.environment == "prd"
  labels             = { environment = var.environment, managed_by = "terraform", project = var.name }
  public_net {
    ipv4_enabled = true
    ipv6_enabled = false
  }
  lifecycle {
    ignore_changes = [ssh_keys]
  }
}
output "host" {
  value = { id = hcloud_server.odoo.id, ipv4 = hcloud_server.odoo.ipv4_address, name = var.name, environment = var.environment }
}
