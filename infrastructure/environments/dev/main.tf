locals {
  environment = "dev"
  project     = "eve-market"
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name

  common_tags = {
    Environment = local.environment
    Project     = local.project
    AccountId   = local.account_id
    ManagedBy   = "terraform"
  }
}

# 1. Network Stack
module "network_stack" {
  source = "../../stacks/network"

  environment        = local.environment
  project_name       = local.project
  vpc_id             = data.aws_vpc.existing_vpc.id
  vpc_cidr           = data.aws_vpc.existing_vpc.cidr_block
  private_subnet_ids = data.aws_subnets.private.ids

  tags = local.common_tags
}

# 2. Storage Stack
module "storage_stack" {
  source = "../../stacks/storage"

  environment = local.environment
  account_id  = local.account_id
  project     = local.project

  tags = local.common_tags
}

# 3. Data Processing Stack
module "data_processing_stack" {
  source = "../../stacks/data_processing"

  environment = local.environment
  account_id  = local.account_id
  project     = local.project

  # Dependencies
  market_data_bucket_id    = module.storage_stack.market_data_bucket_id
  market_data_bucket_arn   = module.storage_stack.market_data_bucket_arn
  athena_results_bucket_id = module.storage_stack.athena_results_bucket_id

  tags = local.common_tags
}

# 4. Analytics Stack
module "analytics_stack" {
  source = "../../stacks/analytics"

  environment        = local.environment
  account_id         = local.account_id
  project            = local.project
  vpc_id             = data.aws_vpc.existing_vpc.id
  private_subnet_ids = data.aws_subnets.private.ids

  # Dependencies
  sagemaker_bucket_id      = module.storage_stack.sagemaker_bucket_id
  sagemaker_bucket_arn     = module.storage_stack.sagemaker_bucket_arn
  glue_database_name       = module.data_processing_stack.glue_database_name
  glue_role_name           = module.data_processing_stack.glue_role_name
  athena_results_bucket_id = module.storage_stack.athena_results_bucket_id

  tags = local.common_tags
}

# 5. Application Stack
module "application_stack" {
  source = "../../stacks/application"

  environment        = local.environment
  project_name       = local.project
  region             = local.region
  vpc_id             = data.aws_vpc.existing_vpc.id
  private_subnet_ids = data.aws_subnets.private.ids
  public_subnet_ids  = module.network_stack.public_subnet_ids

  tags = local.common_tags
}