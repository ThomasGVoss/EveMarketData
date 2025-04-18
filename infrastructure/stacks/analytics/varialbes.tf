
variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "project" {
  description = "Project name"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of the private subnets"
  type        = list(string)
}

variable "sagemaker_bucket_id" {
  description = "ID of the SageMaker S3 bucket"
  type        = string
}

variable "sagemaker_bucket_arn" {
  description = "ARN of the SageMaker S3 bucket"
  type        = string
}

variable "glue_database_name" {
  description = "Name of the Glue database"
  type        = string
}

variable "glue_role_name" {
  description = "Name of the Glue IAM role"
  type        = string
}

variable "athena_results_bucket_id" {
  description = "ID of the Athena results bucket"
  type        = string
}

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}