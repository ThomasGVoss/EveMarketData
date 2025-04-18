
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

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}