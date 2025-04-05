# Create S3 bucket for SageMaker
resource "aws_s3_bucket" "sagemaker_bucket" {
  bucket = "sagemaker-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "SageMaker Bucket"
    Environment = var.environment
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
