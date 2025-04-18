data "aws_vpc" "existing_vpc" {
  id = "vpc-00e4420e6016e8123"
}

data "aws_region" "current" {}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Fetch public subnets from the VPC
data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing_vpc.id]
  }

  # Adjust this filter to match how your public subnets are tagged
  # Common tags might be "Type" = "Public" or "Name" contains "public"
  filter {
    name   = "tag:Name"
    values = ["*public*", "*Public*"] # This will match any subnet with "public" in the name
  }
}

# Fetch all private subnets from the VPC
data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing_vpc.id]
  }
}

# Get information about all subnets in your VPC
data "aws_subnets" "all_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing_vpc.id]
  }
}

# Then for each subnet, get detailed info
data "aws_subnet" "subnet_details" {
  for_each = toset(data.aws_subnets.all_subnets.ids)
  id       = each.value
}

