output "app_server" {
  description = "The created EC2 instance"
  value       = aws_instance.app_server
}

output "instance_id" {
  description = "The ID of the created EC2 instance"
  value       = aws_instance.app_server.id
}

output "private_ip" {
  description = "The private IP of the created EC2 instance"
  value       = aws_instance.app_server.private_ip
}

output "public_ip" {
  description = "The public IP of the created EC2 instance, if available"
  value       = aws_instance.app_server.public_ip
} 