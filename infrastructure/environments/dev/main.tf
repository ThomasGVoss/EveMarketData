# Create S3 bucket for SageMaker
module "sagemaker_bucket" {
  source = "../../modules/s3"

  bucket_name    = "sagemaker-${var.environment}-${data.aws_caller_identity.current.account_id}"
  bucket_purpose = "sagemaker"
  
  # SageMaker-specific configurations
  enable_lifecycle          = true
  standard_ia_transition_days = 31  # Keep data in standard longer for active use
  glacier_transition_days     = 90 # Move to Glacier later
  expiration_days             = 365 # Longer retention for ML data
  enable_versioning           = false # Version control for ML artifacts
    
  tags = {
    Environment = var.environment
    Project     = "SageMaker"
    Purpose     = "Machine Learning Environment"
  }
}

# Create S3 bucket for market data
module "market_data_bucket" {
  source = "../../modules/s3"

  bucket_name    = "market-data-${var.environment}-${data.aws_caller_identity.current.account_id}"
  bucket_purpose = "market-data"
  
  # Optional configurations
  enable_lifecycle          = true
  standard_ia_transition_days = 31
  glacier_transition_days     = 90
  expiration_days             = 365
  enable_versioning           = false
    
  tags = {
    Environment = var.environment
    Project     = "EveMarketData"
    Purpose     = "Market Data Storage"
  }
}

# Lambda for market prices data ingestion
module "market_prices_lambda" {
  source = "../../modules/lambda"

  function_name       = "market-data-prices-ingestion"
  handler             = "market_price_ingestion.lambda_handler"
  source_dir          = "src/market_prices" 
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
  source_dir          = "src/market_orders" 
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
  s3_bucket_arn  = module.sagemaker_bucket.bucket_arn
  s3_output_path = "s3://${module.sagemaker_bucket.bucket_id}/outputs"

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

# Athena Resources for Market Data Analytics
module "market_data_athena" {
  source = "../../modules/athena"

  environment        = var.environment
  glue_database_name = module.market_data_glue.glue_database_name
  athena_results_bucket_name = module.athena_results_bucket.bucket_id

  tags = {
    Environment = var.environment
    Project     = "EveMarketData"
    AccountId   = data.aws_caller_identity.current.account_id
  }
}

# Attach Athena permissions to the existing role if needed
resource "aws_iam_role_policy_attachment" "athena_permissions" {
  role       = module.market_data_glue.glue_role_name # You might need to add this as an output in your glue module
  policy_arn = module.market_data_athena.athena_policy_arn
}

# Athena results bucket
module "athena_results_bucket" {
  source = "../../modules/s3"

  bucket_name    = "athena-results-${var.environment}-${data.aws_caller_identity.current.account_id}"
  bucket_purpose = "athena-results"
  
  # Different lifecycle settings for query results
  enable_lifecycle          = true
  standard_ia_transition_days = 31  # Move to IA sooner
  glacier_transition_days     = 90 # Move to Glacier sooner
  expiration_days             = 365 # Shorter retention
  enable_versioning           = false
  
  tags = {
    Environment = var.environment
    Project     = "EveMarketData"
    Purpose     = "Athena Query Results"
  }
}
