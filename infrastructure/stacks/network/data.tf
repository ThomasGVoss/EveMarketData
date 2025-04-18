# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_internet_gateway" "existing" {
  filter {
    name   = "attachment.vpc-id"
    values = [var.vpc_id]
  }
}

# Get a list of private subnets by availability zone
data "aws_subnet" "private_subnets" {
  for_each = toset(var.private_subnet_ids)
  id       = each.value
}


# Get main route table for the VPC
data "aws_route_table" "main" {
  vpc_id = var.vpc_id
  filter {
    name   = "association.main"
    values = ["true"]
  }
}

# Data source for the current region
data "aws_region" "current" {}