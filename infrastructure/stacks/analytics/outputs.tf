
# Outputs
output "sagemaker_domain_id" {
  value = module.sagemaker_domain.domain_id
}

output "sagemaker_execution_role_arn" {
  value = module.sagemaker_domain.execution_role_arn 
  description = "Role of the execution role for the SageMaker domain"
}

output "sagemaker_bucket_name" {
  value = replace(var.sagemaker_bucket_arn, "arn:aws:s3:::", "")
  description = "name of the S3 bucket for the SageMaker domain"
  
}

output "athena_policy_arn" {
  value = module.market_data_athena.athena_policy_arn
}