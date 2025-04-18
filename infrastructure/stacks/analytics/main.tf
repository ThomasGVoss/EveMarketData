
# Reference the SageMaker module
module "sagemaker_domain" {
  source = "../../modules/sagemaker"

  account_id = var.account_id

  domain_name = "sagemaker-domain-${var.environment}"
  auth_mode   = "IAM"

  # VPC configuration
  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # Network access type - using VPC only for better security
  app_network_access_type = "VpcOnly"

  # S3 configuration
  s3_bucket_arn  = var.sagemaker_bucket_arn
  s3_output_path = "s3://${var.sagemaker_bucket_id}/outputs"

  # User profile configuration
  create_default_user_profile  = true
  default_user_profile_name    = "dev-user"
  jupyter_instance_type        = "ml.t3.medium"
  kernel_gateway_instance_type = "ml.t3.medium"

  # Additional security groups - can connect to the EC2 instance
  additional_security_group_ids = []

  # Tags
  tags = var.tags
}

# Athena Resources for Market Data Analytics
module "market_data_athena" {
  source = "../../modules/athena"

  environment                = var.environment
  glue_database_name         = var.glue_database_name
  athena_results_bucket_name = var.athena_results_bucket_id

  tags = var.tags
}

# Attach Athena permissions to the existing role if needed
resource "aws_iam_role_policy_attachment" "athena_permissions" {
  role       = var.glue_role_name
  policy_arn = module.market_data_athena.athena_policy_arn
}
