terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.23.0" }
  }
}
variable "bucket" { type = string }
resource "aws_s3_bucket" "backup" {
  bucket        = var.bucket
  force_destroy = false
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_versioning" "backup" {
  bucket = aws_s3_bucket.backup.id
  versioning_configuration { status = "Enabled" }
}
output "bucket" { value = aws_s3_bucket.backup.id }
