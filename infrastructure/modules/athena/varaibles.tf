variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
}

variable "glue_database_name" {
  description = "Name of the Glue database containing the market data tables"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}

variable "athena_results_bucket_name" {
  description = "Name of the S3 bucket for storing Athena query results"
  type        = string
}
