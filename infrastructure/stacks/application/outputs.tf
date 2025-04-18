
# Outputs
output "streamlit_ecr_repository_url" {
  value = module.streamlit_ecr.repository_url
}

output "streamlit_alb_dns_name" {
  value = module.streamlit_alb.alb_dns_name
}

output "streamlit_service_name" {
  value = module.streamlit_ecs.service_name
}