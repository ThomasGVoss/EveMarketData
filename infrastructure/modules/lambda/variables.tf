variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
}

variable "function_name" {
  description = "Name of the Lambda function (without environment suffix)"
  type        = string
  default     = "market-data-ingestion"
}

variable "handler" {
  description = "Handler function (format: file.function)"
  type        = string
  default     = "market_data_ingestion.lambda_handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.11"
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 128
}

variable "source_dir" {
  description = "Directory containing Lambda source code"
  type        = string
  default     = "src"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket where market data will be stored"
  type        = string
}

variable "additional_environment_variables" {
  description = "Additional environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}

variable "schedule_expression" {
  description = "CloudWatch Events schedule expression for when to trigger the Lambda function"
  type        = string
  default     = "rate(1 hour)"
}

variable "create_schedule" {
  description = "Whether to create a CloudWatch Events schedule for the Lambda function"
  type        = bool
  default     = true
} 