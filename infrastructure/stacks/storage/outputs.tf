# Outputs
output "sagemaker_bucket_id" {
  description = "The ID of the SageMaker bucket"
  value       = length(data.aws_s3_bucket.existing_sagemaker_bucket) > 0 ? data.aws_s3_bucket.existing_sagemaker_bucket[0].id : (length(module.sagemaker_bucket) > 0 ? module.sagemaker_bucket[0].bucket_id : null)
}

output "sagemaker_bucket_arn" {
  description = "The ARN of the SageMaker bucket"
  value       = length(data.aws_s3_bucket.existing_sagemaker_bucket) > 0 ? data.aws_s3_bucket.existing_sagemaker_bucket[0].arn : (length(module.sagemaker_bucket) > 0 ? module.sagemaker_bucket[0].bucket_arn : null)
}

output "market_data_bucket_id" {
  description = "The ID of the market data bucket"
  value       = length(data.aws_s3_bucket.existing_market_data_bucket) > 0 ? data.aws_s3_bucket.existing_market_data_bucket[0].id : (length(module.market_data_bucket) > 0 ? module.market_data_bucket[0].bucket_id : null)
}

output "market_data_bucket_arn" {
  description = "The ARN of the market data bucket"
  value       = length(data.aws_s3_bucket.existing_market_data_bucket) > 0 ? data.aws_s3_bucket.existing_market_data_bucket[0].arn : (length(module.market_data_bucket) > 0 ? module.market_data_bucket[0].bucket_arn : null)
}

output "athena_results_bucket_id" {
  description = "The ID of the Athena results bucket"
  value       = length(data.aws_s3_bucket.existing_athena_results_bucket) > 0 ? data.aws_s3_bucket.existing_athena_results_bucket[0].id : (length(module.athena_results_bucket) > 0 ? module.athena_results_bucket[0].bucket_id : null)
}

output "athena_results_bucket_arn" {
  description = "The ARN of the Athena results bucket"
  value       = length(data.aws_s3_bucket.existing_athena_results_bucket) > 0 ? data.aws_s3_bucket.existing_athena_results_bucket[0].arn : (length(module.athena_results_bucket) > 0 ? module.athena_results_bucket[0].bucket_arn : null)
}