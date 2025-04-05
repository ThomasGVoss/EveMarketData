variable "ami_id" {
  description = "The AMI ID to use for the instance"
  type        = string
  default     = "ami-0669b163befffbdfc" # Amazon Linux 2 in eu-central-1
}

variable "vpc_id" {
  description = "The VPC ID to launch the instance in"
  type        = string
}

variable "instance_type" {
  description = "The instance type to use"
  type        = string
  default     = "t2.micro"
}

variable "subnet_id" {
  description = "The subnet ID to launch the instance in"
  type        = string
}

variable "security_group_ids" {
  description = "List of security group IDs to associate with the instance"
  type        = list(string)
  default     = []
}

variable "name" {
  description = "Name of the instance"
  type        = string
  default     = "EC2Instance"
} 