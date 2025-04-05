variable "vpc_id" {
  description = "ID of the existing VPC to use"
  type        = string
  default     = "vpc-00e4420e6016e8123x" # Replace with your actual VPC ID
}

variable "environment" {
  description = "Environment name (dev, test, prod, etc.)"
  type        = string
  default     = "dev"
}


