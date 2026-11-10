variable "name" {
  type = string
}
variable "environment" {
  type = string
  validation {
    condition     = var.environment == "dev"
    error_message = "This root is exclusively for dev."
  }
}
variable "hostname" {
  type = string
}
variable "cloudflare_zone_id" {
  type = string
}
variable "ssh_public_key" {
  type = string
}
variable "ssh_cidrs" {
  type = list(string)
}
variable "web_cidrs" {
  type = list(string)
}
variable "server_type" {
  type = string
}
variable "region" {
  type = string
}
variable "image" {
  type = string
}
variable "backup_bucket" {
  type = string
}
variable "cloudflare_proxied" {
  type = bool
}
variable "manage_zone_settings" {
  type = bool
}
variable "manage_cache_rules" {
  type = bool
}
variable "s3_endpoint" { type = string }
variable "s3_region" { type = string }
variable "cache_hostnames" { type = list(string) }
