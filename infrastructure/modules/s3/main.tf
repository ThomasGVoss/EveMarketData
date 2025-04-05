resource "aws_s3_bucket" "market_data_bucket" {
  bucket = var.bucket_name

  tags = var.tags
}

resource "aws_s3_bucket_lifecycle_configuration" "market_data_lifecycle" {
  bucket = aws_s3_bucket.market_data_bucket.id

  rule {
    id     = "market-data-lifecycle"
    status = "Enabled"

    transition {
      days          = var.standard_ia_transition_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER"
    }

    expiration {
      days = var.expiration_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "market_data_encryption" {
  bucket = aws_s3_bucket.market_data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "market_data_versioning" {
  bucket = aws_s3_bucket.market_data_bucket.id
  
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_public_access_block" "market_data_public_access_block" {
  bucket = aws_s3_bucket.market_data_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
} 