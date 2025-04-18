
# Bucket-Namen definieren
locals {
  sagemaker_bucket_name      = "sagemaker-${var.environment}-${var.account_id}"
  market_data_bucket_name    = "market-data-${var.environment}-${var.account_id}"
  athena_results_bucket_name = "athena-results-${var.environment}-${var.account_id}"
}


data "aws_s3_bucket" "existing_sagemaker_bucket" {
  bucket = local.sagemaker_bucket_name

  count = try(
    length(local.sagemaker_bucket_name) > 0 ? 1 : 0,
    0
  )
}

data "aws_s3_bucket" "existing_market_data_bucket" {
  bucket = local.market_data_bucket_name
  count = try(
    length(local.market_data_bucket_name) > 0 ? 1 : 0,
    0
  )
}

data "aws_s3_bucket" "existing_athena_results_bucket" {
  bucket = local.athena_results_bucket_name
  count = try(
    length(local.athena_results_bucket_name) > 0 ? 1 : 0,
    0
  )
}

# Create S3 bucket for SageMaker
module "sagemaker_bucket" {
  source = "../../modules/s3"
  count  = length(data.aws_s3_bucket.existing_sagemaker_bucket) == 0 ? 1 : 0

  bucket_name    = "sagemaker-${var.environment}-${var.account_id}"
  bucket_purpose = "sagemaker"

  # SageMaker-specific configurations
  enable_lifecycle            = true
  standard_ia_transition_days = 7     # Keep data in standard longer for active use
  glacier_transition_days     = 30    # Move to Glacier later
  expiration_days             = 90    # Longer retention for ML data
  enable_versioning           = false # Version control for ML artifacts

  tags = merge(var.tags, {
    Purpose = "Machine Learning Environment"
  })
}

# Create S3 bucket for market data
module "market_data_bucket" {
  source = "../../modules/s3"
  count  = length(data.aws_s3_bucket.existing_market_data_bucket) == 0 ? 1 : 0

  bucket_name    = "market-data-${var.environment}-${var.account_id}"
  bucket_purpose = "market-data"

  # Optional configurations
  enable_lifecycle            = true
  standard_ia_transition_days = 7
  glacier_transition_days     = 30
  expiration_days             = 90
  enable_versioning           = false

  tags = merge(var.tags, {
    Purpose = "Market Data Storage"
  })
}

# Athena results bucket
module "athena_results_bucket" {
  source = "../../modules/s3"
  count  = length(data.aws_s3_bucket.existing_athena_results_bucket) == 0 ? 1 : 0

  bucket_name    = "athena-results-${var.environment}-${var.account_id}"
  bucket_purpose = "athena-results"

  # Different lifecycle settings for query results
  enable_lifecycle            = true
  standard_ia_transition_days = 7  # Move to IA sooner
  glacier_transition_days     = 30 # Move to Glacier sooner
  expiration_days             = 90 # Shorter retention
  enable_versioning           = false

  tags = merge(var.tags, {
    Purpose = "Athena Query Results"
  })
}

