variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "vpc_id" {
  description = "ID of the existing VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR of the existing VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of existing private subnets"
  type        = list(string)
}

variable "tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
  default     = {}
}