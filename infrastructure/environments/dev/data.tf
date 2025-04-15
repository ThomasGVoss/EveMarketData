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
    values = ["*public*", "*Public*"]  # This will match any subnet with "public" in the name
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Make sure we have subnets data for debugging
output "debug_public_subnet_ids" {
  value = data.aws_subnets.public.ids
}

# Get information about all subnets in your VPC
data "aws_subnets" "all_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing_vpc.id]
  }
}

output "all_subnet_ids" {
  value = data.aws_subnets.all_subnets.ids
}

# Then for each subnet, get detailed info
data "aws_subnet" "subnet_details" {
  for_each = toset(data.aws_subnets.all_subnets.ids)
  id       = each.value
}

output "subnet_details" {
  value = {
    for id, subnet in data.aws_subnet.subnet_details : id => {
      cidr_block = subnet.cidr_block
      az         = subnet.availability_zone
      tags       = subnet.tags
    }
  }
}

