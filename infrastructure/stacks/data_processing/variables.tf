
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

variable "market_data_bucket_id" {
  description = "ID of the market data S3 bucket"
  type        = string
}

variable "market_data_bucket_arn" {
  description = "ARN of the market data S3 bucket"
  type        = string
}

variable "athena_results_bucket_id" {
  description = "ID of the Athena results S3 bucket"
  type        = string
}

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}