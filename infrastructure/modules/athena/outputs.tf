output "athena_workgroup_name" {
  description = "Name of the Athena workgroup for market data analysis"
  value       = aws_athena_workgroup.market_data_workgroup.name
}

output "athena_workgroup_id" {
  description = "ID of the Athena workgroup"
  value       = aws_athena_workgroup.market_data_workgroup.id
}

output "athena_results_location" {
  description = "S3 location for Athena query results"
  value       = "s3://${var.athena_results_bucket_name}/athena-results/"
}

output "athena_policy_arn" {
  description = "ARN of the Athena permissions policy"
  value       = aws_iam_policy.athena_permissions.arn
}
