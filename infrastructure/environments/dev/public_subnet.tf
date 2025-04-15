# Get available AZs in current region
data "aws_availability_zones" "available" {
  state = "available"
}

# Find the existing Internet Gateway attached to the VPC
data "aws_internet_gateway" "existing" {
  filter {
    name   = "attachment.vpc-id"
    values = [data.aws_vpc.existing_vpc.id]
  }
}

# Create public subnets in 2 AZs
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = data.aws_vpc.existing_vpc.id
  
  # Determine CIDR blocks that don't overlap with existing subnets
  # Adjust these if they overlap with existing CIDR ranges
  cidr_block        = cidrsubnet(data.aws_vpc.existing_vpc.cidr_block, 8, count.index + 100)
  
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "eve-market-public-${count.index}"
    Type = "Public"
    Environment = "dev"
    ManagedBy = "terraform"
  }
}

# Create a route table for public subnets
resource "aws_route_table" "public" {
  vpc_id = data.aws_vpc.existing_vpc.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = data.aws_internet_gateway.existing.id
  }
  
  tags = {
    Name = "eve-market-public-rt"
    Environment = "dev"
    ManagedBy = "terraform"
  }
}

# Associate public subnets with the public route table
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Output the public subnet IDs for reference
output "public_subnet_ids" {
  value = aws_subnet.public[*].id
  description = "IDs of the newly created public subnets"
}
