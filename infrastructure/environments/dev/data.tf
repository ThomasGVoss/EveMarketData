data "aws_vpc" "existing_vpc" {
  id = "vpc-00e4420e6016e8123"
}

# Fetch all private subnets from the VPC
data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing_vpc.id]
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

