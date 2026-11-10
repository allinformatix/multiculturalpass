terraform {
  required_version = ">= 1.13.5, < 2.0.0"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "= 1.70.1"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "= 5.24.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.23.0"
    }
  }
}

terraform {
  backend "remote" {}
}
