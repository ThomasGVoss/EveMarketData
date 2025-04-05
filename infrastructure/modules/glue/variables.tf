variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket where market data is stored"
  type        = string
}

variable "crawler_schedule" {
  description = "Cron expression for the Glue Crawler schedule"
  type        = string
  default     = "cron(0 */12 * * ? *)"  # Läuft alle 12 Stunden
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}
