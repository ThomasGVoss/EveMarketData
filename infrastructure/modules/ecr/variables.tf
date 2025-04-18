variable "repository_name" {
  description = "Name for the ECR repository"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}