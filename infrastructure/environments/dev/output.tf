# Output the VPC and subnet information for reference
output "vpc_id" {
  description = "ID of the VPC being used"
  value       = data.aws_vpc.existing_vpc.id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets in the VPC"
  value       = data.aws_subnets.private.ids
  sensitive   = true
}

output "cidr_block" {
  description = "CIDR block of the VPC"
  value       = data.aws_vpc.existing_vpc.cidr_block
  sensitive   = true
}

output "account_id" {
  description = "Current AWS account ID"
  value       = data.aws_caller_identity.current.account_id
  sensitive   = true
}


output "sagemaker_domain_id" {
  description = "ID of the SageMaker domain"
  value       = module.sagemaker_domain.domain_id
}

output "sagemaker_domain_url" {
  description = "URL of the SageMaker domain"
  value       = module.sagemaker_domain.domain_url
}

output "sagemaker_execution_role_arn" {
  description = "ARN of the SageMaker execution role"
  value       = module.sagemaker_domain.execution_role_arn
}

output "sagemaker_bucket" {
  description = "Name of the S3 bucket created for SageMaker"
  value       = module.sagemaker_bucket.bucket_id
} 

output "sagemaker_bucket_arn" {
  description = "ARN of the S3 bucket created for SageMaker"
  value       = module.sagemaker_bucket.bucket_arn
}

# Streamlit outputs
output "streamlit_ecr_repository_url" {
  description = "The URL of the ECR repository for the Streamlit app"
  value       = module.streamlit_ecr.repository_url
}

output "streamlit_alb_dns_name" {
  description = "The DNS name of the ALB for the Streamlit app"
  value       = module.streamlit_alb.alb_dns_name
}

output "streamlit_ecs_cluster_name" {
  description = "The name of the ECS cluster for the Streamlit app"
  value       = module.streamlit_ecs.cluster_id
}