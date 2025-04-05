variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}

variable "standard_ia_transition_days" {
  description = "Number of days before transitioning objects to STANDARD_IA storage class"
  type        = number
  default     = 30
}

variable "glacier_transition_days" {
  description = "Number of days before transitioning objects to GLACIER storage class"
  type        = number
  default     = 90
}

variable "expiration_days" {
  description = "Number of days before objects expire"
  type        = number
  default     = 365
}

variable "enable_versioning" {
  description = "Whether to enable versioning for the S3 bucket"
  type        = bool
  default     = false
} 