output "public_subnet_ids" {
  value       = aws_subnet.public[*].id
  description = "IDs of the newly created public subnets"
}

output "vpc_endpoint_security_group_id" {
  value       = aws_security_group.vpc_endpoint.id
  description = "ID of the security group for VPC endpoints"
}