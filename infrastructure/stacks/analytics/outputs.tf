
# Outputs
output "sagemaker_domain_id" {
  value = module.sagemaker_domain.domain_id
}

output "athena_policy_arn" {
  value = module.market_data_athena.athena_policy_arn
}