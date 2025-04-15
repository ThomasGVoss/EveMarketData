# Get a list of private subnets by availability zone
data "aws_subnet" "private_subnets" {
  for_each = toset(data.aws_subnets.private.ids)
  id       = each.value
}

# Select one subnet per AZ to avoid the "DuplicateSubnetsInSameZone" error
locals {
  # Create a map of AZ -> subnet ID
  az_to_subnet = {
    for id, subnet in data.aws_subnet.private_subnets : 
      subnet.availability_zone => id...
  }
  
  # Select the first subnet ID from each AZ
  selected_subnet_ids = [for subnet_ids in values(local.az_to_subnet) : subnet_ids[0]]
}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoint" {
  name        = "ecr-endpoint-sg"
  description = "Allow HTTPS inbound for ECR endpoints"
  vpc_id      = data.aws_vpc.existing_vpc.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.existing_vpc.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ECR VPC Endpoints with one subnet per AZ
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id             = data.aws_vpc.existing_vpc.id
  service_name       = "com.amazonaws.eu-central-1.ecr.dkr"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = local.selected_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id             = data.aws_vpc.existing_vpc.id
  service_name       = "com.amazonaws.eu-central-1.ecr.api"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = local.selected_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true
}

# Get main route table for the VPC
data "aws_route_table" "main" {
  vpc_id = data.aws_vpc.existing_vpc.id
  filter {
    name   = "association.main"
    values = ["true"]
  }
}

# S3 Gateway endpoint for ECR
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = data.aws_vpc.existing_vpc.id
  service_name      = "com.amazonaws.eu-central-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [data.aws_route_table.main.id]
}

# Add CloudWatch Logs VPC endpoint
resource "aws_vpc_endpoint" "logs" {
  vpc_id             = data.aws_vpc.existing_vpc.id
  service_name       = "com.amazonaws.eu-central-1.logs"
  vpc_endpoint_type  = "Interface"
  subnet_ids         = local.selected_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true
}
