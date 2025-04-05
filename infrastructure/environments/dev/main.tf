# Create S3 bucket for SageMaker
resource "aws_s3_bucket" "sagemaker_bucket" {
  bucket = "sagemaker-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "SageMaker Bucket"
    Environment = var.environment
  }
}

# Create S3 bucket for market data
module "market_data_bucket" {
  source = "../../modules/s3"

  bucket_name = "market-data-${var.environment}-${data.aws_caller_identity.current.account_id}"
  
  # Optional configurations
  standard_ia_transition_days = 30
  glacier_transition_days     = 90
  expiration_days             = 365
  enable_versioning           = false
  
  tags = {
    Name        = "Market Data Bucket"
    Environment = var.environment
    Project     = "EveMarketData"
  }
}

# Lambda for market prices data ingestion
module "market_prices_lambda" {
  source = "../../modules/lambda"

  function_name       = "market-data-prices-ingestion"
  handler             = "market_price_ingestion.lambda_handler"
  source_dir          = "src/market_prices"  # Create this directory
  environment         = var.environment
  s3_bucket_name      = module.market_data_bucket.bucket_id
  schedule_expression = "rate(12 hours)"
  
  tags = {
    Environment = var.environment
    Project     = "EveMarketData"
    AccountId   = data.aws_caller_identity.current.account_id
  }
}

# Lambda for market orders data ingestion
module "market_orders_lambda" {
  source = "../../modules/lambda"

  function_name       = "market-data-orders-ingestion"
  handler             = "market_order_ingestion.lambda_handler"
  source_dir          = "src/market_orders"  # Create this directory
  environment         = var.environment
  s3_bucket_name      = module.market_data_bucket.bucket_id
  schedule_expression = "rate(12 hours)"
  
  additional_environment_variables = {
    REGIONS     = "10000002,10000032,10000043,10000030"
    TYPE_IDS    = "17357,230,222,9957"
  }
  
  tags = {
    Environment = var.environment
    Project     = "EveMarketData"
    AccountId   = data.aws_caller_identity.current.account_id
  }
}

# Reference the SageMaker module
module "sagemaker_domain" {
  source = "../../modules/sagemaker"

  account_id = data.aws_caller_identity.current.account_id

  domain_name = "sagemaker-domain-${var.environment}"
  auth_mode   = "IAM"

  # VPC configuration
  vpc_id     = data.aws_vpc.existing_vpc.id
  subnet_ids = data.aws_subnets.private.ids

  # Network access type - using VPC only for better security
  app_network_access_type = "VpcOnly"

  # S3 configuration
  s3_bucket_arn  = aws_s3_bucket.sagemaker_bucket.arn
  s3_output_path = "s3://${aws_s3_bucket.sagemaker_bucket.bucket}/outputs"

  # User profile configuration
  create_default_user_profile  = true
  default_user_profile_name    = "dev-user"
  jupyter_instance_type        = "ml.t3.medium"
  kernel_gateway_instance_type = "ml.t3.medium"

  # Additional security groups - can connect to the EC2 instance
  additional_security_group_ids = []

  # Tags
  tags = {
    Environment = var.environment
    Project     = "SageMaker"
    AccountId   = data.aws_caller_identity.current.account_id
  }
}

# Glue Resources for Market Data Analytics
module "market_data_glue" {
  source = "../../modules/glue"

  environment    = var.environment
  s3_bucket_name = module.market_data_bucket.bucket_id
  crawler_schedule = "cron(0 0/23 * * ? *)"  # Läuft alle 12 Stunden (um 0:00, 12:00 Uhr)
  
  tags = {
    Environment = var.environment
    Project     = "EveMarketData"
    AccountId   = data.aws_caller_identity.current.account_id
  }
}
