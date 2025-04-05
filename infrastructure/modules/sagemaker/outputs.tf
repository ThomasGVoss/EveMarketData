output "domain_id" {
  description = "The ID of the SageMaker Domain"
  value       = aws_sagemaker_domain.domain.id
}

output "domain_arn" {
  description = "The ARN of the SageMaker Domain"
  value       = aws_sagemaker_domain.domain.arn
}

output "domain_url" {
  description = "The URL of the SageMaker Domain"
  value       = aws_sagemaker_domain.domain.url
}

output "security_group_id" {
  description = "The ID of the security group created for SageMaker"
  value       = aws_security_group.sagemaker_sg.id
}

output "execution_role_arn" {
  description = "The ARN of the IAM role created for SageMaker execution"
  value       = aws_iam_role.sagemaker_execution_role.arn
}

output "execution_role_name" {
  description = "The name of the IAM role created for SageMaker execution"
  value       = aws_iam_role.sagemaker_execution_role.name
} 