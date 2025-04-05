variable "domain_name" {
  description = "Name of the SageMaker domain"
  type        = string
}

variable "auth_mode" {
  description = "Authentication mode for the domain"
  type        = string
  default     = "IAM"
  validation {
    condition     = contains(["IAM", "SSO"], var.auth_mode)
    error_message = "Authentication mode must be either IAM or SSO"
  }
}

variable "vpc_id" {
  description = "ID of the VPC where SageMaker will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "IDs of the subnets where SageMaker will be deployed"
  type        = list(string)
}

variable "kms_key_id" {
  description = "The KMS key ID to encrypt domain storage. If not specified, the default KMS key is used"
  type        = string
  default     = null
}

variable "app_network_access_type" {
  description = "Network access type for SageMaker applications"
  type        = string
  default     = "VpcOnly"
  validation {
    condition     = contains(["VpcOnly"], var.app_network_access_type)
    error_message = "App network access type must be either PublicInternetOnly or VpcOnly"
  }
}

variable "additional_security_group_ids" {
  description = "Additional security group IDs to attach to SageMaker domain"
  type        = list(string)
  default     = []
}

variable "s3_output_path" {
  description = "S3 path for SageMaker notebooks output"
  type        = string
  default     = null
}

variable "s3_kms_key_id" {
  description = "KMS key ID for S3 encryption"
  type        = string
  default     = null
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket for SageMaker to use"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# User profile related variables
variable "create_default_user_profile" {
  description = "Whether to create a default user profile"
  type        = bool
  default     = true
}

variable "default_user_profile_name" {
  description = "Name for the default user profile"
  type        = string
  default     = "default-user"
}

variable "jupyter_instance_type" {
  description = "Instance type for JupyterServer applications"
  type        = string
  default     = "ml.t3.medium"
}

variable "kernel_gateway_instance_type" {
  description = "Instance type for KernelGateway applications"
  type        = string
  default     = "ml.t3.medium"
} 

variable "account_id" {
  description = "AWS account ID"
  type        = string
}
